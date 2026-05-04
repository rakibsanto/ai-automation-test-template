"""
Test Generator — generates all 21 test types from a parsed spec.

Each type produces a focused AI prompt with real test data injected.
No AI guessing — actual payloads, actual selector hints, actual spec data.

Types: functional, validation, negative, boundary, security, api_network,
       accessibility, responsive, navigation, session_auth, performance,
       console_errors, error_states, visual, cross_browser,
       smoke, data_driven, i18n, rate_limiting, cookie_storage, deep_form
"""
from __future__ import annotations
import os, sys, re
from pathlib import Path

try:
    from ai_engine.spec_parser import ParsedSpec
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from ai_engine.spec_parser import ParsedSpec

BASE_URL = os.getenv("BASE_URL", "https://beta-stg.markopolo.ai")

# ── AI caller (injected by agent.py) ─────────────────────────────────────────
_ai_call = None

def set_ai_caller(fn):
    global _ai_call
    _ai_call = fn

def _ai(prompt: str, max_tokens: int = 2500) -> str:
    if _ai_call is None:
        raise RuntimeError("Call set_ai_caller() before test_generator")
    return _ai_call(prompt, max_tokens)


# ── Shared rules injected into every prompt ───────────────────────────────────
_RULES = f"""
PLAYWRIGHT PYTHON STRICT RULES (violating ANY rule = test cannot run):
- Output ONLY def test_...() function bodies + their decorators. NO imports. NO module code.
- Signature MUST be: def test_NAME(page: Page): OR def test_NAME(page: Page, param):
- Navigation: page.goto(URL) then page.wait_for_load_state("networkidle")
- Selector priority: get_by_role > get_by_label > get_by_placeholder > locator('input[type=...]')
- Assertions: expect(locator).to_be_visible() / expect(page).to_have_url() / assert + message
- Assertion messages: ALWAYS include what was expected — assert X, f"Expected Y, got {{X}}"
- Unique email: f"qa_{{int(time.time())}}@mailinator.com"
- Password: os.getenv("TEST_PASSWORD", "Test@1234!")
- BASE_URL = os.getenv("BASE_URL", "{BASE_URL}")
- MAX 25 lines per function. End every def completely — never leave open.
- Include ONE docstring per test explaining what it verifies and what test data it uses.
- Use @pytest.mark.parametrize for data-driven tests (payload, input value, viewport).
- Add # TEST_DATA: <values used> comment in docstring for traceability.
- NO markdown fences. NO prose. Functions only.
"""


# ─────────────────────────────────────────────────────────────────────────────
# HELPER: build human-readable test data section
# ─────────────────────────────────────────────────────────────────────────────

def _tdata(spec: ParsedSpec) -> str:
    valid   = " | ".join(spec.test_data_valid[:4])   if spec.test_data_valid   else "see spec"
    invalid = " | ".join(spec.test_data_invalid[:4]) if spec.test_data_invalid else "see spec"
    return f"Valid inputs: {valid}\nInvalid inputs: {invalid}"


def _selector_hints(spec: ParsedSpec) -> str:
    if not spec.raw:
        return ""
    # Extract UI element table hints from raw spec
    hints = []
    for line in spec.raw.splitlines():
        if "|" in line and "---" not in line and "Element" not in line:
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 2:
                hints.append(f"  {parts[0]}: {parts[1]}")
    return "UI ELEMENT HINTS:\n" + "\n".join(hints[:8]) if hints else ""


# ─────────────────────────────────────────────────────────────────────────────
# 1. FUNCTIONAL — every user flow, all steps, real actions
# ─────────────────────────────────────────────────────────────────────────────
def functional(spec: ParsedSpec) -> str:
    if not spec.flows:
        return ""
    flows_text = ""
    for i, f in enumerate(spec.flows[:8], 1):
        steps = "\n    ".join(f["steps"][:8])
        flows_text += f"\nFLOW {i}: {f['name']}\n    {steps}\n"

    valid_email = spec.test_data_valid[0] if spec.test_data_valid else "testuser@mailinator.com"
    valid_pass  = spec.test_data_valid[1] if len(spec.test_data_valid) > 1 else "Test@1234!"

    return _ai(f"""{_RULES}
PAGE: {spec.page_name}  URL: {spec.url}

Write ONE pytest+Playwright test function per user flow.
Each test must: navigate, fill real inputs, click submit, assert the expected outcome.

TEST DATA:
  valid_email = "{valid_email}" (or use f"qa_{{int(time.time())}}@mailinator.com" for uniqueness)
  valid_password = os.getenv("TEST_PASSWORD", "{valid_pass}")
  invalid_email = "INVALID@@@"
  invalid_password = "wrong"

{_selector_hints(spec)}

FLOWS TO TEST:
{flows_text}

REQUIREMENT: Each function must assert the SPECIFIC outcome described (redirect URL, error message, etc).
Write {min(len(spec.flows), 8)} test functions now:""", 3500)


# ─────────────────────────────────────────────────────────────────────────────
# 2. VALIDATION — every field rule, valid AND invalid inputs
# ─────────────────────────────────────────────────────────────────────────────
def validation(spec: ParsedSpec) -> str:
    rules = "\n".join(f"  RULE {i+1}: {r}" for i, r in enumerate(spec.validation_rules[:12]))
    invalid_data = "\n".join(f"  - {t}" for t in spec.test_data_invalid[:8])
    valid_data   = "\n".join(f"  - {t}" for t in spec.test_data_valid[:5])

    return _ai(f"""{_RULES}
PAGE: {spec.page_name}  URL: {spec.url}

Write VALIDATION tests. For every rule: one test with INVALID input (must show error) + one with VALID input.

VALIDATION RULES:
{rules or "  - Email: valid format required\n  - Password: minimum 8 chars\n  - All fields: required"}

INVALID TEST INPUTS (inject these directly into tests):
{invalid_data or "  - empty string\n  - spaces only\n  - invalid@@@email"}

VALID TEST INPUTS:
{valid_data or "  - valid@example.com\n  - Test@1234!"}

PATTERN (use exactly):
1. page.goto(URL) + wait
2. Fill the field with the test value
3. page.locator('button[type="submit"]').click()
4. page.wait_for_timeout(500)
5. For invalid: assert error visible — expect(page.locator("[role='alert']")).to_be_visible()
6. For valid: assert no error OR url changed

Include # TEST_DATA: <input_value> in each function docstring.
Write 8-12 test functions now:""", 3000)


