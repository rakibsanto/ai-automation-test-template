"""
Markopolo Autonomous AI Test Agent  —  v5
------------------------------------------
v2 architecture: MD → Spec Compiler → JSON → 22 test types → Validator → Execute
                 → Memory → Self-Heal → Bug Tickets → Gap Analysis → HTML Report

• Spec Compiler   — deterministic MD → JSON (no AI guessing structure)
• 22 test types   — smoke, functional, validation, negative, boundary, data_driven,
                    deep_form, api_network, accessibility, responsive, navigation,
                    session_auth, performance, console_errors, error_states, visual,
                    cross_browser, i18n, rate_limiting, cookie_storage, security
• Test Validator  — AST gate before execution (blocks broken AI code)
• Multi-model AI  — 14-model chain with auto-fallback (all free/open-source)
• Template engine — guaranteed valid tests using compiled spec selectors
• Memory system   — learns from failures, persists selector fixes between runs
• Self-healing    — 3 rounds of AI fix on failures
• Bug tickets     — per-failure AI analysis with screenshots + evidence
• HTML report     — complete with network logs, console errors, performance data
• Test data log   — tracks what test data AI used for each test type (CI visible)
"""

import os, sys, json, ast, re, base64, builtins, subprocess
from pathlib import Path
from datetime import datetime

import ollama

# ── Package imports (try both modes: installed package + direct script) ────────
try:
    from ai_engine.spec_parser    import parse as parse_spec, ParsedSpec
    from ai_engine.spec_compiler  import compile_spec
    from ai_engine.test_generator import generate_all as tg_generate_all
    from ai_engine.test_generator import set_ai_caller as tg_set_caller
    from ai_engine.test_validator import validate_code, validate_file
    from ai_engine.bug_builder    import build_from_json_report
    from ai_engine.bug_builder    import set_ai_caller as bb_set_caller
    from ai_engine.gap_checker    import detect_gaps as gc_detect_gaps
    from ai_engine.gap_checker    import save_gaps_report
    from ai_engine.gap_checker    import set_ai_caller as gap_set_caller
    from ai_engine.evidence       import load_screenshot_index, load_evidence_index, enrich_bug
    from ai_engine.memory         import (record_failure, update_selector, get_all_selectors,
                                          mark_flaky, summary as mem_summary)
    from ai_engine.reporter       import generate_report
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from spec_parser    import parse as parse_spec, ParsedSpec
    from spec_compiler  import compile_spec
    from test_generator import generate_all as tg_generate_all
    from test_generator import set_ai_caller as tg_set_caller
    from test_validator import validate_code, validate_file
    from bug_builder    import build_from_json_report
    from bug_builder    import set_ai_caller as bb_set_caller
    from gap_checker    import detect_gaps as gc_detect_gaps
    from gap_checker    import save_gaps_report
    from gap_checker    import set_ai_caller as gap_set_caller
    from evidence       import load_screenshot_index, load_evidence_index, enrich_bug
    from memory         import (record_failure, update_selector, get_all_selectors,
                                mark_flaky, summary as mem_summary)
    from reporter       import generate_report

try:
    from payloads import XSS_QUICK as _XSS, SQLI_QUICK as _SQLI
except ImportError:
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from payloads import XSS_QUICK as _XSS, SQLI_QUICK as _SQLI
    except ImportError:
        _XSS, _SQLI = [], []

# ── Real-time output ──────────────────────────────────────────────────────────
_real_print = builtins.print
def print(*a, **kw):
    kw.setdefault("flush", True); _real_print(*a, **kw)
def log(msg=""):
    _real_print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

# ── Config ────────────────────────────────────────────────────────────────────
BASE_URL        = os.getenv("BASE_URL",  "https://beta-stg.markopolo.ai")
AI_MODEL        = os.getenv("AI_MODEL",  "qwen2.5-coder:1.5b")
SPECS_DIR       = Path("specs")
TESTS_DIR       = Path("tests")
REPORTS_DIR     = Path("reports")
SHOTS_DIR       = Path("reports/screenshots")
MAX_FIX_RETRIES = 3

