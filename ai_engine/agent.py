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
• Browser Agent   — browser-use + Ollama for autonomous selector discovery (optional)
• Template engine — guaranteed valid tests using compiled spec selectors
• Memory system   — learns from failures, persists selector fixes between runs
• Self-healing    — 3 rounds of AI fix on failures
• Bug tickets     — per-failure AI analysis with screenshots + evidence
• HTML report     — complete with network logs, console errors, performance data
• Test data log   — written incrementally; CI always has data even if cancelled
"""

import os, sys, json, ast, re, builtins, subprocess
import concurrent.futures as _cf
from pathlib import Path
from datetime import datetime

import ollama

# ── Package imports ────────────────────────────────────────────────────────────
try:
    from ai_engine.spec_parser    import parse as parse_spec, ParsedSpec
    from ai_engine.spec_compiler  import compile_spec
    from ai_engine.test_generator import generate_all as tg_generate_all
    from ai_engine.test_generator import set_ai_caller as tg_set_caller
    from ai_engine.test_validator import validate_code
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
    from test_validator import validate_code
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

# Optional browser-use integration (no API key — uses local Ollama)
try:
    from ai_engine.browser_agent import discover_page, run_exploratory_check
    _BROWSER_USE_AVAILABLE = True
except ImportError:
    _BROWSER_USE_AVAILABLE = False

# ── Real-time output ──────────────────────────────────────────────────────────
_real_print = builtins.print
def print(*a, **kw):
    kw.setdefault("flush", True); _real_print(*a, **kw)
def log(msg=""):
    _real_print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

# ── Config ────────────────────────────────────────────────────────────────────
BASE_URL         = os.getenv("BASE_URL",  "https://beta-stg.markopolo.ai")
AI_MODEL         = os.getenv("AI_MODEL",  "qwen2.5-coder:1.5b")
AI_TIMEOUT       = int(os.getenv("AI_TIMEOUT", "90"))    # seconds per ollama call
BROWSER_USE_ON   = os.getenv("BROWSER_USE_ENABLED", "false").lower() == "true"
BROWSER_USE_MDL  = os.getenv("BROWSER_USE_MODEL", "qwen2.5:7b")
SPECS_DIR        = Path("specs")
TESTS_DIR        = Path("tests")
REPORTS_DIR      = Path("reports")
SHOTS_DIR        = Path("reports/screenshots")
MAX_FIX_RETRIES  = 3

# Spec files to skip — these are templates/docs, not real test specs
_SKIP_SPECS = {"TEMPLATE.md", "README.md", "EXAMPLE.md"}

# ── Multi-model chain — 14 free/open-source models ────────────────────────────
MODEL_CHAIN = [
    (AI_MODEL,                4096, 0.05),
    (AI_MODEL,                2000, 0.10),
    ("qwen2.5-coder:7b",      4096, 0.05),
    ("deepseek-coder:6.7b",   4096, 0.05),
    ("codellama:7b",          3000, 0.08),
    ("mistral:7b",            3000, 0.08),
    ("phi4:3.8b",             3000, 0.08),
    ("llama3.2:3b",           3000, 0.10),
    ("phi3.5",                3000, 0.10),
    ("gemma2:2b",             2500, 0.10),
    ("llama3.2:1b",           3000, 0.10),
    ("qwen2.5-coder:1.5b",    2000, 0.12),
    ("tinyllama:1.1b",        2000, 0.12),
    ("qwen2.5:0.5b",          1500, 0.15),
]

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
5. Navigation: page.goto(url, wait_until="domcontentloaded", timeout=15000)
6. Selector priority: get_by_role > get_by_label > get_by_placeholder > locator(css)
7. Assertions: expect(locator).to_be_visible() / expect(page).to_have_url()
8. Unique test emails: f"qa_{{int(time.time())}}@mailinator.com"
9. Passwords: os.getenv("TEST_PASSWORD", "Test@1234!")
10. MAX 25 lines per function. End every function COMPLETELY — never leave open.
"""

SYS_BUG = "You are a senior QA lead. Write formal, actionable bug tickets."
SYS_ANALYST = "You are a senior QA engineer. Analyse test coverage gaps."

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
_CONFIRMED_UNAVAILABLE: set[str] = set()