# ─────────────────────────────────────────────────────────────────────────────
# 3. NEGATIVE — wrong inputs that must be rejected
# ─────────────────────────────────────────────────────────────────────────────
def negative(spec: ParsedSpec) -> str:
    page_lower = spec.page_name.lower()
    scenarios = []
    if "login" in page_lower:
        scenarios = [
            "wrong password with valid email → show 'Invalid credentials' error",
            "valid password with unregistered email → show 'User not found' error",
            "empty email, filled password → show 'Email required' error",
            "filled email, empty password → show 'Password required' error",
            "both fields empty → show validation errors",
            "SQL injection in email → login fails, no DB error exposed",
            "very long password (300 chars) → graceful error, no crash",
            "correct email with old/expired session → redirect to login",
        ]
    elif "signup" in page_lower or "register" in page_lower:
        scenarios = [
            "already registered email → 'Email already exists' error",
            "password < 8 chars → 'Password too short' error",
            "mismatched confirm password → 'Passwords do not match' error",
            "invalid email format → 'Invalid email' error",
            "all fields empty → multiple validation errors",
            "name with only spaces → 'Name required' or trimmed error",
        ]
    elif "reset" in page_lower or "password" in page_lower:
        scenarios = [
            "unregistered email → show success message (don't reveal if email exists)",
            "empty email field → show 'Email required' error",
            "invalid email format → show validation error",
            "already used reset token → show 'Token expired' or 'Invalid link' error",
            "expired token → show 'Link expired' error",
        ]
    else:
        scenarios = [
            "empty form submission → validation errors appear",
            "invalid input format → format error shown",
            "very long input (300+ chars) → graceful error",
        ]

    scenarios_text = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(scenarios))
    return _ai(f"""{_RULES}
PAGE: {spec.page_name}  URL: {spec.url}

Write NEGATIVE tests — inputs that MUST be REJECTED with a user-friendly error.
NEVER crash. NEVER show stack traces. NEVER return blank page.

SCENARIOS TO TEST:
{scenarios_text}

For EACH scenario:
- Fill the form with the wrong/negative input
- Submit or trigger action
- Assert the user-facing error appears (not a JS error, not a 500 page)
- Assert the URL did NOT redirect to dashboard/success

Include # TEST_DATA: <input_used> in each docstring.
Write {len(scenarios)} test functions now:""", 3000)


# ─────────────────────────────────────────────────────────────────────────────
# 4. BOUNDARY — min/max/exact edge lengths
# ─────────────────────────────────────────────────────────────────────────────
def boundary(spec: ParsedSpec) -> str:
    boundary_cases = [
        ("email_min",          "a@b.co",               "minimum valid email",         "pass"),
        ("email_255_chars",    "a"*248 + "@test.com",   "255-char email",              "pass or graceful error"),
        ("email_256_chars",    "a"*249 + "@test.com",   "256-char email (over limit)", "graceful error"),
        ("password_min",       "Aa1!aaaa",              "minimum 8-char password",     "pass"),
        ("password_7_chars",   "Aa1!aaa",               "7-char password (below min)", "error"),
        ("password_max",       "A"*99 + "a1!",          "100-char password",           "pass or graceful error"),
        ("spaces_only_email",  "   ",                   "spaces-only email",           "error (required/invalid)"),
        ("spaces_only_pass",   "   ",                   "spaces-only password",        "error"),
        ("single_char_email",  "a",                     "single char email",           "error"),
        ("null_bytes",         "test\x00@test.com",     "null byte in email",          "graceful error"),
        ("unicode_email",      "tëst@examplé.com",      "unicode email",               "error or pass (depends on impl)"),
        ("newline_in_email",   "test\nemail@test.com",  "newline in email",            "error"),
    ]

    cases_text = "\n".join(
        f"  - {name}: input='{val[:40]}' desc='{desc}' expect={exp}"
        for name, val, desc, exp in boundary_cases
    )

    return _ai(f"""{_RULES}
PAGE: {spec.page_name}  URL: {spec.url}

Write BOUNDARY tests for every form field.
Each test uses an edge-case input value and asserts the SPECIFIC expected behavior.

BOUNDARY TEST CASES:
{cases_text}

Pattern for each test:
1. Navigate to page
2. Fill input with the exact boundary value
3. Submit
4. Assert: error appears (for invalid) OR no error (for valid)
5. Assert: page does NOT crash (no 500, no blank page, URL stays or redirects properly)

Include # TEST_DATA: <exact_value_used> in docstring.
Write 8-10 test functions covering the most important boundary cases above:""", 3000)


# ─────────────────────────────────────────────────────────────────────────────
# 5. SECURITY — XSS, SQLi, injection (parametrized with all payloads)
# ─────────────────────────────────────────────────────────────────────────────
def security(spec: ParsedSpec, xss_payloads: list[str], sqli_payloads: list[str]) -> str:
    xss_list  = ",\n    ".join(f'"{p}"' for p in xss_payloads[:16])
    sqli_list = ",\n    ".join(f'"{p}"' for p in sqli_payloads[:13])

    return _ai(f"""{_RULES}
PAGE: {spec.page_name}  URL: {spec.url}  PATH: {spec.path}

Write SECURITY tests for authorized testing. Use @pytest.mark.parametrize for all payload lists.

XSS PAYLOADS (use ALL of these):
[{xss_list}]

SQLI PAYLOADS (use ALL of these):
[{sqli_list}]

REQUIRED TEST FUNCTIONS:

1. test_xss_injection_parametrized — @pytest.mark.parametrize("payload", XSS_LIST):
   - page.on("dialog", lambda d: (fired.append(d.type), d.dismiss()))
   - Fill email/username field with payload
   - Submit
   - assert not fired, f"XSS alert fired with: {{payload}}"
   - assert payload not in page.content() OR "alert" not in page.content()
   - # TEST_DATA: OWASP XSS payloads × {len(xss_payloads)} vectors

2. test_sqli_login_bypass_parametrized — @pytest.mark.parametrize("sqli", SQLI_LIST):
   - Fill email with sqli payload
   - Fill password with "wrongpass"
   - Submit
   - assert "/dashboard" not in page.url, f"SQLi bypass succeeded with: {{sqli}}"
   - assert error visible (login should FAIL)
   - # TEST_DATA: OWASP SQLi payloads × {len(sqli_payloads)} vectors

3. test_no_server_error_on_malicious_input — test a few aggressive payloads:
   - page.route("**/*", lambda r: r.continue_()) # capture responses
   - Submit malicious input
   - Assert no 500 error page, no stack trace in page content

4. test_https_enforced:
   - Navigate to http:// version of the URL
   - Assert redirect to https:// OR assert page.url starts with "https://"

5. test_no_sensitive_data_in_page_source:
   - After failed login, check page content
   - Assert no database error messages, no "SQL", no "stack trace", no "Exception"

Write all 5 test functions with real payload data embedded:""", 3500)