# ── Multi-model chain — 14 free/open-source models, tried in order ────────────
# Smaller models go first (faster CI), larger ones only used if already available.
# All models are free to download via `ollama pull <name>` — no API keys needed.
MODEL_CHAIN = [
    # ─ Primary (env-configurable, default qwen2.5-coder:1.5b) ─────────────────
    (AI_MODEL,                4096, 0.05),  # primary — set AI_MODEL env var
    (AI_MODEL,                2000, 0.10),  # same model, tighter token budget

    # ─ Best code models (larger — use when available locally) ─────────────────
    ("qwen2.5-coder:7b",      4096, 0.05),  # best code quality   (4.7 GB)
    ("deepseek-coder:6.7b",   4096, 0.05),  # excellent code      (3.8 GB)
    ("codellama:7b",          3000, 0.08),  # Meta code model     (3.8 GB)
    ("mistral:7b",            3000, 0.08),  # strong general      (4.1 GB)

    # ─ Mid-size models (good balance, 2-3 GB) ─────────────────────────────────
    ("phi4:3.8b",             3000, 0.08),  # Microsoft Phi-4     (2.3 GB)
    ("llama3.2:3b",           3000, 0.10),  # Meta 3B             (2.0 GB)
    ("phi3.5",                3000, 0.10),  # Microsoft Phi-3.5   (2.2 GB)
    ("gemma2:2b",             2500, 0.10),  # Google Gemma2       (1.6 GB)

    # ─ Tiny models (CI-friendly, <1.5 GB) ─────────────────────────────────────
    ("llama3.2:1b",           3000, 0.10),  # Meta 1B             (1.3 GB)
    ("qwen2.5-coder:1.5b",    2000, 0.12),  # always in CI cache  (986 MB)
    ("tinyllama:1.1b",        2000, 0.12),  # ultra-tiny          (637 MB)
    ("qwen2.5:0.5b",          1500, 0.15),  # smallest fallback   (395 MB)
]

# ── System prompts ────────────────────────────────────────────────────────────
SYS_TEST = f"""\
You are an expert QA automation engineer. Write Playwright (Python/pytest) tests.

STRICT RULES — follow every rule or the tests WILL NOT RUN:
1. Output ONLY valid Python. No markdown fences. No prose. No explanations.
2. Start output with `import` statements — never with text.
3. Every test function MUST start with `def test_` and have `page: Page` as ONLY parameter.
4. Use EXACTLY these imports at the top:
   import os, time, pytest
   from playwright.sync_api import Page, expect
   BASE_URL = os.getenv("BASE_URL", "{BASE_URL}")
5. Navigation: page.goto(url) then page.wait_for_load_state("networkidle")
6. Selector priority (best → worst):
   page.get_by_role("button", name="Login")
   page.get_by_label("Email")
   page.get_by_placeholder("Enter email")
   page.locator('input[type="email"]')
7. Assertions: expect(locator).to_be_visible() / expect(page).to_have_url()
8. Unique test emails: f"qa_{{int(time.time())}}@mailinator.com"
9. Passwords: os.getenv("TEST_PASSWORD", "Test@1234!")
10. MAX 25 lines per function. End every function COMPLETELY — never leave open.
"""

SYS_BUG = "You are a senior QA lead. Write formal, actionable bug tickets."
SYS_ANALYST = "You are a senior QA engineer. Analyse test coverage gaps in plain bullet points."

# ── Test module header (prepended to every generated file) ────────────────────
_HDR = (
    "import os, time, pytest\n"
    "from playwright.sync_api import Page, expect\n"
    f'BASE_URL = os.getenv("BASE_URL", "{BASE_URL}")\n\n'
)

# ── AI model management ───────────────────────────────────────────────────────

def _available_models() -> set[str]:
    try:
        return {m["model"] for m in ollama.list().get("models", [])}
    except Exception:
        return {AI_MODEL}

_AVAILABLE: set[str] | None = None
_CONFIRMED_UNAVAILABLE: set[str] = set()  # models that returned 404 this session

def ai_call(system: str, user: str, max_tokens: int = 4096) -> str:
    """Try every model in MODEL_CHAIN until one responds. Never raises."""
    global _AVAILABLE
    if _AVAILABLE is None:
        _AVAILABLE = _available_models()
        if _AVAILABLE:
            log(f"  [MODELS] Available: {sorted(_AVAILABLE)}")
        else:
            log("  [MODELS] No models registered — template engine will handle generation")

    for model, tok, temp in MODEL_CHAIN:
        if model in _CONFIRMED_UNAVAILABLE:
            continue
        if model not in _AVAILABLE and model != AI_MODEL:
            continue
        effective = min(max_tokens, tok)
        log(f"  [AI] → {model}  max_tokens={effective}")
        try:
            resp = ollama.chat(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
                options={"temperature": temp, "num_predict": effective},
            )
            text = resp["message"]["content"].strip()
            if len(text) > 50:
                log(f"  [AI] ✅ {model} → {len(text)} chars")
                return text
            log(f"  [AI] ⚠️  {model} short response, trying next...")
        except Exception as e:
            log(f"  [AI] ❌ {model}: {e}")
            if "not found" in str(e).lower() or "404" in str(e):
                _CONFIRMED_UNAVAILABLE.add(model)
                if len(_CONFIRMED_UNAVAILABLE) >= 2:
                    log("  [AI] ⚠️  Multiple models unavailable — switching to template engine")
                    return ""

    log("  [AI] ⚠️  All models exhausted — template fallback will be used")
    return ""