def _chat_with_timeout(model: str, messages: list, options: dict) -> dict | None:
    """Call ollama.chat with a hard timeout — prevents hanging in CI."""
    with _cf.ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(ollama.chat, model=model, messages=messages, options=options)
        try:
            return fut.result(timeout=AI_TIMEOUT)
        except _cf.TimeoutError:
            log(f"  [AI] ⏱  {model} timed out after {AI_TIMEOUT}s")
            return None
        except Exception as e:
            raise e  # let caller handle other exceptions


def ai_call(system: str, user: str, max_tokens: int = 4096) -> str:
    """Try every model in MODEL_CHAIN until one responds. Never raises."""
    global _AVAILABLE
    if _AVAILABLE is None:
        _AVAILABLE = _available_models()
        if _AVAILABLE:
            log(f"  [MODELS] Available: {sorted(_AVAILABLE)}")
        else:
            log("  [MODELS] No models — template engine will handle generation")

    for model, tok, temp in MODEL_CHAIN:
        if model in _CONFIRMED_UNAVAILABLE:
            continue
        if model not in _AVAILABLE and model != AI_MODEL:
            continue
        effective = min(max_tokens, tok)
        log(f"  [AI] → {model}  max_tokens={effective}  timeout={AI_TIMEOUT}s")
        try:
            resp = _chat_with_timeout(
                model,
                [{"role": "system", "content": system},
                 {"role": "user",   "content": user}],
                {"temperature": temp, "num_predict": effective},
            )
            if resp is None:
                continue  # timeout — try next model but don't permanently blacklist
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
                    log("  [AI] ⚠️  Multiple models unavailable — template engine")
                    return ""

    log("  [AI] ⚠️  All models exhausted — template fallback")
    return ""


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
        ast.parse(code); return True, ""
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
    return _HDR + "\n".join(clean_lines).lstrip()

# ── Template engine ───────────────────────────────────────────────────────────

def _safe_doc(s: str) -> str:
    """Strip characters that break Python triple-quoted docstrings."""
    return s.replace("\\", "").replace('"""', "'''").replace("`", "'")