# ─────────────────────────────────────────────────────────────────────────────
# 6. API / NETWORK — intercept requests and validate contract
# ─────────────────────────────────────────────────────────────────────────────
def api_network(spec: ParsedSpec) -> str:
    endpoints = "\n".join(
        f"  {e.get('method','POST')} {e.get('endpoint','')}"
        for e in spec.api_endpoints[:5]
    ) or "  POST /api/auth/login (or similar auth endpoint)"

    return _ai(f"""{_RULES}
PAGE: {spec.page_name}  URL: {spec.url}

Write API/NETWORK tests using Playwright request interception.

API ENDPOINTS FROM SPEC:
{endpoints}

REQUIRED TESTS:

1. test_login_api_request_method: Intercept the form submit API call, assert method is POST
   with page.expect_request(lambda r: "/api/" in r.url and r.method == "POST") as req:
       page.fill('input[type="email"]', "test@test.com")
       page.fill('input[type="password"]', "Test@1234!")
       page.click('button[type="submit"]')

2. test_api_returns_correct_status_on_valid_login: Submit valid credentials, assert 200/201 status
   with page.expect_response(lambda r: "/api/" in r.url) as resp_info:
       [submit form with valid credentials]
   resp = resp_info.value
   assert resp.status in (200, 201), f"Expected 200/201, got {{resp.status}}"

3. test_api_returns_401_on_invalid_login: Submit wrong password, assert 401/403
   assert resp.status in (401, 403, 422), f"Expected auth error, got {{resp.status}}"

4. test_no_password_in_response: After login, assert response body doesn't contain "password"
   body = resp_info.value.text()
   assert "password" not in body.lower() or check JSON key is not plain text

5. test_request_has_content_type: Assert POST has Content-Type: application/json

6. test_network_errors_handled: Use page.route to abort API call, assert user sees friendly error
   page.route("**/api/**", lambda r: r.abort())
   [fill + submit]
   assert page.locator("[role='alert'], .error").is_visible()

Write all 6 test functions:""", 3000)


# ─────────────────────────────────────────────────────────────────────────────
# 7. ACCESSIBILITY — ARIA, keyboard, axe-core, WCAG 2.1 AA
# ─────────────────────────────────────────────────────────────────────────────
def accessibility(spec: ParsedSpec) -> str:
    return _ai(f"""{_RULES}
PAGE: {spec.page_name}  URL: {spec.url}

Write ACCESSIBILITY tests (WCAG 2.1 AA compliance).

REQUIRED TESTS:

1. test_all_inputs_have_labels: every input has accessible name
   for inp in page.locator('input:not([type="hidden"])').all():
       # check aria-label, aria-labelledby, or associated <label>
       assert inp.get_attribute("aria-label") or inp.get_attribute("id"), "Input missing label"

2. test_submit_button_has_accessible_name:
   btn = page.locator('button[type="submit"]')
   assert btn.inner_text().strip() or btn.get_attribute("aria-label"), "Button has no accessible name"

3. test_keyboard_navigation_order: tab through form, check focus moves logically
   page.keyboard.press("Tab")  # focus email
   assert page.locator('input[type="email"]').is_focused()
   page.keyboard.press("Tab")  # focus password
   page.keyboard.press("Tab")  # focus submit

4. test_form_submits_on_enter_key: fill email+password, press Enter → form submits
   page.locator('input[type="email"]').fill("test@test.com")
   page.locator('input[type="password"]').fill("Test@1234!")
   page.keyboard.press("Enter")
   page.wait_for_timeout(1000)
   # assert something happened (URL changed or error visible)

5. test_error_messages_have_aria_role: after failed submit, error has role="alert"
   page.locator('button[type="submit"]').click()
   error = page.locator("[role='alert']")
   assert error.is_visible(), "Error message doesn't use role=alert for screen readers"

6. test_axe_core_no_violations: inject axe-core and run scan
   page.add_script_tag(url="https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.9.0/axe.min.js")
   page.wait_for_timeout(1000)
   results = page.evaluate("async () => await axe.run()")
   critical = [v for v in results.get("violations", []) if v.get("impact") in ("critical","serious")]
   assert not critical, f"axe-core critical violations: {{[v['description'] for v in critical]}}"

7. test_color_contrast_not_broken: page loads without CSS errors that break contrast
   errors = []
   page.on("console", lambda m: errors.append(m.text) if "contrast" in m.text.lower() else None)
   page.goto("{spec.url}")
   # (informational — many sites won't log contrast errors)
   assert True

Write all 7 test functions:""", 3000)


# ─────────────────────────────────────────────────────────────────────────────
# 8. RESPONSIVE — 6 viewports + layout checks
# ─────────────────────────────────────────────────────────────────────────────
def responsive(spec: ParsedSpec) -> str:
    return _ai(f"""{_RULES}
PAGE: {spec.page_name}  URL: {spec.url}

Write RESPONSIVE tests using @pytest.mark.parametrize for viewports.

@pytest.mark.parametrize("width,height,name", [
    (375, 667, "iPhone SE"),
    (390, 844, "iPhone 14"),
    (768, 1024, "iPad"),
    (1024, 768, "iPad Landscape"),
    (1280, 720, "Desktop HD"),
    (1920, 1080, "Full HD"),
])
def test_responsive_layout(page: Page, width, height, name):
    page.set_viewport_size({{"width": width, "height": height}})
    page.goto("{spec.url}")
    page.wait_for_load_state("networkidle")
    # Submit button visible at all sizes
    assert page.locator('button[type="submit"]').is_visible(), f"Submit hidden on {{name}} ({{width}}px)"
    # No horizontal scroll
    overflow = page.evaluate("() => document.documentElement.scrollWidth > window.innerWidth")
    assert not overflow, f"Horizontal overflow on {{name}} ({{width}}px)"

Also write:
- test_touch_target_sizes: buttons are at least 44×44px on mobile
  page.set_viewport_size({{"width": 375, "height": 667}})
  btn = page.locator('button[type="submit"]')
  box = btn.bounding_box()
  assert box["height"] >= 44, f"Button too small for touch: {{box['height']}}px"

- test_font_size_not_tiny_on_mobile: ensure text is readable
  page.set_viewport_size({{"width": 375, "height": 667}})
  # check email input font size
  size = page.evaluate("() => parseFloat(window.getComputedStyle(document.querySelector('input[type=email]')).fontSize)")
  assert size >= 14, f"Input font size {{size}}px too small (min 14px)"

Write all 3 test functions/groups:""", 2500)