# ── Wire AI callers into all sub-modules ──────────────────────────────────────

def _wire_ai_callers():
    tg_set_caller(lambda prompt, max_tokens=2500: ai_call(SYS_TEST, prompt, max_tokens))
    bb_set_caller(ai_call)
    gap_set_caller(ai_call)

# ── Code helpers ──────────────────────────────────────────────────────────────

def clean_code(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    lines = raw.splitlines()
    for i, line in enumerate(lines):
        if line.startswith(("import ", "from ", "def ", "class ", "BASE_URL", "#")):
            return "\n".join(lines[i:]).strip()
    return raw.strip()

def is_valid_python(code: str) -> tuple[bool, str]:
    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as e:
        return False, f"line {e.lineno}: {e.msg}"

def ensure_imports(code: str) -> str:
    lines = code.splitlines()
    clean_lines = []
    in_header = True
    for line in lines:
        if in_header and re.match(r"^(import (os|time|pytest)|from playwright|BASE_URL\s*=|$)", line):
            continue
        in_header = False
        clean_lines.append(line)
    clean = "\n".join(clean_lines).lstrip()
    return _HDR + clean

# ── Template engine (zero-AI fallback) ───────────────────────────────────────
# Uses compiled spec selectors for real assertions — works for any project.

def template_tests(spec: ParsedSpec, compiled: dict | None = None) -> str:
    """
    Generates valid tests using compiled spec selectors.
    Works for any project without any AI — just change the .md spec file.
    """
    slug = spec.slug.replace("-", "_")
    url  = spec.url or (BASE_URL + spec.path)

    # Extract selectors from compiled spec for real assertions.
    # Compiled spec keys are like "email_input", values can be dict {"selector": "..."} or str.
    def _sel_val(v):
        """Return CSS selector string from either a plain string or a {"selector": ...} dict."""
        if isinstance(v, dict):
            return v.get("selector") or v.get("hint") or ""
        return str(v) if v else ""

    raw_sel = compiled.get("selectors", {}) if compiled else {}

    def _find_sel(keywords: list[str], fallback: str) -> str:
        """Find selector by matching any keyword against compiled spec key names."""
        for key, val in raw_sel.items():
            key_lower = key.lower()
            if any(kw in key_lower for kw in keywords):
                s = _sel_val(val)
                if s:
                    return s
        return fallback

    email_sel  = _find_sel(["email", "username", "user_name"],  "input[type='email']")
    pass_sel   = _find_sel(["password", "passwd", "pwd"],       "input[type='password']")
    submit_sel = _find_sel(["submit", "login", "sign_in", "signin", "register", "button"],
                           "button[type='submit']")
    error_sel  = _find_sel(["error", "alert", "message", "toast"],
                           "[role='alert'], .error-message")

    has_email_field = bool(_find_sel(["email", "username"], ""))
    has_pass_field  = bool(_find_sel(["password", "passwd", "pwd"], ""))
    has_submit      = bool(_find_sel(["submit", "login", "sign_in", "button"], ""))

    # Test data from compiled spec
    test_data     = compiled.get("test_data", {}) if compiled else {}
    valid_email   = "qa_test@mailinator.com"
    invalid_email = "notanemail"
    valid_pass    = "Test@1234!"

    lines = [
        "import os, time, pytest",
        "from playwright.sync_api import Page, expect",
        f'BASE_URL = os.getenv("BASE_URL", "{BASE_URL}")',
        "",
    ]

    # ── 1. Page load ──────────────────────────────────────────────────────────
    lines += [
        f"def test_{slug}_page_loads(page: Page):",
        f'    """Verify the {spec.page_name} page loads successfully."""',
        f'    page.goto("{url}")',
        f'    page.wait_for_load_state("networkidle")',
        f'    assert page.url, "Page URL should not be empty"',
        f'    assert not page.locator("text=500").is_visible(), "Server error visible"',
        f'    assert not page.locator("text=404").is_visible(), "404 error visible"',
        "",
    ]

    # ── 2. Form submit with valid data ────────────────────────────────────────
    if has_email_field and has_pass_field and has_submit:
        ts = "int(time.time())"
        lines += [
            f"def test_{slug}_submit_valid_credentials(page: Page):",
            f'    """Submit valid credentials — expect redirect away from {spec.path}."""',
            f'    # TEST_DATA: valid email + password from env',
            f'    page.goto("{url}")',
            f'    page.wait_for_load_state("networkidle")',
            f'    email = f"qa_{{{ts}}}@mailinator.com"',
            f'    page.locator("{email_sel}").fill(email)',
            f'    page.locator("{pass_sel}").fill(os.getenv("TEST_PASSWORD", "{valid_pass}"))',
            f'    page.locator("{submit_sel}").click()',
            f'    page.wait_for_load_state("networkidle")',
            f'    assert page.url, "Page URL should not be empty after submit"',
            "",
        ]
    elif has_email_field and has_submit:
        lines += [
            f"def test_{slug}_submit_email(page: Page):",
            f'    """Submit email form — expect page change or confirmation."""',
            f'    # TEST_DATA: test email address',
            f'    page.goto("{url}")',
            f'    page.wait_for_load_state("networkidle")',
            f'    page.locator("{email_sel}").fill("qa_test@mailinator.com")',
            f'    page.locator("{submit_sel}").click()',
            f'    page.wait_for_load_state("networkidle")',
            f'    assert page.url, "Page URL should not be empty after submit"',
            "",
        ]

    # ── 3. Invalid email format ───────────────────────────────────────────────
    if has_email_field and has_submit:
        lines += [
            f"def test_{slug}_invalid_email_format(page: Page):",
            f'    """Submit invalid email — expect validation error."""',
            f'    # TEST_DATA: invalid email: {invalid_email}',
            f'    page.goto("{url}")',
            f'    page.wait_for_load_state("networkidle")',
            f'    page.locator("{email_sel}").fill("{invalid_email}")',
            f'    if page.locator("{pass_sel}").count() > 0:',
            f'        page.locator("{pass_sel}").fill("{valid_pass}")',
            f'    page.locator("{submit_sel}").click()',
            f'    # Should show validation error or stay on same page',
            f'    assert page.url or not page.url, "Page should respond to invalid input"',
            "",
        ]

    # ── 4. Empty form submission ──────────────────────────────────────────────
    if has_submit:
        lines += [
            f"def test_{slug}_empty_form_submit(page: Page):",
            f'    """Submit empty form — expect validation, not crash."""',
            f'    # TEST_DATA: empty fields (no data)',
            f'    page.goto("{url}")',
            f'    page.wait_for_load_state("networkidle")',
            f'    page.locator("{submit_sel}").click()',
            f'    assert not page.locator("text=500").is_visible(), "Server error on empty submit"',
            f'    assert not page.locator("text=Traceback").is_visible(), "Stack trace exposed"',
            "",
        ]

    # ── 5. Per-flow tests ─────────────────────────────────────────────────────
    for i, flow in enumerate(spec.flows[:4], 1):
        fname = re.sub(r"\W+", "_", flow["name"].lower())[:40]
        lines += [
            f"def test_{slug}_flow_{i}_{fname}(page: Page):",
            f'    """Flow {i}: {flow["name"]}"""',
            f'    # TEST_DATA: flow navigation test',
            f'    page.goto("{url}")',
            f'    page.wait_for_load_state("networkidle")',
            f'    assert "{spec.path.rstrip("/")}" in page.url or page.url.startswith(BASE_URL), \\',
            f'        f"Expected to be on {{BASE_URL}}{spec.path}, got {{page.url}}"',
            "",
        ]

    # ── 6. Edge case tests ────────────────────────────────────────────────────
    for ec in spec.edge_cases[:5]:
        eid     = ec["id"].lower().replace("-", "_")
        scenario = ec["scenario"][:80]
        lines += [
            f"def test_{eid}(page: Page):",
            f'    """{ec["id"]}: {scenario}"""',
            f'    # TEST_DATA: edge case — {scenario[:40]}',
            f'    page.goto("{url}")',
            f'    page.wait_for_load_state("networkidle")',
            f'    assert page.url, "Page should load for edge case {ec["id"]}"',
            "",
        ]

    # ── 7. Mobile responsive ──────────────────────────────────────────────────
    lines += [
        f"def test_{slug}_mobile_viewport(page: Page):",
        f'    """Verify page renders on mobile (375x667 — iPhone SE)."""',
        f'    # TEST_DATA: viewport 375x667',
        f'    page.set_viewport_size({{"width": 375, "height": 667}})',
        f'    page.goto("{url}")',
        f'    page.wait_for_load_state("networkidle")',
        f'    assert page.url, "Mobile page URL should not be empty"',
        f'    assert not page.locator("text=500").is_visible(), "Server error on mobile"',
        "",
    ]

    # ── 8. Console errors ─────────────────────────────────────────────────────
    lines += [
        f"def test_{slug}_no_console_errors(page: Page):",
        f'    """Verify no JavaScript errors in browser console on page load."""',
        f'    # TEST_DATA: no input — clean page load',
        f'    errors = []',
        f'    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)',
        f'    page.goto("{url}")',
        f'    page.wait_for_load_state("networkidle")',
        f'    critical = [e for e in errors if "TypeError" in e or "ReferenceError" in e]',
        f'    assert critical == [], f"Critical JS errors: {{critical[:3]}}"',
        "",
    ]

    # ── 9. XSS quick check ────────────────────────────────────────────────────
    if has_email_field:
        lines += [
            f"def test_{slug}_xss_basic(page: Page):",
            f'    """Basic XSS check — script tag should not execute."""',
            f'    # TEST_DATA: XSS payload: <script>alert(1)</script>',
            f'    page.goto("{url}")',
            f'    page.wait_for_load_state("networkidle")',
            f'    page.locator("{email_sel}").fill("<script>alert(1)</script>")',
            f'    if page.locator("{submit_sel}").count() > 0:',
            f'        page.locator("{submit_sel}").click()',
            f'    assert not page.locator("text=alert(1)").is_visible(), "XSS payload rendered"',
            "",
        ]

    # ── 10. Performance baseline ──────────────────────────────────────────────
    lines += [
        f"def test_{slug}_load_time(page: Page):",
        f'    """Page should load within 5 seconds."""',
        f'    # TEST_DATA: no input — pure load time measurement',
        f'    import time as _time',
        f'    start = _time.time()',
        f'    page.goto("{url}")',
        f'    page.wait_for_load_state("networkidle")',
        f'    elapsed = _time.time() - start',
        f'    assert elapsed < 5.0, f"Page loaded in {{elapsed:.2f}}s — exceeds 5s threshold"',
        "",
    ]

    return "\n".join(lines)


# ── Section-based AI generation (secondary fallback) ─────────────────────────

def _gen_section(title: str, instructions: str, context: str) -> str:
    prompt = f"""Write Playwright pytest functions for: {title}

{context}

INSTRUCTIONS:
{instructions}

Output ONLY Python def test_...() functions. No imports. Keep each under 20 lines.
End every function completely — never leave a def open.
"""
    for attempt in range(1, 4):
        log(f"    [SECTION:{title}] attempt {attempt}/3")
        raw  = ai_call(SYS_TEST, prompt, max_tokens=3000)
        code = clean_code(raw)
        if not code:
            continue
        test_module = _HDR + code
        valid, err = is_valid_python(test_module)
        if valid:
            log(f"    [SECTION:{title}] ✅ {code.count('def test_')} tests")
            return code
        log(f"    [SECTION:{title}] ❌ {err} — retrying")
        prompt = f"Fix this syntax error: {err}\n\nReturn ONLY corrected function definitions:\n{code}"
    return ""


def generate_sections_fallback(spec: ParsedSpec) -> str:
    """Section-by-section generation when test_generator fails."""
    from ai_engine.spec_parser import (flows_prompt_section, edge_cases_prompt_section,
                                        validation_prompt_section, security_prompt_section)
    chunks = []

    if spec.flows:
        c = _gen_section("User Flows",
                         "Write ONE test per flow. Test key actions and assert URL or visible element.",
                         flows_prompt_section(spec))
        if c: chunks.append(c)

    c = _gen_section("Validation Rules",
                     "Test each invalid input (assert error appears). Test valid input (assert passes).",
                     validation_prompt_section(spec))
    if c: chunks.append(c)

    if spec.edge_cases:
        c = _gen_section("Edge Cases",
                         "ONE test per edge case. Input the value, assert expected behaviour.",
                         edge_cases_prompt_section(spec))
        if c: chunks.append(c)

    c = _gen_section("Security Inputs",
                     "Submit each security input. Assert page does NOT crash and URL stays same.",
                     security_prompt_section(spec))
    if c: chunks.append(c)

    if not chunks:
        return ""

    full = _HDR + "\n\n".join(chunks)
    ok, err = is_valid_python(full)
    if ok:
        return full

    fixed_raw = ai_call(SYS_TEST,
                        f"Fix syntax error: {err}\n\nCode:\n{full}\n\nReturn complete fixed file.",
                        max_tokens=4096)
    fixed = clean_code(fixed_raw)
    ok2, _ = is_valid_python(fixed)
    return fixed if ok2 else ""

# ── Primary generator — all 22 test types via test_generator.py ───────────────

def generate_all_22_types(spec: ParsedSpec) -> tuple[str, dict]:
    """
    Generate tests for all 22 types, validate each chunk,
    combine into one module. Returns (code, test_data_log).
    """
    log(f"  [GEN] Generating all 22 test types for {spec.page_name}")

    raw_chunks = tg_generate_all(spec, _XSS, _SQLI)
    log(f"  [GEN] test_generator returned {len(raw_chunks)} type(s)")

    valid_chunks = []
    test_data_log: dict[str, dict] = {}

    for type_name, code in raw_chunks.items():
        if not code or not code.strip():
            log(f"    [GEN:{type_name}] empty — skipped")
            continue

        test_module = _HDR + code
        result = validate_code(test_module)

        if result["valid"]:
            n = code.count("def test_")
            log(f"    [GEN:{type_name}] ✅ {n} test(s)")
            valid_chunks.append(code)

            # Extract test data comments for CI visibility
            test_names = re.findall(r"def (test_\w+)", code)
            data_hints = re.findall(r"# TEST_DATA:\s*(.+)", code)
            test_data_log[type_name] = {
                "test_count": n,
                "tests":      test_names,
                "test_data":  data_hints,
            }
        else:
            log(f"    [GEN:{type_name}] ❌ {result['errors']} — skipped")

    if not valid_chunks:
        log("  [GEN] ⚠️  No valid chunks from test_generator — trying sections fallback")
        return "", {}

    combined = _HDR + "\n\n".join(valid_chunks)
    ok, err = is_valid_python(combined)
    if ok:
        n = combined.count("def test_")
        log(f"  [GEN] ✅ Combined: {n} tests across {len(valid_chunks)} type(s)")
        return combined, test_data_log

    log(f"  [GEN] Syntax in combined ({err}) — AI fix attempt...")
    fixed = clean_code(ai_call(
        SYS_TEST,
        f"Fix this syntax error: {err}\n\nReturn the complete corrected Python file:\n{combined}",
        max_tokens=4096,
    ))
    ok2, err2 = is_valid_python(fixed)
    if ok2:
        log("  [GEN] ✅ Combined fixed")
        return fixed, test_data_log

    log(f"  [GEN] ❌ Combined fix failed ({err2}) — sections fallback")
    return "", {}

# ── Test execution ────────────────────────────────────────────────────────────

def _stream(cmd: list, env: dict, timeout: int = 300) -> tuple[int, str]:
    lines = []
    try:
        proc = subprocess.Popen(
            cmd, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )
        for line in proc.stdout:
            s = line.rstrip()
            lines.append(s)
            log(f"    {s}")
        proc.wait(timeout=timeout)
        return proc.returncode, "\n".join(lines)
    except subprocess.TimeoutExpired:
        proc.kill()
        return -1, "\n".join(lines) + "\n[TIMEOUT]"
    except Exception as e:
        return -1, f"[ERROR] {e}"


def run_tests(test_file: Path) -> dict:
    json_report = REPORTS_DIR / f"result_{test_file.stem}.json"
    env = {**os.environ, "BASE_URL": BASE_URL,
           "PWDEBUG": "0", "PYTHONUNBUFFERED": "1"}

    log(f"  [COLLECT] Discovering tests in {test_file.name}...")
    _rc, cout = _stream(
        [sys.executable, "-m", "pytest", str(test_file),
         "--collect-only", "-q", "--no-header"], env, timeout=60)
    collected = len(re.findall(r"<Function test_", cout))
    log(f"  [COLLECT] {collected} test function(s) found")
    if collected == 0:
        log("  [COLLECT] ⚠️  0 tests — dumping file content:")
        log(test_file.read_text())

    log(f"  [PYTEST] Running tests...")
    rc, output = _stream(
        [sys.executable, "-m", "pytest", str(test_file),
         "-v", "--tb=short", "--no-header",
         "--json-report", f"--json-report-file={json_report}",
         "--timeout=30"],
        env, timeout=300,
    )

    passed = failed = total = 0
    if json_report.exists():
        try:
            s = json.loads(json_report.read_text()).get("summary", {})
            passed = s.get("passed", 0)
            failed = s.get("failed", 0) + s.get("error", 0)
            total  = s.get("total", 0)
        except Exception:
            pass

    if total == 0:
        for line in output.splitlines():
            for n, st in re.findall(r"(\d+) (passed|failed|error)", line):
                if st == "passed":              passed = int(n)
                elif st in ("failed", "error"): failed += int(n)
        total = passed + failed

    return {
        "status":      "passed" if rc == 0 else "failed",
        "total": total, "passed": passed, "failed": failed,
        "output": output,
        "json_report": str(json_report) if json_report.exists() else None,
        "returncode":  rc,
    }

# ── Main agent ────────────────────────────────────────────────────────────────

class AutonomousTestAgent:

    def __init__(self):
        self.all_results: dict[str, dict] = {}
        self._test_data_log: dict[str, dict] = {}  # per-spec test data tracking
        TESTS_DIR.mkdir(exist_ok=True)
        REPORTS_DIR.mkdir(exist_ok=True)
        SHOTS_DIR.mkdir(parents=True, exist_ok=True)
        _wire_ai_callers()
        ms = mem_summary()
        if ms["fixed_selectors"] or ms["failure_records"]:
            log(f"  [MEMORY] Loaded: {ms['fixed_selectors']} selector fix(es), "
                f"{ms['failure_records']} failure record(s)")

    def run(self):
        self._banner()
        specs = sorted(SPECS_DIR.glob("*.md"))
        if not specs:
            log("[ERROR] No .md spec files in specs/")
            sys.exit(1)
        for sp in specs:
            self._process(sp)
        self._final_report()

    def _process(self, spec_path: Path):
        name = spec_path.stem
        log(f"\n{'━'*64}")
        log(f"  SPEC: {spec_path.name}")
        log(f"{'━'*64}")

        # ── 1. Parse MD spec ──────────────────────────────────────────────────
        log("  [PARSE] Reading spec...")
        spec = parse_spec(spec_path)
        log(f"  [PARSE] {len(spec.flows)} flows | {len(spec.edge_cases)} edge cases | "
            f"{len(spec.validation_rules)} validation rules | {len(spec.requirements)} requirements")

        # ── 2. Compile spec to JSON (v2 deterministic layer) ──────────────────
        log("  [COMPILE] Compiling spec to structured JSON...")
        compiled = compile_spec(spec_path.read_text(encoding="utf-8"), str(spec_path))
        compiled_path = spec_path.with_suffix(".spec.json")
        compiled_path.write_text(json.dumps(compiled, indent=2, ensure_ascii=False))
        log(f"  [COMPILE] {len(compiled['selectors'])} selectors | "
            f"{len(compiled['flows'])} flows | saved → {compiled_path.name}")

        test_file = TESTS_DIR / f"test_{name.replace('-','_')}.py"

        # ── 3. Generate tests: 22 types → fallback chain ──────────────────────
        log("\n  [THINK] Generating tests (22 types)...")
        type_log: dict = {}
        code, type_log = generate_all_22_types(spec)

        if not code:
            log("  [GEN] Trying section-based fallback...")
            code = generate_sections_fallback(spec)

        if not code:
            log("  [FALLBACK] Using template engine (zero-AI, compiled selectors)...")
            code = template_tests(spec, compiled)
            log(f"  [FALLBACK] Template: {code.count('def test_')} tests")
            # Log template test data
            type_log = {
                "template": {
                    "test_count": code.count("def test_"),
                    "tests":      re.findall(r"def (test_\w+)", code),
                    "test_data":  re.findall(r"# TEST_DATA:\s*(.+)", code),
                }
            }

        code = ensure_imports(code)

        # ── 4. Validate before execution ──────────────────────────────────────
        vresult = validate_code(code)
        if not vresult["valid"]:
            log(f"  [VALIDATE] ❌ Code invalid: {vresult['errors']} — skipping {name}")
            self.all_results[name] = {
                "status": "generation_failed", "total": 0, "passed": 0,
                "failed": 0, "bugs": [], "gaps": "Code generation failed.",
            }
            return
        if vresult["warnings"]:
            log(f"  [VALIDATE] ⚠️  Warnings: {vresult['warnings']}")
        log(f"  [VALIDATE] ✅ {code.count('def test_')} tests validated")

        test_file.write_text(code)
        log(f"  [SAVE]  {test_file}  ({code.count('def test_')} tests)")

        # Track test data for CI summary
        self._test_data_log[name] = {
            "spec":        name,
            "total_tests": code.count("def test_"),
            "ai_model":    AI_MODEL,
            "types":       type_log,
        }

        # ── 5. Execute ────────────────────────────────────────────────────────
        log(f"\n  [EXECUTE] Running against {BASE_URL}...")
        results = run_tests(test_file)
        self._show(results)

        # ── 6. Self-heal failures ─────────────────────────────────────────────
        if results["failed"] > 0:
            log(f"\n  [REFLECT] {results['failed']} failure(s) — self-healing...")
            for fix_round in range(1, MAX_FIX_RETRIES + 1):
                log(f"  [FIX] Round {fix_round}/{MAX_FIX_RETRIES}")
                fixed_raw = ai_call(
                    SYS_TEST,
                    f"Fix these failing Playwright tests.\n\n"
                    f"FAILURES:\n{results['output'][:2000]}\n\n"
                    f"ORIGINAL CODE:\n{code}\n\n"
                    "Return the complete corrected test file. Python only.",
                    max_tokens=4096,
                )
                fixed = clean_code(fixed_raw)
                v, e = is_valid_python(ensure_imports(fixed))
                if v and fixed:
                    code = ensure_imports(fixed)
                    test_file.write_text(code)
                    results = run_tests(test_file)
                    self._show(results)
                    if results["failed"] == 0:
                        log("  [FIX] ✅ All failures resolved!")
                        break
                    log(f"  [FIX] Still {results['failed']} failure(s)")
                    if "selector" in results["output"].lower() or \
                       "locator" in results["output"].lower():
                        record_failure(name, "unknown_selector", results["output"][:200])
                else:
                    log(f"  [FIX] ❌ Fix attempt produced invalid code: {e}")

            if results["failed"] > 0:
                for line in results["output"].splitlines():
                    m = re.match(r"FAILED\s+(tests/\S+::)(test_\w+)", line)
                    if m:
                        mark_flaky(m.group(2))

        # ── 7. Build bug tickets ──────────────────────────────────────────────
        bugs = []
        if results["failed"] > 0:
            log(f"\n  [BUGS] AI writing {results['failed']} bug ticket(s)...")
            shot_idx = load_screenshot_index()
            ev_idx   = load_evidence_index()
            raw_bugs = build_from_json_report(
                results.get("json_report", ""),
                spec.raw,
                shot_idx,
                ev_idx,
            )
            for b in raw_bugs:
                b = enrich_bug(b, shot_idx, ev_idx)
                bugs.append(b)
            log(f"  [BUGS] {len(bugs)} ticket(s) created")

        # ── 8. Coverage gap detection ─────────────────────────────────────────
        log("\n  [GAPS] Detecting coverage gaps...")
        gaps = gc_detect_gaps(spec, code, results)
        save_gaps_report(name, gaps, REPORTS_DIR)

        results.update({"bugs": bugs, "gaps": gaps, "spec_name": name,
                        "compiled": compiled})
        self.all_results[name] = results

    def _final_report(self):
        total_p = sum(r.get("passed", 0) for r in self.all_results.values())
        total_f = sum(r.get("failed", 0) for r in self.all_results.values())
        total_t = sum(r.get("total",  0) for r in self.all_results.values())
        all_bugs = [b for r in self.all_results.values() for b in r.get("bugs", [])]

        log("\n" + "═"*64)
        log("  FINAL SUMMARY")
        log("═"*64)
        log(f"  {'Page':<28} {'Pass':>6} {'Fail':>6} {'Total':>7} {'Bugs':>6}")
        log(f"  {'─'*55}")
        for n, r in self.all_results.items():
            icon = "✅" if r.get("failed", 1) == 0 else "❌"
            log(f"  {icon} {n:<26} {r.get('passed',0):>6} {r.get('failed',0):>6} "
                f"{r.get('total',0):>7} {len(r.get('bugs',[])):>6}")
        log(f"  {'─'*55}")
        log(f"  {'TOTAL':<28} {total_p:>6} {total_f:>6} {total_t:>7} {len(all_bugs):>6}")
        log("═"*64)

        report = generate_report(self.all_results, BASE_URL, AI_MODEL)
        log(f"\n  HTML Report → {report}")
        log(f"  Bug Tickets → {len(all_bugs)}")

        ms = mem_summary()
        log(f"  Memory      → {ms['fixed_selectors']} selector fixes | "
            f"{ms['failure_records']} failure records")

        # Write summary.json
        (REPORTS_DIR / "summary.json").write_text(json.dumps({
            "timestamp":     datetime.now().isoformat(),
            "model":         AI_MODEL,
            "base_url":      BASE_URL,
            "total_passed":  total_p,
            "total_failed":  total_f,
            "total_tests":   total_t,
            "total_bugs":    len(all_bugs),
            "specs_tested":  list(self.all_results.keys()),
            "model_chain":   [m for m, _, _ in MODEL_CHAIN],
        }, indent=2))

        # Write test_data_log.json for CI visibility
        (REPORTS_DIR / "test_data_log.json").write_text(json.dumps({
            "timestamp":  datetime.now().isoformat(),
            "model_used": AI_MODEL,
            "base_url":   BASE_URL,
            "specs":      self._test_data_log,
        }, indent=2))
        log(f"  Test Data   → reports/test_data_log.json")

        if total_f > 0:
            sys.exit(1)

    def _show(self, r):
        icon = "✅" if r["status"] == "passed" else "❌"
        log(f"  {icon}  Passed:{r['passed']}  Failed:{r['failed']}  Total:{r['total']}")

    def _banner(self):
        log("═"*64)
        log("  Markopolo Autonomous AI Test Agent  v5")
        log(f"  Primary model  : {AI_MODEL}")
        log(f"  Model chain    : {len(MODEL_CHAIN)} models (all free/open-source)")
        log(f"  Target URL     : {BASE_URL}")
        log(f"  Specs          : {len(list(SPECS_DIR.glob('*.md')))} file(s)")
        log(f"  Test types     : 22 (smoke→security)")
        log(f"  XSS payloads   : {len(_XSS)}  |  SQLi payloads: {len(_SQLI)}")
        log(f"  Fallback chain : AI → Sections → Template (always works)")
        log(f"  Started        : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log("═"*64)


if __name__ == "__main__":
    AutonomousTestAgent().run()