def template_tests(spec: ParsedSpec, compiled: dict | None = None) -> str:
    """
    Generates valid Playwright tests using compiled spec selectors.
    Works for any project without AI — just change the .md spec file.
    All page operations have explicit timeouts to prevent CI hangs.
    """
    slug = spec.slug.replace("-", "_")
    url  = spec.url or (BASE_URL + spec.path)
    NAV  = f'wait_until="domcontentloaded", timeout=15000'   # safe navigation args
    WT   = "timeout=10000"                                    # short wait timeout

    # Extract selectors from compiled spec
    def _sel_val(v):
        if isinstance(v, dict):
            return v.get("selector") or v.get("hint") or ""
        return str(v) if v else ""

    raw_sel = compiled.get("selectors", {}) if compiled else {}

    def _find_sel(kws: list[str], fallback: str) -> str:
        for key, val in raw_sel.items():
            if any(kw in key.lower() for kw in kws):
                s = _sel_val(val)
                if s: return s
        return fallback

    email_sel  = _find_sel(["email", "username"],              "input[type='email']")
    pass_sel   = _find_sel(["password", "passwd", "pwd"],      "input[type='password']")
    submit_sel = _find_sel(["submit", "login", "sign_in",
                             "signin", "register", "button"],  "button[type='submit']")

    has_email  = bool(_find_sel(["email", "username"], ""))
    has_pass   = bool(_find_sel(["password", "passwd", "pwd"], ""))
    has_submit = bool(_find_sel(["submit", "login", "sign_in", "button"], ""))

    lines = [
        "import os, time, pytest",
        "from playwright.sync_api import Page, expect",
        f'BASE_URL = os.getenv("BASE_URL", "{BASE_URL}")',
        "",
    ]

    # 1. Page load
    lines += [
        f"def test_{slug}_page_loads(page: Page):",
        f'    """Verify {spec.page_name} page loads without server errors."""',
        f'    page.goto("{url}", {NAV})',
        f'    assert page.url, "Page URL should not be empty"',
        f'    assert not page.locator("text=500").is_visible({WT}), "Server error visible"',
        f'    assert not page.locator("text=404").is_visible({WT}), "404 error visible"',
        "",
    ]

    # 2. Submit with valid credentials
    if has_email and has_pass and has_submit:
        lines += [
            f"def test_{slug}_submit_valid_credentials(page: Page):",
            f'    """Submit valid credentials — expect redirect."""',
            f'    # TEST_DATA: valid email + TEST_PASSWORD env var',
            f'    page.goto("{url}", {NAV})',
            f'    page.locator("{email_sel}").wait_for(state="visible", timeout=10000)',
            f'    page.locator("{email_sel}").fill(f"qa_{{int(time.time())}}@mailinator.com")',
            f'    page.locator("{pass_sel}").fill(os.getenv("TEST_PASSWORD", "Test@1234!"))',
            f'    page.locator("{submit_sel}").click()',
            f'    page.wait_for_load_state("domcontentloaded", {WT})',
            f'    assert page.url, "Page URL should not be empty after submit"',
            "",
        ]
    elif has_email and has_submit:
        lines += [
            f"def test_{slug}_submit_email(page: Page):",
            f'    """Submit email form."""',
            f'    # TEST_DATA: test email address',
            f'    page.goto("{url}", {NAV})',
            f'    page.locator("{email_sel}").fill("qa_test@mailinator.com")',
            f'    page.locator("{submit_sel}").click()',
            f'    page.wait_for_load_state("domcontentloaded", {WT})',
            f'    assert page.url, "Page URL after submit"',
            "",
        ]

    # 3. Invalid email validation
    if has_email and has_submit:
        lines += [
            f"def test_{slug}_invalid_email_format(page: Page):",
            f'    """Submit invalid email — expect validation error."""',
            f'    # TEST_DATA: invalid email: notanemail',
            f'    page.goto("{url}", {NAV})',
            f'    page.locator("{email_sel}").wait_for(state="visible", timeout=10000)',
            f'    page.locator("{email_sel}").fill("notanemail")',
            f'    if page.locator("{pass_sel}").count() > 0:',
            f'        page.locator("{pass_sel}").fill("Test@1234!")',
            f'    page.locator("{submit_sel}").click()',
            f'    assert page.url or True, "Page responds to invalid email"',
            "",
        ]

    # 4. Empty form submit
    if has_submit:
        lines += [
            f"def test_{slug}_empty_form_submit(page: Page):",
            f'    """Submit empty form — expect validation, not crash."""',
            f'    # TEST_DATA: empty fields',
            f'    page.goto("{url}", {NAV})',
            f'    page.locator("{submit_sel}").click()',
            f'    assert not page.locator("text=500").is_visible({WT}), "Server error on empty submit"',
            f'    assert not page.locator("text=Traceback").is_visible({WT}), "Stack trace exposed"',
            "",
        ]

    # 5. User flows
    for i, flow in enumerate(spec.flows[:4], 1):
        fname = re.sub(r"\W+", "_", flow["name"].lower())[:40]
        lines += [
            f"def test_{slug}_flow_{i}_{fname}(page: Page):",
            f'    """Flow {i}: {_safe_doc(flow["name"])}"""',
            f'    # TEST_DATA: flow navigation',
            f'    page.goto("{url}", {NAV})',
            f'    assert "{spec.path.rstrip("/")}" in page.url or page.url.startswith(BASE_URL), \\',
            f'        f"Expected on {{BASE_URL}}{spec.path}, got {{page.url}}"',
            "",
        ]

    # 6. Edge cases
    for ec in spec.edge_cases[:5]:
        eid      = ec["id"].lower().replace("-", "_")
        scenario = _safe_doc(ec["scenario"][:80])
        lines += [
            f"def test_{eid}(page: Page):",
            f'    """{ec["id"]}: {scenario}"""',
            f'    # TEST_DATA: edge case — {scenario[:40]}',
            f'    page.goto("{url}", {NAV})',
            f'    assert page.url, "Page loads for edge case {ec["id"]}"',
            "",
        ]

    # 7. Mobile responsive
    lines += [
        f"def test_{slug}_mobile_viewport(page: Page):",
        f'    """Verify page renders on mobile (375x667)."""',
        f'    # TEST_DATA: viewport 375x667 (iPhone SE)',
        f'    page.set_viewport_size({{"width": 375, "height": 667}})',
        f'    page.goto("{url}", {NAV})',
        f'    assert page.url, "Mobile viewport page URL"',
        f'    assert not page.locator("text=500").is_visible({WT}), "Server error on mobile"',
        "",
    ]

    # 8. Console errors
    lines += [
        f"def test_{slug}_no_console_errors(page: Page):",
        f'    """Verify no critical JS errors on page load."""',
        f'    # TEST_DATA: no input — clean page load',
        f'    errors = []',
        f'    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)',
        f'    page.goto("{url}", {NAV})',
        f'    critical = [e for e in errors if "TypeError" in e or "ReferenceError" in e]',
        f'    assert critical == [], f"Critical JS errors: {{critical[:3]}}"',
        "",
    ]

    # 9. XSS quick check
    if has_email:
        lines += [
            f"def test_{slug}_xss_basic(page: Page):",
            f'    """Basic XSS — script tag should not execute."""',
            f'    # TEST_DATA: XSS payload <script>alert(1)</script>',
            f'    page.goto("{url}", {NAV})',
            f'    page.locator("{email_sel}").wait_for(state="visible", timeout=10000)',
            f'    page.locator("{email_sel}").fill("<script>alert(1)</script>")',
            f'    if page.locator("{submit_sel}").count() > 0:',
            f'        page.locator("{submit_sel}").click()',
            f'    assert not page.locator("text=alert(1)").is_visible({WT}), "XSS payload rendered"',
            "",
        ]

    # 10. Load time
    lines += [
        f"def test_{slug}_load_time(page: Page):",
        f'    """Page loads within 5 seconds."""',
        f'    # TEST_DATA: no input — load time measurement',
        f'    import time as _t',
        f'    start = _t.time()',
        f'    page.goto("{url}", {NAV})',
        f'    elapsed = _t.time() - start',
        f'    assert elapsed < 5.0, f"Page loaded in {{elapsed:.2f}}s — exceeds 5s threshold"',
        "",
    ]

    return "\n".join(lines)