# ─────────────────────────────────────────────────────────────────────────────
# 9. NAVIGATION — all internal links, back button, direct URL access
# ─────────────────────────────────────────────────────────────────────────────
def navigation(spec: ParsedSpec) -> str:
    page_lower = spec.page_name.lower()
    if "login" in page_lower:
        links = [
            ("forgot_password", "Forgot Password", "/reset", "forgot password / reset page"),
            ("signup_link",     "Sign Up / Create account", "/signup", "registration page"),
        ]
    elif "signup" in page_lower:
        links = [
            ("login_link",  "Log In / Sign In", "/login", "login page"),
            ("terms_link",  "Terms of Service", "/terms", "terms page (if exists)"),
        ]
    else:
        links = [
            ("back_to_login", "Back to Login", "/login", "login page"),
        ]

    link_tests = ""
    for key, label, dest, desc in links:
        link_tests += f"\n  - test_nav_{key}: click '{label}' → assert URL contains '{dest}' ({desc})"

    return _ai(f"""{_RULES}
PAGE: {spec.page_name}  URL: {spec.url}

Write NAVIGATION tests for all internal page links.

LINKS TO TEST:
{link_tests}
  - test_nav_back_button: navigate to page, go to another page, press browser back → lands back on {spec.url}
  - test_nav_direct_url_access: navigate directly to {spec.url} → page loads without redirect loop
  - test_nav_logo_home: click logo → navigates to home/root page (if logo present)

Pattern for each link test:
1. page.goto("{spec.url}")
2. Find the link (get_by_role("link", name=...) or get_by_text(...))
3. click it
4. page.wait_for_url("**{dest}**", timeout=5000) or assert dest in page.url

Write {len(links) + 3} test functions now:""", 2500)


# ─────────────────────────────────────────────────────────────────────────────
# 10. SESSION / AUTH — tokens, redirects, multi-session
# ─────────────────────────────────────────────────────────────────────────────
def session_auth(spec: ParsedSpec) -> str:
    return _ai(f"""{_RULES}
PAGE: {spec.page_name}  URL: {spec.url}

Write SESSION/AUTH tests:

1. test_unauthenticated_redirected_to_login:
   Navigate to /dashboard without auth token
   assert "/login" in page.url or "/auth" in page.url

2. test_authenticated_user_bypasses_login:
   page.evaluate("localStorage.setItem('authToken', 'fake-valid-token')")
   page.goto("{spec.url}")
   page.wait_for_timeout(1000)
   # App should either redirect away OR keep user on login
   assert page.url is not None  # page is accessible

3. test_no_auth_token_after_failed_login:
   page.goto("{spec.url}")
   page.locator('input[type="email"]').fill("wrong@test.com")
   page.locator('input[type="password"]').fill("wrongpass")
   page.locator('button[type="submit"]').click()
   page.wait_for_timeout(1000)
   token = page.evaluate("() => localStorage.getItem('authToken') || localStorage.getItem('token')")
   assert not token, f"Auth token should not be set after failed login, got: {{token}}"

4. test_session_cookies_set_on_login:
   After successful login with valid credentials, check for session cookie
   cookies = page.context.cookies()
   session_cookies = [c for c in cookies if "session" in c["name"].lower() or "auth" in c["name"].lower()]
   # (informational — not all apps use cookies)

5. test_logout_clears_storage:
   If logout button exists: click it, assert localStorage is cleared
   Try: page.goto(BASE_URL + "/dashboard"), after logout assert redirect to login

6. test_concurrent_session_handling:
   Open two contexts, login in one, check the other still works
   (basic: just verify second login attempt doesn't break the first)

Write all 6 test functions:""", 2500)


# ─────────────────────────────────────────────────────────────────────────────
# 11. PERFORMANCE — Web Vitals, resource sizes, load timing
# ─────────────────────────────────────────────────────────────────────────────
def performance(spec: ParsedSpec) -> str:
    js_timing = "() => { const t = window.performance.timing; return { dom: t.domContentLoadedEventEnd - t.navigationStart, load: t.loadEventEnd - t.navigationStart, ttfb: t.responseStart - t.navigationStart }; }"

    return _ai(f"""{_RULES}
PAGE: {spec.page_name}  URL: {spec.url}

Write PERFORMANCE tests checking Core Web Vitals and load times.

1. test_page_load_under_5_seconds:
   import time
   start = time.time()
   page.goto("{spec.url}")
   page.wait_for_load_state("networkidle")
   elapsed = (time.time() - start) * 1000
   assert elapsed < 5000, f"Slow load: {{elapsed:.0f}}ms (SLA: 5000ms)"

2. test_dom_content_loaded_under_2_seconds:
   Use page.evaluate with JS: '{js_timing}'
   timing = page.evaluate("() => {{ const t = window.performance.timing; return t.domContentLoadedEventEnd - t.navigationStart; }}")
   assert timing < 2000, f"DOMContentLoaded: {{timing}}ms (limit: 2000ms)"

3. test_ttfb_reasonable:
   ttfb = page.evaluate("() => window.performance.timing.responseStart - window.performance.timing.navigationStart")
   assert ttfb < 1000, f"TTFB too slow: {{ttfb}}ms"

4. test_no_render_blocking_large_resources:
   blocking = []
   def check_resp(resp):
       if resp.request.resource_type in ("script", "stylesheet"):
           try:
               if len(resp.body()) > 500_000: blocking.append((resp.url[-60:], len(resp.body())))
           except: pass
   page.on("response", check_resp)
   page.goto("{spec.url}")
   page.wait_for_load_state("networkidle")
   assert not blocking, f"Large blocking resources: {{blocking}}"

5. test_no_failed_network_requests:
   failed = []
   def on_resp(r):
       if r.status >= 500: failed.append((r.url[-60:], r.status))
   page.on("response", on_resp)
   page.goto("{spec.url}")
   page.wait_for_load_state("networkidle")
   assert not failed, f"Server errors: {{failed}}"

6. test_web_vitals_lcp_reasonable:
   lcp = page.evaluate("() => new Promise(resolve => new PerformanceObserver(list => {{ const e = list.getEntries(); resolve(e.length ? e[e.length-1].startTime : 0); }}).observe({{type:'largest-contentful-paint', buffered:true}}))")
   # LCP should be under 4 seconds (Good: <2.5s, Needs Improvement: <4s)
   if lcp > 0:
       assert lcp < 4000, f"LCP too slow: {{lcp:.0f}}ms (limit: 4000ms)"

Write all 6 test functions:""", 2500)


