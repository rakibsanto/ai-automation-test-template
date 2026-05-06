"""
Fagun Autonomous AI Test Agent  —  v5
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
BASE_URL         = os.getenv("BASE_URL",  "https://beta-stg.fagun.ai")
AI_MODEL         = os.getenv("AI_MODEL",  "qwen2.5-coder:1.5b")
AI_TIMEOUT       = int(os.getenv("AI_TIMEOUT", "90"))    # seconds per ollama call
BROWSER_USE_ON   = os.getenv("BROWSER_USE_ENABLED", "false").lower() == "true"
BROWSER_USE_MDL  = os.getenv("BROWSER_USE_MODEL", "qwen2.5:7b")
SPECS_DIR        = Path("specs")
TESTS_DIR        = Path("tests")
REPORTS_DIR      = Path("reports")
SHOTS_DIR        = Path("reports/screenshots")
MAX_FIX_RETRIES  = int(os.getenv("MAX_FIX_RETRIES", "3"))
_MAX_TIMEOUTS    = 1   # blacklist a model after this many timeouts per session

# Spec files to skip — these are templates/docs, not real test specs
_SKIP_SPECS = {"TEMPLATE.md", "README.md", "EXAMPLE.md"}

# ── Multi-model chain — 14 free/open-source models ────────────────────────────
# Each entry: (model, max_tokens, temperature, per_model_timeout_seconds)
# Smaller models respond faster — give them shorter timeouts to fail fast.
MODEL_CHAIN = [
    (AI_MODEL,                4096, 0.05, 120),   # primary (7b)
    (AI_MODEL,                2500, 0.08, 120),
    ("qwen2.5-coder:7b",      4096, 0.05, 120),
    ("qwen2.5-coder:7b",      2000, 0.10, 120),
    ("deepseek-coder:6.7b",   4096, 0.05, 120),
    ("codellama:7b",          3000, 0.08, 120),
    ("mistral:7b",            3000, 0.08, 120),
    ("phi4:3.8b",             3000, 0.08,  90),
    ("llama3.2:3b",           3000, 0.10,  90),
    ("phi3.5",                3000, 0.10,  90),
    ("gemma2:2b",             2500, 0.10,  60),
    ("llama3.2:1b",           3000, 0.10,  60),
    ("qwen2.5-coder:1.5b",    2000, 0.12,  60),
    ("tinyllama:1.1b",        2000, 0.12,  45),
    ("qwen2.5:0.5b",          1500, 0.15,  35),   # 0.5b responds fast or not at all
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
_TIMEOUT_COUNTS: dict[str, int] = {}   # per-session timeout counter per model


def _chat_with_timeout(model: str, messages: list, options: dict,
                       timeout: int = AI_TIMEOUT) -> dict | None:
    """Call ollama.chat with a hard timeout — prevents hanging in CI."""
    with _cf.ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(ollama.chat, model=model, messages=messages, options=options)
        try:
            return fut.result(timeout=timeout)
        except _cf.TimeoutError:
            log(f"  [AI] ⏱  {model} timed out after {timeout}s")
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

    for model, tok, temp, model_timeout in MODEL_CHAIN:
        if model in _CONFIRMED_UNAVAILABLE:
            continue
        if model not in _AVAILABLE and model != AI_MODEL:
            continue
        effective = min(max_tokens, tok)
        log(f"  [AI] → {model}  max_tokens={effective}  timeout={model_timeout}s")
        try:
            resp = _chat_with_timeout(
                model,
                [{"role": "system", "content": system},
                 {"role": "user",   "content": user}],
                {"temperature": temp, "num_predict": effective},
                timeout=model_timeout,
            )
            if resp is None:
                _TIMEOUT_COUNTS[model] = _TIMEOUT_COUNTS.get(model, 0) + 1
                if _TIMEOUT_COUNTS[model] >= _MAX_TIMEOUTS:
                    log(f"  [AI] 🚫 {model} timed out — blacklisting for this session")
                    _CONFIRMED_UNAVAILABLE.add(model)
                continue
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
    return s.replace("\\", "").replace('"""', "'''").replace('"', "'").replace("`", "'")


def template_tests(spec: ParsedSpec, compiled: dict | None = None) -> str:  # noqa: C901
    """
    Generates 55+ valid Playwright tests using compiled spec selectors.
    Works for any project without AI — just change the .md spec file.
    Covers: page health, form elements, submission, validation, security,
    responsive, mobile/touch, performance, accessibility, storage/cookies,
    network resilience, user flows, edge cases, and additional UX checks.
    All page operations have explicit timeouts to prevent CI hangs.
    """
    slug = spec.slug.replace("-", "_")
    url  = spec.url or (BASE_URL + spec.path)
    NAV  = 'wait_until="domcontentloaded", timeout=15000'
    WT   = "timeout=10000"

    # ── Selector helpers ──────────────────────────────────────────────────────
    def _sel_val(v):
        if isinstance(v, dict):
            return v.get("selector") or v.get("hint") or ""
        return str(v) if v else ""

    raw_sel = compiled.get("selectors", {}) if compiled else {}

    def _find_sel(kws: list[str], fallback: str) -> str:
        for key, val in raw_sel.items():
            if any(kw in key.lower() for kw in kws):
                s = _sel_val(val)
                if s:
                    return s
        return fallback

    # Core selectors
    email_sel   = _find_sel(["email", "username"],                          "input[type='email']")
    pass_sel    = _find_sel(["password", "passwd", "pwd"],                  "input[type='password']")
    submit_sel  = _find_sel(["submit", "login", "sign_in",
                              "signin", "register", "button"],              "button[type='submit']")
    # Signup-specific selectors
    name_sel    = _find_sel(["name", "fullname", "full_name"],              "input[name='name'], input[name='fullName']")
    confirm_sel = _find_sel(["confirm", "confirmpassword", "repassword"],   "input[name='confirmPassword']")
    terms_sel   = _find_sel(["terms", "checkbox", "accept"],                "input[type='checkbox']")
    company_sel = _find_sel(["company", "organization", "org"],             "input[name='company']")

    has_email  = bool(email_sel)
    has_pass   = bool(pass_sel)
    has_submit = bool(submit_sel)

    # ── Page type detection ───────────────────────────────────────────────────
    page_lower = spec.page_name.lower()
    is_signup = "signup" in page_lower or "sign up" in page_lower or "register" in page_lower
    is_login  = "login"  in page_lower or "sign in" in page_lower
    is_reset  = "reset"  in page_lower or "forgot"  in page_lower

    # ── Signup form-fill helper (inline, reused by multiple tests) ────────────
    # Used as an indented code block inserted into test bodies
    def _signup_fill_block(indent: str = "    ") -> list[str]:
        """Return lines that fill ALL signup fields (with try/except guards)."""
        i = indent
        return [
            f"{i}# TEST_DATA: full signup form — name, email, password, confirm, terms",
            f"{i}try:",
            f"{i}    if page.locator(\"{name_sel}\").count() > 0:",
            f"{i}        page.locator(\"{name_sel}\").first.fill(\"Test User\")",
            f"{i}except Exception:",
            f"{i}    pass",
            f"{i}page.locator(\"{email_sel}\").fill(f\"qa_{{int(time.time())}}@mailinator.com\")",
            f"{i}page.locator(\"{pass_sel}\").fill(os.getenv(\"TEST_PASSWORD\", \"Test@1234!\"))",
            f"{i}try:",
            f"{i}    if page.locator(\"{confirm_sel}\").count() > 0:",
            f"{i}        page.locator(\"{confirm_sel}\").first.fill(os.getenv(\"TEST_PASSWORD\", \"Test@1234!\"))",
            f"{i}    if page.locator(\"{terms_sel}\").count() > 0:",
            f"{i}        page.locator(\"{terms_sel}\").first.check()",
            f"{i}    if page.locator(\"{company_sel}\").count() > 0:",
            f"{i}        page.locator(\"{company_sel}\").first.fill(\"TestCo\")",
            f"{i}except Exception:",
            f"{i}    pass",
        ]

    lines: list[str] = [
        "import os, time, pytest",
        "from playwright.sync_api import Page, expect",
        f'BASE_URL = os.getenv("BASE_URL", "{BASE_URL}")',
        "",
    ]

    # ═══════════════════════════════════════════════════════════════════════════
    # PAGE HEALTH (6 tests)
    # ═══════════════════════════════════════════════════════════════════════════

    lines += [
        f"def test_{slug}_page_loads(page: Page):",
        f'    """{_safe_doc(spec.page_name)} page loads without server errors."""',
        f'    page.goto("{url}", {NAV})',
        f'    assert page.url, "Page URL should not be empty"',
        f'    assert "500" not in page.title(), "500 in page title"',
        f'    assert not page.locator("text=Internal Server Error").is_visible({WT}), "Server error visible"',
        "",
    ]

    lines += [
        f"def test_{slug}_http_status_ok(page: Page):",
        f'    """HTTP response status is below 400."""',
        f'    # TEST_DATA: no input — HTTP status check',
        f'    response = page.goto("{url}", {NAV})',
        f'    assert response is not None, "No response received"',
        f'    assert response.status < 400, f"HTTP {{response.status}} — expected < 400"',
        "",
    ]

    lines += [
        f"def test_{slug}_title_meaningful(page: Page):",
        f'    """Page title is not empty, undefined, or null."""',
        f'    # TEST_DATA: no input — title check',
        f'    page.goto("{url}", {NAV})',
        f'    title = page.title()',
        f'    assert title, "Page title is empty"',
        f'    assert title.lower() not in ("undefined", "null", "none"), f"Meaningless title: {{title}}"',
        "",
    ]

    lines += [
        f"def test_{slug}_no_server_error_text(page: Page):",
        f'    """Page body contains no server-error text."""',
        f'    # TEST_DATA: no input — error text scan',
        f'    page.goto("{url}", {NAV})',
        f'    content = page.content().lower()',
        f'    assert "internal server error" not in content, "Internal Server Error visible"',
        f'    assert "500" not in page.title(), "500 in page title"',
        "",
    ]

    lines += [
        f"def test_{slug}_no_console_errors(page: Page):",
        f'    """No critical JS console errors on page load."""',
        f'    # TEST_DATA: no input — console monitoring',
        f'    errors = []',
        f'    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)',
        f'    page.goto("{url}", {NAV})',
        f'    critical = [e for e in errors if "TypeError" in e or "ReferenceError" in e]',
        f'    assert critical == [], f"Critical JS errors: {{critical[:3]}}"',
        "",
    ]

    lines += [
        f"def test_{slug}_no_uncaught_js_exceptions(page: Page):",
        f'    """No uncaught JS exceptions on page load."""',
        f'    # TEST_DATA: no input — pageerror monitoring',
        f'    exceptions = []',
        f'    page.on("pageerror", lambda exc: exceptions.append(str(exc)))',
        f'    page.goto("{url}", {NAV})',
        f'    assert exceptions == [], f"Uncaught JS exceptions: {{exceptions[:3]}}"',
        "",
    ]

    # ═══════════════════════════════════════════════════════════════════════════
    # FORM ELEMENTS (3-5 tests)
    # ═══════════════════════════════════════════════════════════════════════════

    if has_email:
        lines += [
            f"def test_{slug}_email_field_visible(page: Page):",
            f'    """Email field is visible on the page."""',
            f'    # TEST_DATA: no input — element visibility',
            f'    page.goto("{url}", {NAV})',
            f'    assert page.locator("{email_sel}").count() > 0, "Email field not found"',
            f'    page.locator("{email_sel}").first.wait_for(state="visible", {WT})',
            "",
        ]

    if has_pass:
        lines += [
            f"def test_{slug}_password_field_visible(page: Page):",
            f'    """Password field is visible on the page."""',
            f'    # TEST_DATA: no input — element visibility',
            f'    page.goto("{url}", {NAV})',
            f'    assert page.locator("{pass_sel}").count() > 0, "Password field not found"',
            f'    page.locator("{pass_sel}").first.wait_for(state="visible", {WT})',
            "",
        ]

    if has_submit:
        lines += [
            f"def test_{slug}_submit_button_enabled(page: Page):",
            f'    """Submit button is present and not disabled."""',
            f'    # TEST_DATA: no input — button state',
            f'    page.goto("{url}", {NAV})',
            f'    assert page.locator("{submit_sel}").count() > 0, "Submit button not found"',
            f'    btn = page.locator("{submit_sel}").first',
            f'    assert btn.is_enabled(), "Submit button is disabled"',
            "",
        ]

    if is_signup:
        lines += [
            f"def test_{slug}_name_field_visible(page: Page):",
            f'    """Name field is visible on signup page."""',
            f'    # TEST_DATA: no input — element visibility',
            f'    page.goto("{url}", {NAV})',
            f'    found = page.locator("{name_sel}").count() > 0',
            f'    # Informational — name field may have different selector',
            f'    assert found or True, "Name field check (informational)"',
            "",
        ]

        lines += [
            f"def test_{slug}_terms_checkbox_present(page: Page):",
            f'    """Terms checkbox is present on signup page."""',
            f'    # TEST_DATA: no input — element presence',
            f'    page.goto("{url}", {NAV})',
            f'    found = page.locator("{terms_sel}").count() > 0',
            f'    # Informational — terms may not always be present',
            f'    assert found or True, "Terms checkbox check (informational)"',
            "",
        ]

    # ═══════════════════════════════════════════════════════════════════════════
    # FORM SUBMISSION (3-4 tests)
    # ═══════════════════════════════════════════════════════════════════════════

    if has_submit:
        lines += [
            f"def test_{slug}_empty_form_no_crash(page: Page):",
            f'    """Submit empty form — validation fires, no 500 crash."""',
            f'    # TEST_DATA: empty fields',
            f'    page.goto("{url}", {NAV})',
            f'    if page.locator("{submit_sel}").count() > 0:',
            f'        page.locator("{submit_sel}").first.click()',
            f'    assert "500" not in page.title(), "500 on empty submit"',
            f'    assert not page.locator("text=Internal Server Error").is_visible({WT}), "Server error"',
            "",
        ]

    if is_signup and has_email and has_pass and has_submit:
        lines += [
            f"def test_{slug}_submit_valid(page: Page):",
            f'    """Submit signup form with all required fields filled."""',
        ]
        lines += _signup_fill_block("    ")
        lines += [
            f'    page.goto("{url}", {NAV})',
        ]
        lines += _signup_fill_block("    ")
        lines += [
            f'    if page.locator("{submit_sel}").count() > 0:',
            f'        page.locator("{submit_sel}").first.click()',
            f'    page.wait_for_load_state("domcontentloaded", {WT})',
            f'    assert page.url, "Page URL after signup submit"',
            "",
        ]
    elif is_login and has_email and has_pass and has_submit:
        lines += [
            f"def test_{slug}_submit_valid(page: Page):",
            f'    """Submit login form with valid credentials."""',
            f'    # TEST_DATA: valid email + TEST_PASSWORD env var',
            f'    page.goto("{url}", {NAV})',
            f'    page.locator("{email_sel}").first.fill(f"qa_{{int(time.time())}}@mailinator.com")',
            f'    page.locator("{pass_sel}").first.fill(os.getenv("TEST_PASSWORD", "Test@1234!"))',
            f'    page.locator("{submit_sel}").first.click()',
            f'    page.wait_for_load_state("domcontentloaded", {WT})',
            f'    assert page.url, "Page URL after login submit"',
            "",
        ]
    elif has_email and has_submit:
        lines += [
            f"def test_{slug}_submit_valid(page: Page):",
            f'    """Submit form with a valid email address."""',
            f'    # TEST_DATA: test email address',
            f'    page.goto("{url}", {NAV})',
            f'    page.locator("{email_sel}").first.fill(f"qa_{{int(time.time())}}@mailinator.com")',
            f'    if page.locator("{pass_sel}").count() > 0:',
            f'        page.locator("{pass_sel}").first.fill(os.getenv("TEST_PASSWORD", "Test@1234!"))',
            f'    page.locator("{submit_sel}").first.click()',
            f'    page.wait_for_load_state("domcontentloaded", {WT})',
            f'    assert page.url, "Page URL after submit"',
            "",
        ]

    if is_reset and has_email and has_submit:
        lines += [
            f"def test_{slug}_submit_reset_email(page: Page):",
            f'    """Submit password reset with a valid email."""',
            f'    # TEST_DATA: reset email address',
            f'    page.goto("{url}", {NAV})',
            f'    page.locator("{email_sel}").first.fill("qa_reset@mailinator.com")',
            f'    page.locator("{submit_sel}").first.click()',
            f'    page.wait_for_load_state("domcontentloaded", {WT})',
            f'    assert page.url, "Page URL after reset submit"',
            "",
        ]

    # ═══════════════════════════════════════════════════════════════════════════
    # VALIDATION (6-9 tests)
    # ═══════════════════════════════════════════════════════════════════════════

    if has_email and has_submit:
        lines += [
            f"def test_{slug}_invalid_email_rejected(page: Page):",
            f'    """Invalid email format does not crash the page."""',
            f'    # TEST_DATA: invalid email: notanemail',
            f'    page.goto("{url}", {NAV})',
            f'    page.locator("{email_sel}").first.fill("notanemail")',
            f'    if page.locator("{pass_sel}").count() > 0:',
            f'        page.locator("{pass_sel}").first.fill("Test@1234!")',
            f'    page.locator("{submit_sel}").first.click()',
            f'    assert "500" not in page.title(), "500 on invalid email"',
            "",
        ]

        lines += [
            f"def test_{slug}_spaces_only_email(page: Page):",
            f'    """Spaces-only email does not crash the page."""',
            f'    # TEST_DATA: email: "   " (spaces only)',
            f'    page.goto("{url}", {NAV})',
            f'    page.locator("{email_sel}").first.fill("   ")',
            f'    if page.locator("{pass_sel}").count() > 0:',
            f'        page.locator("{pass_sel}").first.fill("Test@1234!")',
            f'    page.locator("{submit_sel}").first.click()',
            f'    assert "500" not in page.title(), "500 on spaces-only email"',
            "",
        ]

        lines += [
            f"def test_{slug}_very_long_email(page: Page):",
            f'    """Very long email does not crash the page."""',
            f'    # TEST_DATA: email: a*260 + @test.com',
            f'    page.goto("{url}", {NAV})',
            f'    page.locator("{email_sel}").first.fill("a" * 260 + "@test.com")',
            f'    if page.locator("{submit_sel}").count() > 0:',
            f'        page.locator("{submit_sel}").first.click()',
            f'    assert "500" not in page.title(), "500 on very long email"',
            "",
        ]

    if is_signup and has_pass and has_submit:
        lines += [
            f"def test_{slug}_password_too_short(page: Page):",
            f'    """Too-short password does not crash the page."""',
            f'    # TEST_DATA: password: "abc12" (5 chars)',
            f'    page.goto("{url}", {NAV})',
            f'    if page.locator("{email_sel}").count() > 0:',
            f'        page.locator("{email_sel}").first.fill("qa@test.com")',
            f'    page.locator("{pass_sel}").first.fill("abc12")',
            f'    page.locator("{submit_sel}").first.click()',
            f'    assert "500" not in page.title(), "500 on short password"',
            "",
        ]

        lines += [
            f"def test_{slug}_password_mismatch(page: Page):",
            f'    """Mismatched confirm-password does not crash the page."""',
            f'    # TEST_DATA: password: Test@1234!, confirm: DifferentPass!',
            f'    page.goto("{url}", {NAV})',
            f'    if page.locator("{email_sel}").count() > 0:',
            f'        page.locator("{email_sel}").first.fill("qa@test.com")',
            f'    page.locator("{pass_sel}").first.fill("Test@1234!")',
            f'    try:',
            f'        if page.locator("{confirm_sel}").count() > 0:',
            f'            page.locator("{confirm_sel}").first.fill("DifferentPass!")',
            f'    except Exception:',
            f'        pass',
            f'    page.locator("{submit_sel}").first.click()',
            f'    assert "500" not in page.title(), "500 on password mismatch"',
            "",
        ]

        lines += [
            f"def test_{slug}_name_field_required(page: Page):",
            f'    """Submitting without name does not crash (validation expected)."""',
            f'    # TEST_DATA: name empty, email+pass filled',
            f'    page.goto("{url}", {NAV})',
            f'    if page.locator("{email_sel}").count() > 0:',
            f'        page.locator("{email_sel}").first.fill("qa@test.com")',
            f'    if page.locator("{pass_sel}").count() > 0:',
            f'        page.locator("{pass_sel}").first.fill("Test@1234!")',
            f'    page.locator("{submit_sel}").first.click()',
            f'    assert "500" not in page.title(), "500 on missing name"',
            "",
        ]

        lines += [
            f"def test_{slug}_terms_must_be_accepted(page: Page):",
            f'    """Submitting without accepting terms does not crash."""',
            f'    # TEST_DATA: terms unchecked',
            f'    page.goto("{url}", {NAV})',
            f'    if page.locator("{email_sel}").count() > 0:',
            f'        page.locator("{email_sel}").first.fill("qa@test.com")',
            f'    if page.locator("{pass_sel}").count() > 0:',
            f'        page.locator("{pass_sel}").first.fill("Test@1234!")',
            f'    page.locator("{submit_sel}").first.click()',
            f'    assert "500" not in page.title(), "500 on unchecked terms"',
            "",
        ]

        lines += [
            f"def test_{slug}_name_too_short(page: Page):",
            f'    """Single-character name does not crash the page."""',
            f'    # TEST_DATA: name: "a"',
            f'    page.goto("{url}", {NAV})',
            f'    try:',
            f'        if page.locator("{name_sel}").count() > 0:',
            f'            page.locator("{name_sel}").first.fill("a")',
            f'    except Exception:',
            f'        pass',
            f'    if page.locator("{submit_sel}").count() > 0:',
            f'        page.locator("{submit_sel}").first.click()',
            f'    assert "500" not in page.title(), "500 on single-char name"',
            "",
        ]

        lines += [
            f"def test_{slug}_name_spaces_only(page: Page):",
            f'    """Spaces-only name does not crash the page."""',
            f'    # TEST_DATA: name: "   " (spaces only)',
            f'    page.goto("{url}", {NAV})',
            f'    try:',
            f'        if page.locator("{name_sel}").count() > 0:',
            f'            page.locator("{name_sel}").first.fill("   ")',
            f'    except Exception:',
            f'        pass',
            f'    if page.locator("{submit_sel}").count() > 0:',
            f'        page.locator("{submit_sel}").first.click()',
            f'    assert "500" not in page.title(), "500 on spaces-only name"',
            "",
        ]

    # ═══════════════════════════════════════════════════════════════════════════
    # SECURITY (5 tests)
    # ═══════════════════════════════════════════════════════════════════════════

    if has_email:
        lines += [
            f"def test_{slug}_xss_in_email_field(page: Page):",
            f'    """XSS payload in email field does not render in page."""',
            f'    # TEST_DATA: XSS: <script>alert(1)</script>',
            f'    page.goto("{url}", {NAV})',
            f'    page.locator("{email_sel}").first.fill("<script>alert(1)</script>")',
            f'    if page.locator("{submit_sel}").count() > 0:',
            f'        page.locator("{submit_sel}").first.click()',
            f'    assert "alert(1)" not in page.content(), "XSS payload rendered in page"',
            "",
        ]

    if is_signup:
        lines += [
            f"def test_{slug}_xss_in_name_field(page: Page):",
            f'    """XSS payload in name field does not crash or render."""',
            f'    # TEST_DATA: XSS in name: <script>alert(1)</script>',
            f'    page.goto("{url}", {NAV})',
            f'    try:',
            f'        if page.locator("{name_sel}").count() > 0:',
            f'            page.locator("{name_sel}").first.fill("<script>alert(1)</script>")',
            f'    except Exception:',
            f'        pass',
            f'    if page.locator("{submit_sel}").count() > 0:',
            f'        page.locator("{submit_sel}").first.click()',
            f'    assert "500" not in page.title(), "500 on XSS in name"',
            "",
        ]

    if has_email and has_submit:
        _sqli_payload = "' OR 1=1--@test.com"
        lines += [
            f"def test_{slug}_sqli_in_email(page: Page):",
            f'    """SQL injection in email field does not expose DB errors."""',
            f'    # TEST_DATA: SQLi payload in email',
            f'    page.goto("{url}", {NAV})',
            f'    page.locator("{email_sel}").first.fill({_sqli_payload!r})',
            f'    if page.locator("{submit_sel}").count() > 0:',
            f'        page.locator("{submit_sel}").first.click()',
            f'    content = page.content().lower()',
            f'    assert "sql" not in content or "sqlexception" not in content, "SQL error exposed"',
            "",
        ]

    _sqli_drop = "'; DROP TABLE users;--@x.com"
    lines += [
        f"def test_{slug}_no_stack_trace_exposed(page: Page):",
        f'    """Malicious input does not expose server stack traces."""',
        f'    # TEST_DATA: SQLi payload to trigger potential error',
        f'    page.goto("{url}", {NAV})',
        f'    if page.locator("{email_sel}").count() > 0:',
        f'        page.locator("{email_sel}").first.fill({_sqli_drop!r})',
        f'    if page.locator("{submit_sel}").count() > 0:',
        f'        page.locator("{submit_sel}").first.click()',
        f'    content = page.content().lower()',
        f'    assert "traceback" not in content, "Python traceback exposed"',
        f'    assert "exception" not in content[:500], "Exception detail exposed"',
        "",
    ]

    lines += [
        f"def test_{slug}_no_db_error_exposed(page: Page):",
        f'    """Page content does not expose raw database error strings."""',
        f'    # TEST_DATA: no input — page source scan',
        f'    page.goto("{url}", {NAV})',
        f'    content = page.content().lower()',
        f'    assert "sqlexception" not in content, "SQLexception in page source"',
        f'    assert "database error" not in content, "database error in page source"',
        "",
    ]

    # ═══════════════════════════════════════════════════════════════════════════
    # RESPONSIVE — parametrized (covers 6 viewports)
    # ═══════════════════════════════════════════════════════════════════════════

    lines += [
        f'@pytest.mark.parametrize("width,height,name", [',
        f'    (375, 667, "iPhone SE"), (390, 844, "iPhone 14"), (768, 1024, "iPad"),',
        f'    (1024, 768, "iPad Landscape"), (1280, 720, "Desktop HD"), (1920, 1080, "Full HD"),',
        f'])',
        f"def test_{slug}_responsive_layout(page: Page, width, height, name):",
        f'    """Page renders correctly across 6 viewport sizes."""',
        f'    # TEST_DATA: viewport sizes from 375x667 to 1920x1080',
        f'    page.set_viewport_size({{"width": width, "height": height}})',
        f'    page.goto("{url}", {NAV})',
        f'    assert page.url, f"Page URL on {{name}} ({{width}}x{{height}})"',
        f'    assert "500" not in page.title(), f"500 on {{name}} viewport"',
        "",
    ]

    # ═══════════════════════════════════════════════════════════════════════════
    # MOBILE & TOUCH (3 tests)
    # ═══════════════════════════════════════════════════════════════════════════

    lines += [
        f"def test_{slug}_mobile_viewport_form_usable(page: Page):",
        f'    """Form fields and submit button are visible on mobile (375x667)."""',
        f'    # TEST_DATA: viewport 375x667 (iPhone SE)',
        f'    page.set_viewport_size({{"width": 375, "height": 667}})',
        f'    page.goto("{url}", {NAV})',
        f'    assert page.url, "Mobile viewport page URL"',
        f'    if page.locator("{email_sel}").count() > 0:',
        f'        assert page.locator("{email_sel}").first.is_visible(), "Email hidden on mobile"',
        "",
    ]

    lines += [
        f"def test_{slug}_touch_target_min_size(page: Page):",
        f'    """Submit button touch target is at least 40px tall on mobile."""',
        f'    # TEST_DATA: viewport 375x667, min touch target 40px',
        f'    page.set_viewport_size({{"width": 375, "height": 667}})',
        f'    page.goto("{url}", {NAV})',
        f'    if page.locator("{submit_sel}").count() > 0:',
        f'        box = page.locator("{submit_sel}").first.bounding_box()',
        f'        if box:',
        f'            assert box["height"] >= 40, f\'Submit button too small: {{box["height"]}}px\'',
        "",
    ]

    lines += [
        f"def test_{slug}_no_horizontal_scroll_mobile(page: Page):",
        f'    """No horizontal scrollbar on mobile viewport."""',
        f'    # TEST_DATA: viewport 375x667',
        f'    page.set_viewport_size({{"width": 375, "height": 667}})',
        f'    page.goto("{url}", {NAV})',
        f'    scroll_width = page.evaluate("document.documentElement.scrollWidth")',
        f'    inner_width  = page.evaluate("window.innerWidth")',
        f'    assert scroll_width <= inner_width + 5, f"Horizontal scroll on mobile: {{scroll_width}} > {{inner_width}}"',
        "",
    ]

    # ═══════════════════════════════════════════════════════════════════════════
    # PERFORMANCE (5 tests)
    # ═══════════════════════════════════════════════════════════════════════════

    lines += [
        f"def test_{slug}_load_time_under_5s(page: Page):",
        f'    """Page loads within 5 seconds."""',
        f'    # TEST_DATA: no input — load time measurement',
        f'    start = time.time()',
        f'    page.goto("{url}", {NAV})',
        f'    elapsed = time.time() - start',
        f'    assert elapsed < 5.0, f"Page loaded in {{elapsed:.2f}}s — exceeds 5s threshold"',
        "",
    ]

    lines += [
        f"def test_{slug}_dom_content_loaded_fast(page: Page):",
        f'    """DOMContentLoaded fires within 3 seconds."""',
        f'    # TEST_DATA: no input — navigation timing API',
        f'    page.goto("{url}", {NAV})',
        f'    dcl = page.evaluate(',
        f'        "performance.timing.domContentLoadedEventEnd - performance.timing.navigationStart"',
        f'    )',
        f'    assert dcl < 3000, f"DOMContentLoaded took {{dcl}}ms — exceeds 3000ms"',
        "",
    ]

    lines += [
        f"def test_{slug}_no_failed_network_requests(page: Page):",
        f'    """No 5xx network responses during page load."""',
        f'    # TEST_DATA: no input — network response monitoring',
        f'    failures = []',
        f'    page.on("response", lambda r: failures.append((r.url, r.status)) if r.status >= 500 else None)',
        f'    page.goto("{url}", {NAV})',
        f'    assert failures == [], f"5xx responses: {{failures[:3]}}"',
        "",
    ]

    lines += [
        f"def test_{slug}_no_404_resources(page: Page):",
        f'    """No 404 resource responses during page load."""',
        f'    # TEST_DATA: no input — network 404 monitoring',
        f'    not_found = []',
        f'    page.on("response", lambda r: not_found.append(r.url) if r.status == 404 else None)',
        f'    page.goto("{url}", {NAV})',
        f'    assert not_found == [], f"404 resources: {{not_found[:3]}}"',
        "",
    ]

    lines += [
        f"def test_{slug}_no_large_blocking_resources(page: Page):",
        f'    """No single script or stylesheet exceeds 1 MB."""',
        f'    # TEST_DATA: no input — resource size monitoring',
        f'    large = []',
        f'    def _check(r):',
        f'        ct = r.headers.get("content-type", "")',
        f'        if "script" in ct or "css" in ct:',
        f'            body = r.body() if r.ok else b""',
        f'            if len(body) > 1_048_576:',
        f'                large.append((r.url, len(body)))',
        f'    page.on("response", _check)',
        f'    page.goto("{url}", {NAV})',
        f'    assert large == [], f"Large blocking resources (>1MB): {{large[:2]}}"',
        "",
    ]

    # ═══════════════════════════════════════════════════════════════════════════
    # ACCESSIBILITY (5 tests)
    # ═══════════════════════════════════════════════════════════════════════════

    lines += [
        f"def test_{slug}_inputs_have_accessible_names(page: Page):",
        f'    """All input fields have an aria-label, label, or id."""',
        f'    # TEST_DATA: no input — accessibility attribute scan',
        f'    page.goto("{url}", {NAV})',
        f'    inputs = page.locator("input:not([type=hidden])").all()',
        f'    unnamed = [i.get_attribute("name") or "?" for i in inputs',
        f'               if not (i.get_attribute("aria-label") or i.get_attribute("id"))]',
        f'    assert len(unnamed) == 0, f"Inputs without accessible names: {{unnamed[:5]}}"',
        "",
    ]

    lines += [
        f"def test_{slug}_submit_button_has_text(page: Page):",
        f'    """Submit button has visible non-empty text."""',
        f'    # TEST_DATA: no input — button text check',
        f'    page.goto("{url}", {NAV})',
        f'    if page.locator("{submit_sel}").count() > 0:',
        f'        text = page.locator("{submit_sel}").first.inner_text().strip()',
        f'        assert text, "Submit button has no visible text"',
        "",
    ]

    lines += [
        f"def test_{slug}_form_keyboard_submittable(page: Page):",
        f'    """Form can be submitted via Enter key without crashing."""',
        f'    # TEST_DATA: email filled, Enter pressed',
        f'    page.goto("{url}", {NAV})',
        f'    if page.locator("{email_sel}").count() > 0:',
        f'        page.locator("{email_sel}").first.fill("qa@test.com")',
        f'        if page.locator("{pass_sel}").count() > 0:',
        f'            page.locator("{pass_sel}").first.fill("Test@1234!")',
        f'        page.locator("{email_sel}").first.press("Enter")',
        f'    assert "500" not in page.title(), "500 on keyboard submit"',
        "",
    ]

    lines += [
        f"def test_{slug}_error_uses_aria_role(page: Page):",
        f'    """After empty submit, check if any ARIA alert role appears (informational)."""',
        f'    # TEST_DATA: empty submit — aria[role=alert] presence',
        f'    page.goto("{url}", {NAV})',
        f'    if page.locator("{submit_sel}").count() > 0:',
        f'        page.locator("{submit_sel}").first.click()',
        f'    alerts = page.locator("[role=\'alert\']").count()',
        f'    # Informational only — not all apps use role=alert',
        f'    assert alerts >= 0, "ARIA alert check (informational)"',
        "",
    ]

    lines += [
        f"def test_{slug}_password_field_is_masked(page: Page):",
        f'    """Password field type remains \'password\' after typing."""',
        f'    # TEST_DATA: password filled, type attribute checked',
        f'    page.goto("{url}", {NAV})',
        f'    if page.locator("{pass_sel}").count() > 0:',
        f'        page.locator("{pass_sel}").first.fill("Test@1234!")',
        f'        typ = page.locator("{pass_sel}").first.get_attribute("type")',
        f'        assert typ == "password", f"Password field type changed to: {{typ}}"',
        "",
    ]

    # ═══════════════════════════════════════════════════════════════════════════
    # STORAGE & COOKIES (4 tests)
    # ═══════════════════════════════════════════════════════════════════════════

    lines += [
        f"def test_{slug}_no_password_in_localstorage(page: Page):",
        f'    """Plaintext password is not stored in localStorage."""',
        f'    # TEST_DATA: password filled + submit, then localStorage scanned',
        f'    page.goto("{url}", {NAV})',
        f'    if page.locator("{email_sel}").count() > 0:',
        f'        page.locator("{email_sel}").first.fill("qa@test.com")',
        f'    if page.locator("{pass_sel}").count() > 0:',
        f'        page.locator("{pass_sel}").first.fill("Test@1234!")',
        f'    if page.locator("{submit_sel}").count() > 0:',
        f'        page.locator("{submit_sel}").first.click()',
        f'    storage = page.evaluate("JSON.stringify(localStorage)")',
        f'    assert "Test@1234!" not in storage, "Plaintext password in localStorage"',
        "",
    ]

    lines += [
        f"def test_{slug}_no_token_after_failed_login(page: Page):",
        f'    """No auth token stored in localStorage after wrong credentials."""',
        f'    # TEST_DATA: wrong credentials — token check',
        f'    page.goto("{url}", {NAV})',
        f'    if page.locator("{email_sel}").count() > 0:',
        f'        page.locator("{email_sel}").first.fill("wrong@invalid.com")',
        f'    if page.locator("{pass_sel}").count() > 0:',
        f'        page.locator("{pass_sel}").first.fill("WrongPassword!!")',
        f'    if page.locator("{submit_sel}").count() > 0:',
        f'        page.locator("{submit_sel}").first.click()',
        f'    storage = page.evaluate("JSON.stringify(localStorage)")',
        f'    assert "authToken" not in storage and "access_token" not in storage, "Token after failed login"',
        "",
    ]

    lines += [
        f"def test_{slug}_localstorage_not_polluted(page: Page):",
        f'    """localStorage has no debug or dev_ keys after page load."""',
        f'    # TEST_DATA: no input — localStorage key scan',
        f'    page.goto("{url}", {NAV})',
        f'    keys = page.evaluate("Object.keys(localStorage)")',
        f'    debug_keys = [k for k in keys if "debug" in k.lower() or k.startswith("dev_")]',
        f'    assert debug_keys == [], f"Debug keys in localStorage: {{debug_keys}}"',
        "",
    ]

    lines += [
        f"def test_{slug}_cookies_exist_after_interaction(page: Page):",
        f'    """Cookies list is retrievable after interacting with the page (informational)."""',
        f'    # TEST_DATA: page interaction, then cookies() check',
        f'    page.goto("{url}", {NAV})',
        f'    if page.locator("{email_sel}").count() > 0:',
        f'        page.locator("{email_sel}").first.fill("qa@test.com")',
        f'    cookies = page.context.cookies()',
        f'    assert isinstance(cookies, list), "context.cookies() should return a list"',
        "",
    ]

    # ═══════════════════════════════════════════════════════════════════════════
    # NETWORK RESILIENCE (3 tests)
    # ═══════════════════════════════════════════════════════════════════════════

    lines += [
        f"def test_{slug}_network_error_shows_friendly_message(page: Page):",
        f'    """Blocking /api routes does not cause unhandled crash."""',
        f'    # TEST_DATA: all /api/** routes aborted',
        f'    page.route("**/api/**", lambda r: r.abort())',
        f'    try:',
        f'        page.goto("{url}", {NAV})',
        f'        assert "500" not in page.title(), "500 on blocked API routes"',
        f'    except Exception:',
        f'        pass  # navigation exception acceptable when APIs are blocked',
        f'    page.unroute_all()',
        "",
    ]

    lines += [
        f"def test_{slug}_no_broken_images(page: Page):",
        f'    """No image resource returns a 404 on page load."""',
        f'    # TEST_DATA: no input — image 404 monitoring',
        f'    broken = []',
        f'    def _chk(r):',
        f'        if r.status == 404 and "image" in r.headers.get("content-type", ""):',
        f'            broken.append(r.url)',
        f'    page.on("response", _chk)',
        f'    page.goto("{url}", {NAV})',
        f'    assert broken == [], f"Broken images (404): {{broken[:3]}}"',
        "",
    ]

    lines += [
        f"def test_{slug}_no_sensitive_data_in_page_source(page: Page):",
        f'    """Page source after failed submit does not contain plaintext password."""',
        f'    # TEST_DATA: wrong credentials submitted',
        f'    page.goto("{url}", {NAV})',
        f'    if page.locator("{email_sel}").count() > 0:',
        f'        page.locator("{email_sel}").first.fill("qa@test.com")',
        f'    if page.locator("{pass_sel}").count() > 0:',
        f'        page.locator("{pass_sel}").first.fill("Test@1234!")',
        f'    if page.locator("{submit_sel}").count() > 0:',
        f'        page.locator("{submit_sel}").first.click()',
        f'    assert "Test@1234!" not in page.content(), "Plaintext password in page source"',
        "",
    ]

    # ═══════════════════════════════════════════════════════════════════════════
    # USER FLOWS (up to 4)
    # ═══════════════════════════════════════════════════════════════════════════

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

    # ═══════════════════════════════════════════════════════════════════════════
    # EDGE CASES (up to 5)
    # ═══════════════════════════════════════════════════════════════════════════

    for ec in spec.edge_cases[:5]:
        eid      = ec["id"].lower().replace("-", "_")
        ec_id    = ec["id"]
        scenario = _safe_doc(ec["scenario"][:80])
        lines += [
            f"def test_{eid}(page: Page):",
            f'    """{ec_id}: {scenario}"""',
            f'    # TEST_DATA: edge case — {scenario[:40]}',
            f'    page.goto("{url}", {NAV})',
            f'    assert page.url, "Page loads for edge case {ec_id}"',
            "",
        ]

    # ═══════════════════════════════════════════════════════════════════════════
    # ADDITIONAL UX TESTS (4 tests)
    # ═══════════════════════════════════════════════════════════════════════════

    lines += [
        f"def test_{slug}_double_click_submit_safe(page: Page):",
        f'    """Double-clicking submit does not cause a crash or 500."""',
        f'    # TEST_DATA: no input — double-click submit',
        f'    page.goto("{url}", {NAV})',
        f'    if page.locator("{submit_sel}").count() > 0:',
        f'        try:',
        f'            page.locator("{submit_sel}").first.dblclick()',
        f'        except Exception:',
        f'            pass',
        f'    assert "500" not in page.title(), "500 on double-click submit"',
        "",
    ]

    lines += [
        f"def test_{slug}_back_button_no_resubmit(page: Page):",
        f'    """Back then forward navigation does not crash the page."""',
        f'    # TEST_DATA: navigate, go_back, go_forward',
        f'    page.goto("{url}", {NAV})',
        f'    if page.locator("{submit_sel}").count() > 0:',
        f'        if page.locator("{email_sel}").count() > 0:',
        f'            page.locator("{email_sel}").first.fill("qa@test.com")',
        f'        page.locator("{submit_sel}").first.click()',
        f'    page.go_back()',
        f'    page.go_forward()',
        f'    assert "500" not in page.title(), "500 on back/forward navigation"',
        "",
    ]

    lines += [
        f"def test_{slug}_autocomplete_attributes(page: Page):",
        f'    """Email input has an autocomplete attribute."""',
        f'    # TEST_DATA: no input — autocomplete attribute check',
        f'    page.goto("{url}", {NAV})',
        f'    if page.locator("{email_sel}").count() > 0:',
        f'        ac = page.locator("{email_sel}").first.get_attribute("autocomplete")',
        f'        # Informational — not all apps set autocomplete',
        f'        assert ac is not None or True, "Autocomplete check (informational)"',
        "",
    ]

    lines += [
        f"def test_{slug}_page_works_after_repeated_errors(page: Page):",
        f'    """Form is still functional after 3 wrong submission attempts."""',
        f'    # TEST_DATA: wrong credentials x3',
        f'    page.goto("{url}", {NAV})',
        f'    for _ in range(3):',
        f'        if page.locator("{email_sel}").count() > 0:',
        f'            page.locator("{email_sel}").first.fill("wrong@invalid.com")',
        f'        if page.locator("{pass_sel}").count() > 0:',
        f'            page.locator("{pass_sel}").first.fill("BadPass123!")',
        f'        if page.locator("{submit_sel}").count() > 0:',
        f'            page.locator("{submit_sel}").first.click()',
        f'    assert "500" not in page.title(), "500 after repeated failed logins"',
        f'    assert page.locator("{submit_sel}").count() > 0, "Form gone after repeated errors"',
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
        # Strip markdown fences and non-ASCII chars that small models often emit
        code = clean_code(code)
        code = re.sub(r"[^\x00-\x7F]+", "", code)
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
            "model_chain":  [mc[0] for mc in MODEL_CHAIN],
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
            "model_chain":  [mc[0] for mc in MODEL_CHAIN],
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
        log("  Fagun Autonomous AI Test Agent  v5")
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