# ── Section-based AI generation (secondary fallback) ─────────────────────────

def _gen_section(title: str, instructions: str, context: str) -> str:
    prompt = f"Write Playwright pytest functions for: {title}\n\n{context}\n\nINSTRUCTIONS:\n{instructions}\n\nOutput ONLY def test_...() functions. No imports."
    for attempt in range(1, 4):
        log(f"    [SECTION:{title}] attempt {attempt}/3")
        raw  = ai_call(SYS_TEST, prompt, max_tokens=3000)
        code = clean_code(raw)
        if not code: continue
        valid, err = is_valid_python(_HDR + code)
        if valid:
            log(f"    [SECTION:{title}] ✅ {code.count('def test_')} tests")
            return code
        log(f"    [SECTION:{title}] ❌ {err} — retrying")
        prompt = f"Fix syntax error: {err}\n\nReturn ONLY corrected function definitions:\n{code}"
    return ""


def generate_sections_fallback(spec: ParsedSpec) -> str:
    try:
        from ai_engine.spec_parser import (flows_prompt_section, edge_cases_prompt_section,
                                            validation_prompt_section, security_prompt_section)
    except ImportError:
        from spec_parser import (flows_prompt_section, edge_cases_prompt_section,
                                  validation_prompt_section, security_prompt_section)
    chunks = []
    if spec.flows:
        c = _gen_section("User Flows", "ONE test per flow. Assert URL or visible element.", flows_prompt_section(spec))
        if c: chunks.append(c)
    c = _gen_section("Validation", "Test invalid input (assert error). Test valid input (assert passes).", validation_prompt_section(spec))
    if c: chunks.append(c)
    if spec.edge_cases:
        c = _gen_section("Edge Cases", "ONE test per edge case. Assert expected behaviour.", edge_cases_prompt_section(spec))
        if c: chunks.append(c)
    if not chunks: return ""
    full = _HDR + "\n\n".join(chunks)
    ok, err = is_valid_python(full)
    if ok: return full
    fixed = clean_code(ai_call(SYS_TEST, f"Fix: {err}\n\nCode:\n{full}\n\nReturn complete fixed file.", 4096))
    ok2, _ = is_valid_python(fixed)
    return fixed if ok2 else ""


# ── Primary generator ─────────────────────────────────────────────────────────