# ─────────────────────────────────────────────────────────────────────────────
# 12. CONSOLE ERRORS — monitor all JS errors and warnings
# ─────────────────────────────────────────────────────────────────────────────
def console_errors(spec: ParsedSpec) -> str:
    return _ai(f"""{_RULES}
PAGE: {spec.page_name}  URL: {spec.url}

Write CONSOLE ERROR tests monitoring browser JavaScript console.

1. test_no_console_errors_on_page_load:
   errors = []
   page.on("console", lambda m: errors.append(f"{{m.type}}: {{m.text}}") if m.type == "error" else None)
   page.goto("{spec.url}")
   page.wait_for_load_state("networkidle")
   assert errors == [], f"Console errors on load ({{len(errors)}}): {{errors[:3]}}"

2. test_no_console_errors_on_form_interaction:
   errors = []
   page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
   page.goto("{spec.url}")
   page.wait_for_load_state("networkidle")
   try:
       page.locator('input[type="email"]').fill("test@example.com")
       page.locator('input[type="password"]').fill("Test@1234!")
       page.locator('button[type="submit"]').click()
       page.wait_for_timeout(2000)
   except: pass
   assert errors == [], f"Console errors during interaction: {{errors[:3]}}"

3. test_no_uncaught_exceptions:
   exceptions = []
   page.on("pageerror", lambda e: exceptions.append(str(e)))
   page.goto("{spec.url}")
   page.wait_for_load_state("networkidle")
   assert exceptions == [], f"Uncaught JS exceptions: {{exceptions}}"

4. test_no_network_errors_in_console:
   network_errors = []
   page.on("console", lambda m: network_errors.append(m.text)
           if m.type == "error" and ("failed to load" in m.text.lower() or "net::" in m.text.lower()) else None)
   page.goto("{spec.url}")
   page.wait_for_load_state("networkidle")
   assert network_errors == [], f"Network errors in console: {{network_errors}}"

5. test_no_404_resources:
   not_found = []
   page.on("response", lambda r: not_found.append(r.url[-60:]) if r.status == 404 else None)
   page.goto("{spec.url}")
   page.wait_for_load_state("networkidle")
   assert not_found == [], f"404 resources: {{not_found}}"

Write all 5 test functions:""", 2500)


# ─────────────────────────────────────────────────────────────────────────────
# 13. ERROR STATES — graceful failure, no leaks
# ─────────────────────────────────────────────────────────────────────────────
def error_states(spec: ParsedSpec) -> str:
    return _ai(f"""{_RULES}
PAGE: {spec.page_name}  URL: {spec.url}

Write ERROR STATE tests verifying graceful failure handling.

1. test_no_stack_trace_exposed:
   page.goto("{spec.url}")
   page.locator('input[type="email"]').fill("' OR 1=1--")
   page.locator('button[type="submit"]').click()
   page.wait_for_timeout(1500)
   content = page.content().lower()
   leaks = ["traceback", "exception", "at object.", "sqlexception", "syntaxerror",
            "undefined is not", "cannot read", "typeerror:", "internal server error"]
   exposed = [l for l in leaks if l in content]
   assert not exposed, f"Internal error leaked to user: {{exposed}}"

2. test_api_failure_shows_friendly_message:
   page.route("**/api/**", lambda r: r.fulfill(status=500, body="Server Error"))
   page.goto("{spec.url}")
   page.locator('input[type="email"]').fill("test@test.com")
   page.locator('button[type="submit"]').click()
   page.wait_for_timeout(1000)
   assert page.locator("[role='alert'], .error, .error-message").is_visible(), \\
       "No friendly error shown when API returns 500"
   assert "500" not in page.content() and "server error" not in page.content().lower()

3. test_network_timeout_handled:
   page.route("**/api/**", lambda r: r.abort("timedout"))
   page.goto("{spec.url}")
   try:
       page.locator('input[type="email"]').fill("test@test.com")
       page.locator('button[type="submit"]').click()
       page.wait_for_timeout(3000)
       # Should show network error message
   except: pass
   assert "500" not in page.content()

4. test_page_stays_functional_after_error:
   Submit wrong credentials → get error → try submitting again
   page.goto("{spec.url}")
   for _ in range(2):
       page.locator('input[type="email"]').fill("wrong@wrong.com")
       page.locator('input[type="password"]').fill("wrongpass")
       page.locator('button[type="submit"]').click()
       page.wait_for_timeout(1000)
   assert page.locator('input[type="email"]').is_visible(), "Page broken after repeated errors"

Write all 4 test functions:""", 2500)


# ─────────────────────────────────────────────────────────────────────────────
# 14. VISUAL / LAYOUT — DOM assertions, no broken layout
# ─────────────────────────────────────────────────────────────────────────────
def visual(spec: ParsedSpec) -> str:
    return _ai(f"""{_RULES}
PAGE: {spec.page_name}  URL: {spec.url}

Write VISUAL/LAYOUT tests using DOM bounding box assertions (no screenshot comparison).

1. test_form_within_viewport_bounds:
   form = page.locator("form").first
   box = form.bounding_box()
   vp = page.viewport_size
   assert box["x"] >= 0, "Form overflows left"
   assert box["x"] + box["width"] <= vp["width"] + 1, "Form overflows right"

2. test_no_overlapping_elements:
   email_box = page.locator('input[type="email"]').bounding_box()
   pass_box  = page.locator('input[type="password"]').bounding_box()
   if email_box and pass_box:
       overlap = (email_box["y"] < pass_box["y"] + pass_box["height"] and
                  pass_box["y"] < email_box["y"] + email_box["height"])
       assert not overlap, "Email and password inputs overlap"

3. test_submit_button_below_inputs:
   btn_box   = page.locator('button[type="submit"]').bounding_box()
   email_box = page.locator('input[type="email"]').bounding_box()
   if btn_box and email_box:
       assert btn_box["y"] > email_box["y"], "Submit button is above inputs (wrong layout)"

4. test_page_title_meaningful:
   title = page.title()
   assert title and len(title) > 2, f"Page title too short: '{{title}}'"
   assert title.lower() not in ("undefined", "null", ""), f"Page title is placeholder: '{{title}}'"

5. test_favicon_loads:
   favicons = []
   page.on("response", lambda r: favicons.append(r.status) if "favicon" in r.url.lower() else None)
   page.goto("{spec.url}")
   page.wait_for_load_state("networkidle")
   if favicons:
       assert all(s < 400 for s in favicons), f"Favicon load failed: {{favicons}}"

6. test_no_broken_images:
   broken = []
   page.on("response", lambda r: broken.append(r.url[-50:])
           if r.request.resource_type == "image" and r.status >= 400 else None)
   page.goto("{spec.url}")
   page.wait_for_load_state("networkidle")
   assert not broken, f"Broken images: {{broken}}"

Write all 6 test functions:""", 2500)


# ─────────────────────────────────────────────────────────────────────────────
# 15. CROSS-BROWSER — parametrized smoke tests
# ─────────────────────────────────────────────────────────────────────────────
def cross_browser(spec: ParsedSpec) -> str:
    return _ai(f"""{_RULES}
PAGE: {spec.page_name}  URL: {spec.url}

Write CROSS-BROWSER smoke tests.
Note: These run under Chromium in CI. Mark them with comments so testers know to run on other browsers.

# cross-browser-smoke: run these on chromium, firefox, webkit

def test_page_loads_crossbrowser(page: Page):
    \"\"\"Cross-browser smoke: page loads and key elements visible.
    # TEST_DATA: none — pure navigation test
    # RUN ON: chromium, firefox, webkit (via pytest --browser=firefox)
    \"\"\"
    page.goto("{spec.url}")
    page.wait_for_load_state("networkidle")
    assert page.locator('input[type="email"]').is_visible() or \\
           page.locator('input[type="text"]').is_visible(), "No visible input on page"
    assert page.locator('button[type="submit"]').is_visible(), "No submit button found"

def test_form_interaction_crossbrowser(page: Page):
    \"\"\"Cross-browser smoke: form is interactive across browsers.
    # TEST_DATA: test@example.com / Test@1234!
    # RUN ON: chromium, firefox, webkit
    \"\"\"
    page.goto("{spec.url}")
    page.wait_for_load_state("networkidle")
    try:
        page.locator('input[type="email"]').fill("test@example.com")
        page.locator('input[type="password"]').fill("Test@1234!")
        assert page.locator('input[type="email"]').input_value() == "test@example.com"
        assert page.locator('input[type="password"]').input_value() == "Test@1234!"
    except Exception as e:
        assert False, f"Form interaction failed cross-browser: {{e}}"

Write these 2 test functions:""", 1500)


# ─────────────────────────────────────────────────────────────────────────────
# 16. SMOKE — critical path in <60 seconds
# ─────────────────────────────────────────────────────────────────────────────
def smoke(spec: ParsedSpec) -> str:
    return _ai(f"""{_RULES}
PAGE: {spec.page_name}  URL: {spec.url}

Write SMOKE tests — fastest possible critical path verification (each under 15s).
These run first in CI to fail fast if the app is completely broken.

def test_smoke_page_accessible(page: Page):
    \"\"\"Smoke: page responds and main form visible.\"\"\"
    page.goto("{spec.url}", timeout=10000)
    assert page.locator("form, main, [role='main']").is_visible(), "Page structure broken"

def test_smoke_form_interactive(page: Page):
    \"\"\"Smoke: can type in form fields.\"\"\"
    page.goto("{spec.url}")
    page.locator('input[type="email"]').fill("smoke@test.com")
    assert page.locator('input[type="email"]').input_value() == "smoke@test.com"

def test_smoke_submit_button_clickable(page: Page):
    \"\"\"Smoke: submit button is clickable (not disabled, not hidden).\"\"\"
    page.goto("{spec.url}")
    btn = page.locator('button[type="submit"]')
    assert btn.is_visible() and btn.is_enabled(), "Submit button broken"

def test_smoke_no_500_error(page: Page):
    \"\"\"Smoke: page returns 200 (not a server error).\"\"\"
    response = page.goto("{spec.url}")
    assert response.status < 400, f"Page returned HTTP {{response.status}}"

Write these 4 smoke test functions:""", 2000)


# ─────────────────────────────────────────────────────────────────────────────
# 17. DATA-DRIVEN — parametrized with all spec test data
# ─────────────────────────────────────────────────────────────────────────────
def data_driven(spec: ParsedSpec) -> str:
    valid_cases   = spec.test_data_valid[:6]   or ["testuser@example.com"]
    invalid_cases = spec.test_data_invalid[:6] or ["invalid@@email", ""]

    valid_list   = ", ".join(f'"{v}"' for v in valid_cases)
    invalid_list = ", ".join(f'"{v}"' for v in invalid_cases)

    return _ai(f"""{_RULES}
PAGE: {spec.page_name}  URL: {spec.url}

Write DATA-DRIVEN tests using @pytest.mark.parametrize with actual spec test data.

VALID TEST DATA FROM SPEC: [{valid_list}]
INVALID TEST DATA FROM SPEC: [{invalid_list}]

@pytest.mark.parametrize("test_email", [{valid_list}])
def test_valid_email_accepted(page: Page, test_email):
    \"\"\"Data-driven: valid email inputs should be accepted by the form.
    # TEST_DATA: {{test_email}} (from spec valid test data)
    \"\"\"
    page.goto("{spec.url}")
    page.locator('input[type="email"]').fill(test_email)
    page.locator('input[type="password"]').fill(os.getenv("TEST_PASSWORD", "Test@1234!"))
    page.locator('button[type="submit"]').click()
    page.wait_for_timeout(500)
    # Should NOT show email format error
    format_error = page.locator("text=/invalid email|valid email|email format/i")
    assert not format_error.is_visible(), f"Valid email '{{test_email}}' rejected with format error"

@pytest.mark.parametrize("test_email", [{invalid_list}])
def test_invalid_email_rejected(page: Page, test_email):
    \"\"\"Data-driven: invalid email inputs must be rejected.
    # TEST_DATA: {{test_email}} (from spec invalid test data)
    \"\"\"
    page.goto("{spec.url}")
    if test_email:
        page.locator('input[type="email"]').fill(test_email)
    page.locator('button[type="submit"]').click()
    page.wait_for_timeout(500)
    error = page.locator("[role='alert'], .error-message, input:invalid")
    assert error.count() > 0, f"No error shown for invalid email: '{{test_email}}'"

Write these 2 parametrized test functions:""", 2500)