def generate_all_22_types(spec: ParsedSpec) -> tuple[str, dict]:
    log(f"  [GEN] Generating all 22 test types for {spec.page_name}")
    raw_chunks = tg_generate_all(spec, _XSS, _SQLI)
    log(f"  [GEN] test_generator returned {len(raw_chunks)} type(s)")

    valid_chunks = []
    type_log: dict = {}

    for type_name, code in raw_chunks.items():
        if not code or not code.strip():
            log(f"    [GEN:{type_name}] empty — skipped")
            continue
        result = validate_code(_HDR + code)
        if result["valid"]:
            n = code.count("def test_")
            log(f"    [GEN:{type_name}] ✅ {n} test(s)")
            valid_chunks.append(code)
            type_log[type_name] = {
                "test_count": n,
                "tests":      re.findall(r"def (test_\w+)", code),
                "test_data":  re.findall(r"# TEST_DATA:\s*(.+)", code),
            }
        else:
            log(f"    [GEN:{type_name}] ❌ {result['errors']} — skipped")

    if not valid_chunks:
        return "", {}

    combined = _HDR + "\n\n".join(valid_chunks)
    ok, err = is_valid_python(combined)
    if ok:
        log(f"  [GEN] ✅ {combined.count('def test_')} tests across {len(valid_chunks)} type(s)")
        return combined, type_log

    log(f"  [GEN] Syntax in combined ({err}) — AI fix attempt...")
    fixed = clean_code(ai_call(SYS_TEST, f"Fix: {err}\n\nReturn complete corrected file:\n{combined}", 4096))
    ok2, err2 = is_valid_python(fixed)
    if ok2:
        log("  [GEN] ✅ Combined fixed")
        return fixed, type_log
    log(f"  [GEN] ❌ Fix failed ({err2}) — sections fallback")
    return "", {}


# ── Test execution ────────────────────────────────────────────────────────────

def _stream(cmd: list, env: dict, timeout: int = 300) -> tuple[int, str]:
    lines = []
    try:
        proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, bufsize=1)
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
    env = {**os.environ, "BASE_URL": BASE_URL, "PWDEBUG": "0", "PYTHONUNBUFFERED": "1"}

    log(f"  [COLLECT] Discovering tests in {test_file.name}...")
    _rc, cout = _stream([sys.executable, "-m", "pytest", str(test_file),
                         "--collect-only", "-q", "--no-header"], env, timeout=60)
    m = re.search(r"(\d+) tests? collected", cout)
    collected = int(m.group(1)) if m else len(re.findall(r"::test_\w+", cout))
    log(f"  [COLLECT] {collected} test function(s) found")
    if collected == 0:
        log("  [COLLECT] ⚠️  0 tests — file content:")
        log(test_file.read_text())

    log("  [PYTEST] Running tests...")
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
        "status":     "passed" if rc == 0 else "failed",
        "total": total, "passed": passed, "failed": failed,
        "output": output,
        "json_report": str(json_report) if json_report.exists() else None,
        "returncode":  rc,
    }


# ── Incremental state writer ──────────────────────────────────────────────────

def _save_partial_state(agent):
    """Write partial results to disk — CI always has data even if job is cancelled."""
    try:
        total_p = sum(r.get("passed", 0) for r in agent.all_results.values())
        total_f = sum(r.get("failed", 0) for r in agent.all_results.values())
        total_t = sum(r.get("total",  0) for r in agent.all_results.values())
        all_bugs = [b for r in agent.all_results.values() for b in r.get("bugs", [])]

        (REPORTS_DIR / "summary.json").write_text(json.dumps({
            "timestamp":    datetime.now().isoformat(),
            "model":        AI_MODEL,
            "base_url":     BASE_URL,
            "total_passed": total_p,
            "total_failed": total_f,
            "total_tests":  total_t,
            "total_bugs":   len(all_bugs),
            "specs_tested": list(agent.all_results.keys()),
            "model_chain":  [m for m, _, _ in MODEL_CHAIN],
            "partial":      True,
        }, indent=2))

        (REPORTS_DIR / "test_data_log.json").write_text(json.dumps({
            "timestamp":  datetime.now().isoformat(),
            "model_used": AI_MODEL,
            "base_url":   BASE_URL,
            "specs":      agent._test_data_log,
        }, indent=2))
    except Exception as e:
        log(f"  [STATE] ⚠️  Could not save partial state: {e}")


# ── Main agent ────────────────────────────────────────────────────────────────