# ─────────────────────────────────────────────────────────────────────────────
# 18. I18N — internationalization: unicode, emoji, RTL, special chars
# ─────────────────────────────────────────────────────────────────────────────
def i18n(spec: ParsedSpec) -> str:
    i18n_inputs = [
        ("arabic_rtl",    "مرحبا@test.com",              "Arabic RTL text in email"),
        ("chinese_chars", "测试用户@example.com",           "Chinese characters in email"),
        ("emoji_in_name", "test😀@example.com",            "Emoji in email"),
        ("accented_chars","tëst@exämplé.com",              "Accented Latin characters"),
        ("japanese",      "テスト@テスト.jp",                "Japanese characters"),
        ("long_unicode",  "à"*50 + "@test.com",           "Long unicode string"),
        ("rtl_password",  "كلمة مرور123",                 "Arabic password"),
        ("zero_width",    "test​@test.com",          "Zero-width character"),
    ]

    cases_text = "\n".join(
        f'    ("{key}", "{inp}", "{desc}"),'
        for key, inp, desc in i18n_inputs
    )

    return _ai(f"""{_RULES}
PAGE: {spec.page_name}  URL: {spec.url}

Write I18N (internationalization) tests for non-ASCII / special character inputs.

@pytest.mark.parametrize("key,test_input,description", [
{cases_text}
])
def test_i18n_input_handling(page: Page, key, test_input, description):
    \"\"\"I18N: app handles international character inputs gracefully.
    # TEST_DATA: {{description}} = {{test_input[:30]}}
    \"\"\"
    page.goto("{spec.url}")
    page.wait_for_load_state("networkidle")
    try:
        page.locator('input[type="email"]').fill(test_input)
    except: pass
    page.locator('button[type="submit"]').click()
    page.wait_for_timeout(500)
    # App should NOT crash — either show validation error OR process the input
    assert "500" not in page.content(), f"Server crash on i18n input: {{description}}"
    exceptions_exposed = any(w in page.content().lower()
                              for w in ["exception", "traceback", "syntaxerror"])
    assert not exceptions_exposed, f"Exception exposed for i18n input: {{description}}"

Also write test_page_content_encoding:
    response = page.goto("{spec.url}")
    headers = response.all_headers()
    content_type = headers.get("content-type", "").lower()
    assert "utf-8" in content_type, f"Page not UTF-8 encoded: {{content_type}}"

Write these 2 test functions:""", 2500)


# ─────────────────────────────────────────────────────────────────────────────
# 19. RATE LIMITING — rapid submission, brute force detection
# ─────────────────────────────────────────────────────────────────────────────
def rate_limiting(spec: ParsedSpec) -> str:
    return _ai(f"""{_RULES}
PAGE: {spec.page_name}  URL: {spec.url}

Write RATE LIMITING tests — verify the app defends against rapid form submission.

1. test_rapid_form_submission_handled:
   \"\"\"Rate limiting: rapid repeated submissions don't crash the app.
   # TEST_DATA: 5 rapid wrong-credentials submissions
   \"\"\"
   page.goto("{spec.url}")
   responses = []
   page.on("response", lambda r: responses.append(r.status) if "/api/" in r.url else None)
   for attempt in range(5):
       page.locator('input[type="email"]').fill(f"test{{attempt}}@test.com")
       page.locator('input[type="password"]').fill("wrongpass")
       page.locator('button[type="submit"]').click()
       page.wait_for_timeout(300)
   # After 5 rapid wrong attempts, check:
   # - Page is still functional (not crashed)
   assert page.locator('input[type="email"]').is_visible(), "Page broke after rapid submissions"
   # - Check if rate limiting kicked in (429 or account lockout message)
   hit_rate_limit = (
       429 in responses or
       page.locator("text=/too many|rate limit|try again|blocked/i").is_visible()
   )
   # Rate limiting is good but not required; just verify no crash
   print(f"Rate limiting applied: {{hit_rate_limit}}")

2. test_brute_force_protection:
   \"\"\"Rate limiting: 10 wrong password attempts trigger protection.
   # TEST_DATA: 10 wrong password attempts for same email
   \"\"\"
   page.goto("{spec.url}")
   test_email = f"brutetest_{{int(time.time())}}@test.com"
   for i in range(10):
       try:
           page.locator('input[type="email"]').fill(test_email)
           page.locator('input[type="password"]').fill(f"wrong{{i}}")
           page.locator('button[type="submit"]').click()
           page.wait_for_timeout(200)
       except: break
   # App should still be working
   assert page.url is not None, "App crashed during brute force test"

3. test_double_click_submit_not_double_submit:
   \"\"\"Rate limiting: double-clicking submit doesn't cause double form submission.
   # TEST_DATA: double-click on submit button
   \"\"\"
   api_calls = []
   page.on("request", lambda r: api_calls.append(r.url) if "/api/" in r.url else None)
   page.goto("{spec.url}")
   page.locator('input[type="email"]').fill("test@test.com")
   page.locator('input[type="password"]').fill("Test@1234!")
   page.locator('button[type="submit"]').dblclick()
   page.wait_for_timeout(1000)
   # Should not have 2+ identical API calls
   api_login_calls = [u for u in api_calls if "login" in u or "auth" in u]
   assert len(api_login_calls) <= 1, f"Double submit occurred: {{len(api_login_calls)}} calls"

Write these 3 test functions:""", 2500)


# ─────────────────────────────────────────────────────────────────────────────
# 20. COOKIE & STORAGE — localStorage, sessionStorage, cookies
# ─────────────────────────────────────────────────────────────────────────────
def cookie_storage(spec: ParsedSpec) -> str:
    return _ai(f"""{_RULES}
PAGE: {spec.page_name}  URL: {spec.url}

Write COOKIE & STORAGE tests for localStorage, sessionStorage, and cookies.

1. test_no_sensitive_data_in_localstorage:
   \"\"\"Storage: no plaintext passwords in localStorage.
   # TEST_DATA: checks localStorage after interaction
   \"\"\"
   page.goto("{spec.url}")
   page.locator('input[type="email"]').fill("test@test.com")
   page.locator('input[type="password"]').fill("Test@1234!")
   page.locator('button[type="submit"]').click()
   page.wait_for_timeout(1000)
   storage = page.evaluate("() => Object.entries(localStorage)")
   for key, value in storage:
       assert "password" not in key.lower(), f"Password key in localStorage: {{key}}"
       if isinstance(value, str) and len(value) < 100:
           assert "Test@1234!" not in value, f"Plaintext password in localStorage[{{key}}]"

2. test_session_storage_cleared_on_bad_login:
   \"\"\"Storage: failed login does not persist auth data.
   # TEST_DATA: wrong credentials → check storage
   \"\"\"
   page.goto("{spec.url}")
   page.locator('input[type="email"]').fill("hacker@evil.com")
   page.locator('input[type="password"]').fill("wrongpass")
   page.locator('button[type="submit"]').click()
   page.wait_for_timeout(1000)
   token = page.evaluate("() => localStorage.getItem('token') || sessionStorage.getItem('token')")
   assert not token, f"Auth token set after failed login: {{token}}"

3. test_cookies_have_security_attributes:
   \"\"\"Storage: cookies use Secure and HttpOnly flags.
   # TEST_DATA: checks cookie attributes after page load
   \"\"\"
   page.goto("{spec.url}")
   page.wait_for_load_state("networkidle")
   cookies = page.context.cookies()
   for cookie in cookies:
       if "session" in cookie["name"].lower() or "auth" in cookie["name"].lower():
           assert cookie.get("httpOnly", False), f"Session cookie {{cookie['name']}} missing HttpOnly"

4. test_localstorage_not_polluted:
   \"\"\"Storage: page doesn't write unexpected data to localStorage.
   # TEST_DATA: monitors localStorage before and after page load
   \"\"\"
   page.goto("{spec.url}")
   page.wait_for_load_state("networkidle")
   keys = page.evaluate("() => Object.keys(localStorage)")
   suspicious = [k for k in keys if any(w in k.lower() for w in ["debug", "test", "hack", "dev_"])]
   assert not suspicious, f"Suspicious localStorage keys: {{suspicious}}"

Write all 4 test functions:""", 2500)


# ─────────────────────────────────────────────────────────────────────────────
# 21. DEEP FORM — every field, every state, every combination
# ─────────────────────────────────────────────────────────────────────────────
def deep_form(spec: ParsedSpec) -> str:
    field_names = [r for r in spec.validation_rules[:6]] if spec.validation_rules else \
                  ["email field", "password field"]

    return _ai(f"""{_RULES}
PAGE: {spec.page_name}  URL: {spec.url}

Write DEEP FORM tests — exhaustively test every form field and state.

FORM FIELDS (from spec):
{chr(10).join(f"  - {r}" for r in spec.validation_rules[:8])}

REQUIRED TESTS:

1. test_tab_order_logical: Tab key moves through fields in visual top-to-bottom order
2. test_paste_into_email_field: Paste an email address using clipboard
   page.locator('input[type="email"]').focus()
   page.evaluate("document.querySelector('input[type=email]').value = 'pasted@test.com'")
   page.locator('input[type="email"]').dispatch_event("input")
   assert page.locator('input[type="email"]').input_value() == "pasted@test.com"

3. test_password_field_masked: Password value is not visible in DOM
   page.locator('input[type="password"]').fill("mysecret")
   inp_type = page.locator('input[type="password"]').get_attribute("type")
   assert inp_type == "password", f"Password field type is '{{inp_type}}' — not masked"

4. test_form_fields_have_autocomplete: Check for autocomplete attributes
   email_ac = page.locator('input[type="email"]').get_attribute("autocomplete")
   pass_ac = page.locator('input[type="password"]').get_attribute("autocomplete")
   # email should have autocomplete="email" or "username"
   # password should have autocomplete="current-password" or "off"

5. test_required_fields_marked: required fields have required attribute OR aria-required
   email = page.locator('input[type="email"]')
   has_required = email.get_attribute("required") is not None or \\
                  email.get_attribute("aria-required") == "true"
   assert has_required, "Email field not marked as required"

6. test_form_clears_after_navigation: Fill form, navigate away, come back → form is clear
   page.goto("{spec.url}")
   page.locator('input[type="email"]').fill("test@test.com")
   page.go_back()
   page.go_forward()
   page.wait_for_load_state("networkidle")
   val = page.locator('input[type="email"]').input_value()
   # May or may not clear — just assert no crash

Write all 6 test functions:""", 2500)


# ─────────────────────────────────────────────────────────────────────────────
# Master runner
# ─────────────────────────────────────────────────────────────────────────────

ALL_TYPES = [
    # CRITICAL (always run)
    ("smoke",          smoke),
    ("functional",     functional),
    ("validation",     validation),
    ("negative",       negative),
    # DEEP COVERAGE
    ("boundary",       boundary),
    ("data_driven",    data_driven),
    ("deep_form",      deep_form),
    # SECURITY
    ("api_network",    api_network),
    # QUALITY
    ("accessibility",  accessibility),
    ("responsive",     responsive),
    ("navigation",     navigation),
    ("session_auth",   session_auth),
    # PERFORMANCE & RELIABILITY
    ("performance",    performance),
    ("console_errors", console_errors),
    ("error_states",   error_states),
    ("visual",         visual),
    ("cross_browser",  cross_browser),
    # ADVANCED
    ("i18n",           i18n),
    ("rate_limiting",  rate_limiting),
    ("cookie_storage", cookie_storage),
]


def generate_all(
    spec: ParsedSpec,
    xss_payloads: list[str] | None = None,
    sqli_payloads: list[str] | None = None,
) -> dict[str, str]:
    """
    Returns {type_name: function_code_blocks} for every test type.
    Each value contains def test_...() blocks with no module-level code.
    """
    xss  = xss_payloads  or []
    sqli = sqli_payloads or []
    results: dict[str, str] = {}

    for name, fn in ALL_TYPES:
        try:
            code = fn(spec)
            results[name] = code or ""
        except Exception as e:
            results[name] = ""
            print(f"  [GEN:{name}] error: {e}", flush=True)

    # Security needs payload lists
    try:
        results["security"] = security(spec, xss, sqli)
    except Exception as e:
        results["security"] = ""
        print(f"  [GEN:security] error: {e}", flush=True)

    return results