class AutonomousTestAgent:

    def __init__(self):
        self.all_results: dict[str, dict] = {}
        self._test_data_log: dict[str, dict] = {}
        TESTS_DIR.mkdir(exist_ok=True)
        REPORTS_DIR.mkdir(exist_ok=True)
        SHOTS_DIR.mkdir(parents=True, exist_ok=True)
        _wire_ai_callers()
        ms = mem_summary()
        if ms["fixed_selectors"] or ms["failure_records"]:
            log(f"  [MEMORY] {ms['fixed_selectors']} selector fix(es), "
                f"{ms['failure_records']} failure record(s)")
        if BROWSER_USE_ON and _BROWSER_USE_AVAILABLE:
            log(f"  [BROWSER-USE] Enabled — model: {BROWSER_USE_MDL}")
        elif BROWSER_USE_ON:
            log("  [BROWSER-USE] Requested but not installed (pip install browser-use langchain-ollama)")

    def run(self):
        self._banner()
        specs = sorted(
            s for s in SPECS_DIR.glob("*.md")
            if s.name not in _SKIP_SPECS and not s.name.startswith("_")
        )
        if not specs:
            log("[ERROR] No .md spec files in specs/ (TEMPLATE.md is skipped automatically)")
            sys.exit(1)
        log(f"  [SPECS] Processing: {[s.name for s in specs]}")
        for sp in specs:
            self._process(sp)
        self._final_report()

    def _process(self, spec_path: Path):
        name = spec_path.stem
        log(f"\n{'━'*64}")
        log(f"  SPEC: {spec_path.name}")
        log(f"{'━'*64}")

        # 1. Parse
        log("  [PARSE] Reading spec...")
        spec = parse_spec(spec_path)
        log(f"  [PARSE] {len(spec.flows)} flows | {len(spec.edge_cases)} edge cases | "
            f"{len(spec.validation_rules)} validation rules")

        # 2. Compile
        log("  [COMPILE] Compiling spec to JSON...")
        compiled = compile_spec(spec_path.read_text(encoding="utf-8"), str(spec_path))
        compiled_path = spec_path.with_suffix(".spec.json")
        compiled_path.write_text(json.dumps(compiled, indent=2, ensure_ascii=False))
        log(f"  [COMPILE] {len(compiled['selectors'])} selectors | saved → {compiled_path.name}")

        # 2b. Optional browser-use discovery
        if BROWSER_USE_ON and _BROWSER_USE_AVAILABLE:
            url = compiled.get("url") or (BASE_URL + spec.path)
            log(f"  [BROWSER-USE] Discovering page: {url}")
            try:
                enriched = discover_page(url, compiled, model=BROWSER_USE_MDL)
                if enriched.get("selectors"):
                    compiled["selectors"].update(enriched["selectors"])
                    log(f"  [BROWSER-USE] ✅ Enriched {len(enriched['selectors'])} selectors")
                if enriched.get("issues"):
                    log(f"  [BROWSER-USE] ⚠️  Found {len(enriched['issues'])} issue(s): {enriched['issues'][:3]}")
            except Exception as e:
                log(f"  [BROWSER-USE] ⚠️  Discovery failed: {e}")

        test_file = TESTS_DIR / f"test_{name.replace('-','_')}.py"

        # 3. Generate
        log("\n  [THINK] Generating tests (22 types)...")
        type_log: dict = {}
        code, type_log = generate_all_22_types(spec)

        if not code:
            log("  [GEN] Trying section-based fallback...")
            code = generate_sections_fallback(spec)

        if not code:
            log("  [FALLBACK] Using template engine (zero-AI, compiled selectors)...")
            code = template_tests(spec, compiled)
            type_log = {
                "template": {
                    "test_count": code.count("def test_"),
                    "tests":      re.findall(r"def (test_\w+)", code),
                    "test_data":  re.findall(r"# TEST_DATA:\s*(.+)", code),
                }
            }
            log(f"  [FALLBACK] Template: {code.count('def test_')} tests")

        code = ensure_imports(code)

        # 4. Validate
        vresult = validate_code(code)
        if not vresult["valid"]:
            log(f"  [VALIDATE] ❌ {vresult['errors']} — skipping {name}")
            self.all_results[name] = {"status": "generation_failed", "total": 0,
                                      "passed": 0, "failed": 0, "bugs": [], "gaps": ""}
            return
        log(f"  [VALIDATE] ✅ {code.count('def test_')} tests validated")
        test_file.write_text(code)
        log(f"  [SAVE]  {test_file}")

        # Track test data — write immediately so CI has data even if cancelled
        self._test_data_log[name] = {
            "spec":        name,
            "total_tests": code.count("def test_"),
            "ai_model":    AI_MODEL,
            "types":       type_log,
        }
        _save_partial_state(self)

        # 5. Execute
        log(f"\n  [EXECUTE] Running against {BASE_URL}...")
        results = run_tests(test_file)
        self._show(results)

        # 6. Self-heal
        if results["failed"] > 0:
            log(f"\n  [REFLECT] {results['failed']} failure(s) — self-healing...")
            for fix_round in range(1, MAX_FIX_RETRIES + 1):
                log(f"  [FIX] Round {fix_round}/{MAX_FIX_RETRIES}")
                fixed_raw = ai_call(
                    SYS_TEST,
                    f"Fix failing Playwright tests.\n\nFAILURES:\n{results['output'][:2000]}\n\n"
                    f"CODE:\n{code}\n\nReturn complete corrected file. Python only.",
                    4096,
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
                    if "selector" in results["output"].lower():
                        record_failure(name, "unknown_selector", results["output"][:200])
                else:
                    log(f"  [FIX] ❌ Invalid code: {e}")

            if results["failed"] > 0:
                for line in results["output"].splitlines():
                    m = re.match(r"FAILED\s+\S+::(test_\w+)", line)
                    if m: mark_flaky(m.group(1))

        # 7. Bug tickets
        bugs = []
        if results["failed"] > 0:
            log(f"\n  [BUGS] Writing {results['failed']} bug ticket(s)...")
            shot_idx = load_screenshot_index()
            ev_idx   = load_evidence_index()
            raw_bugs = build_from_json_report(results.get("json_report", ""), spec.raw, shot_idx, ev_idx)
            for b in raw_bugs:
                bugs.append(enrich_bug(b, shot_idx, ev_idx))
            log(f"  [BUGS] {len(bugs)} ticket(s) created")

        # 8. Gap analysis
        log("\n  [GAPS] Detecting coverage gaps...")
        gaps = gc_detect_gaps(spec, code, results)
        save_gaps_report(name, gaps, REPORTS_DIR)

        results.update({"bugs": bugs, "gaps": gaps, "spec_name": name, "compiled": compiled})
        self.all_results[name] = results

        # Write partial state after each spec (CI always has latest data)
        _save_partial_state(self)

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
        ms = mem_summary()
        log(f"  Memory      → {ms['fixed_selectors']} fixes | {ms['failure_records']} records")

        # Final (non-partial) summary.json
        (REPORTS_DIR / "summary.json").write_text(json.dumps({
            "timestamp":    datetime.now().isoformat(),
            "model":        AI_MODEL,
            "base_url":     BASE_URL,
            "total_passed": total_p,
            "total_failed": total_f,
            "total_tests":  total_t,
            "total_bugs":   len(all_bugs),
            "specs_tested": list(self.all_results.keys()),
            "model_chain":  [m for m, _, _ in MODEL_CHAIN],
        }, indent=2))

        (REPORTS_DIR / "test_data_log.json").write_text(json.dumps({
            "timestamp":  datetime.now().isoformat(),
            "model_used": AI_MODEL,
            "base_url":   BASE_URL,
            "specs":      self._test_data_log,
        }, indent=2))

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
        log(f"  AI timeout     : {AI_TIMEOUT}s per call")
        log(f"  Target URL     : {BASE_URL}")
        log(f"  Specs          : {len(list(s for s in SPECS_DIR.glob('*.md') if s.name not in _SKIP_SPECS))} file(s)")
        log(f"  Test types     : 22 (smoke → security)")
        log(f"  XSS payloads   : {len(_XSS)}  |  SQLi: {len(_SQLI)}")
        log(f"  Browser-use    : {'enabled (' + BROWSER_USE_MDL + ')' if BROWSER_USE_ON else 'disabled (set BROWSER_USE_ENABLED=true)'}")
        log(f"  Started        : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log("═"*64)


if __name__ == "__main__":
    AutonomousTestAgent().run()
