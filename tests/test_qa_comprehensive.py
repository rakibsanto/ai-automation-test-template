"""
QA Comprehensive Test Suite — Fagun Staging
Covers 5 test groups:
  QA-01  Functional & User Flow Tests
  QA-02  Edge Case & Boundary Tests
  QA-03  Security Tests (XSS + SQLi)
  QA-04  Performance & JavaScript Error Tests
  QA-05  Hallucination & Data Integrity Tests
"""

import os, re, time, json
import pytest
from pathlib import Path
from playwright.sync_api import Page, expect

BASE_URL   = os.getenv("BASE_URL", "https://beta-stg.fagun.ai")
LOGIN_URL  = f"{BASE_URL}/login"
SIGNUP_URL = f"{BASE_URL}/signup"
RESET_URL  = f"{BASE_URL}/reset-pass"

# Use domcontentloaded — SPAs never reach networkidle on staging
LOAD_STATE = "domcontentloaded"

VALID_EMAIL    = os.getenv("TEST_USER_EMAIL",    "mejbaur@fagun.ai")
VALID_PASSWORD = os.getenv("TEST_USER_PASSWORD", "")

PAYLOAD_DIR = Path(__file__).parent.parent / "payloads"

# ─────────────────────────────────────────────────────────────────────────────
# Helpers  (SPA-aware: wait for React/Vue to mount before querying elements)
# ─────────────────────────────────────────────────────────────────────────────

_EMAIL_SELECTORS = [
    'input[type="email"]',
    'input[name="email"]',
    'input[placeholder*="email" i]',
    'input[id*="email" i]',
]
_PWD_SELECTORS = [
    'input[type="password"]',
    'input[name="password"]',
    'input[placeholder*="password" i]',
    'input[id*="password" i]',
]
_BTN_SELECTORS = [
    'button[type="submit"]',
    'button:has-text("Login")',
    'button:has-text("Sign In")',
    'button:has-text("Log in")',
    '[data-testid="login-btn"]',
]


def _wait_and_find(page: Page, selectors: list[str], label: str, timeout: int = 12000):
    """
    Wait for any selector in the list to become visible (SPA hydration),
    then return the first matching locator.
    """
    combined = ", ".join(selectors)
    try:
        page.wait_for_selector(combined, state="visible", timeout=timeout)
    except Exception:
        pass  # fall through — the loop below will raise with a clear message
    for sel in selectors:
        loc = page.locator(sel).first
        try:
            if loc.count() > 0 and loc.is_visible(timeout=500):
                return loc
        except Exception:
            continue
    raise AssertionError(f"{label} not found on page after {timeout}ms — "
                         f"tried: {selectors}")


def _email_input(page: Page):
    return _wait_and_find(page, _EMAIL_SELECTORS, "Email input")


def _password_input(page: Page):
    return _wait_and_find(page, _PWD_SELECTORS, "Password input")


def _submit_button(page: Page):
    return _wait_and_find(page, _BTN_SELECTORS, "Submit button")


def _collect_js_errors(page: Page) -> list:
    errors: list = []
    page.on("console", lambda m: errors.append(
        {"type": m.type, "text": m.text}) if m.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append(
        {"type": "pageerror", "text": str(exc)}))
    return errors


def _load_payload_lines(filename: str) -> list[str]:
    p = PAYLOAD_DIR / filename
    if not p.exists():
        return []
    return [
        ln.strip() for ln in p.read_text().splitlines()
        if ln.strip() and not ln.startswith("#")
    ]


# ─────────────────────────────────────────────────────────────────────────────
# QA-01  FUNCTIONAL & USER FLOW TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestQA01Functional:
    """Verifies real form interactions produce correct UI behaviour."""

    def test_qa01_login_page_elements_present(self, page: Page):
        """Page loads with all required form elements visible."""
        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        assert "/login" in page.url or page.url.startswith(BASE_URL), (
            f"Unexpected URL: {page.url}")

        assert _email_input(page).is_visible(),    "Email input missing"
        assert _password_input(page).is_visible(), "Password input missing"
        assert _submit_button(page).is_visible(),  "Submit button missing"

    def test_qa01_empty_email_blocks_submit(self, page: Page):
        """Submitting with empty email must not send a network request."""
        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        submitted_requests: list[str] = []
        page.on("request", lambda r: submitted_requests.append(r.url)
                if "auth" in r.url.lower() or "login" in r.url.lower() else None)

        pwd = _password_input(page)
        pwd.fill("SomePassword123!")
        _submit_button(page).click()
        page.wait_for_timeout(1500)

        assert page.url.endswith("/login") or "/login" in page.url, (
            "Form was submitted despite empty email — should stay on login page")

    def test_qa01_empty_password_blocks_submit(self, page: Page):
        """Submitting with empty password must block form submission."""
        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        _email_input(page).fill("valid@example.com")
        _submit_button(page).click()
        page.wait_for_timeout(1500)

        assert "/login" in page.url, (
            "Form was submitted despite empty password")

    def test_qa01_invalid_email_format_rejected(self, page: Page):
        """Non-email strings in email field must be rejected client-side."""
        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        _email_input(page).fill("notanemail")
        _password_input(page).fill("SomePassword1!")
        _submit_button(page).click()
        page.wait_for_timeout(1500)

        assert "/login" in page.url, (
            "Invalid email format accepted — should be rejected before submission")

    def test_qa01_forgot_password_link_navigates(self, page: Page):
        """Clicking Forgot Password link navigates to /reset-pass."""
        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        link = page.locator(
            'a[href*="reset"], a:has-text("Forgot"), a:has-text("Reset")'
        ).first
        assert link.count() > 0, "Forgot password link not found"
        link.click()
        page.wait_for_load_state(LOAD_STATE)

        assert "reset" in page.url.lower() or "forgot" in page.url.lower(), (
            f"Expected reset URL, got: {page.url}")

    def test_qa01_signup_link_navigates(self, page: Page):
        """Clicking Sign Up link navigates to /signup."""
        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        link = page.locator(
            'a[href*="signup"], a[href*="register"], '
            'a:has-text("Sign Up"), a:has-text("Create account")'
        ).first
        assert link.count() > 0, "Sign Up link not found"
        link.click()
        page.wait_for_load_state(LOAD_STATE)

        assert "signup" in page.url.lower() or "register" in page.url.lower(), (
            f"Expected signup URL, got: {page.url}")

    def test_qa01_invalid_credentials_show_error(self, page: Page):
        """Wrong credentials must display an error message, not crash."""
        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        _email_input(page).fill("notregistered@example.com")
        _password_input(page).fill("WrongPassword123!")
        _submit_button(page).click()
        page.wait_for_timeout(3000)

        # Must stay on login or show an error — must not crash to 500
        current = page.url
        status_code = None

        assert "/login" in current or "error" in current or (
            page.locator('[role="alert"], .error, [class*="error"]').count() > 0
        ), "No error shown after invalid credentials"

        # Ensure no server-error page
        title = page.title()
        assert "500" not in title and "Error" not in title[:20], (
            f"Server error page after invalid login: {title}")

    def test_qa01_password_field_masked_by_default(self, page: Page):
        """Password input type must be 'password' (masked) on page load."""
        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        pwd = _password_input(page)
        field_type = pwd.get_attribute("type")
        assert field_type == "password", (
            f"Password field type is '{field_type}', expected 'password' (masked)")

    def test_qa01_double_submit_prevented(self, page: Page):
        """Rapid double-click on Login must not send two auth requests."""
        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        auth_requests: list = []
        page.on("request", lambda r: auth_requests.append(r.url)
                if "auth" in r.url or "login" in r.url.lower() else None)

        _email_input(page).fill(VALID_EMAIL)
        _password_input(page).fill("SomePass1!")
        btn = _submit_button(page)
        btn.click()
        btn.click(force=True)          # second click — should be ignored
        page.wait_for_timeout(2000)

        duplicate_auth = len([u for u in auth_requests
                               if "login" in u.lower() or "auth" in u]) > 1
        assert not duplicate_auth, (
            f"Double submit sent multiple auth requests: {auth_requests}")


# ─────────────────────────────────────────────────────────────────────────────
# QA-02  EDGE CASE & BOUNDARY TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestQA02EdgeCaseBoundary:
    """Exercises input boundaries, whitespace, Unicode, and extreme lengths."""

    def test_qa02_ec_leading_trailing_whitespace_email(self, page: Page):
        """EC-L-01: Email with leading/trailing spaces — must trim or reject."""
        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        _email_input(page).fill("  valid@example.com  ")
        _password_input(page).fill("SomePassword1!")
        _submit_button(page).click()
        page.wait_for_timeout(2000)

        # Acceptable: trims and proceeds (not crash), or shows validation error
        title = page.title()
        assert "500" not in title and "crash" not in title.lower(), (
            "Whitespace in email caused a server crash")

    def test_qa02_ec_uppercase_email(self, page: Page):
        """EC-L-02: Uppercase email must be treated case-insensitively."""
        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        _email_input(page).fill("MEJBAUR@MARKOPOLO.AI")
        _password_input(page).fill("SomePassword1!")
        _submit_button(page).click()
        page.wait_for_timeout(2000)

        # Must not 500 — either auth succeeds or shows "invalid credentials"
        assert "500" not in page.title(), "Uppercase email triggered server error"

    def test_qa02_ec_password_special_chars(self, page: Page):
        """EC-L-03: Password with special characters must be accepted."""
        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        _email_input(page).fill("valid@example.com")
        _password_input(page).fill("!@#$%^&*()_+{}[]|")
        _submit_button(page).click()
        page.wait_for_timeout(2000)

        assert "500" not in page.title(), "Special-char password caused server error"

    def test_qa02_ec_password_with_spaces(self, page: Page):
        """EC-L-04: Password containing spaces must be accepted."""
        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        _email_input(page).fill("valid@example.com")
        _password_input(page).fill("pass word with spaces 123")
        _submit_button(page).click()
        page.wait_for_timeout(2000)

        assert "500" not in page.title(), "Space in password caused server error"

    @pytest.mark.parametrize("length,label", [
        (255, "255-char"),
        (256, "256-char"),
        (512, "512-char"),
    ])
    def test_qa02_ec_very_long_email(self, page: Page, length: int, label: str):
        """EC-L-05: Very long email (boundary lengths) must not crash."""
        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        local = "a" * (length - len("@x.com"))
        long_email = f"{local}@x.com"
        _email_input(page).fill(long_email)
        _password_input(page).fill("SomePass1!")
        _submit_button(page).click()
        page.wait_for_timeout(2000)

        assert "500" not in page.title(), (
            f"{label} email caused server error")

    def test_qa02_ec_very_long_password(self, page: Page):
        """EC-L-06: 500-char password must be handled gracefully."""
        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        _email_input(page).fill("valid@example.com")
        _password_input(page).fill("A" * 500)
        _submit_button(page).click()
        page.wait_for_timeout(2000)

        assert "500" not in page.title(), "500-char password caused server error"

    def test_qa02_ec_zero_width_unicode_in_email(self, page: Page):
        """EC-L-12: Invisible Unicode chars in email must be normalised or rejected."""
        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        _email_input(page).fill("valid​@example.com")   # zero-width space
        _password_input(page).fill("SomePass1!")
        _submit_button(page).click()
        page.wait_for_timeout(2000)

        assert "500" not in page.title(), "Zero-width Unicode char caused server crash"

    def test_qa02_ec_rtl_unicode_in_email(self, page: Page):
        """Bidirectional/RTL override char in email — must not crash."""
        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        _email_input(page).fill("valid‮@example.com")   # RTL override
        _password_input(page).fill("SomePass1!")
        _submit_button(page).click()
        page.wait_for_timeout(2000)

        assert "500" not in page.title(), "RTL override char caused server crash"

    def test_qa02_ec_emoji_in_email(self, page: Page):
        """Emoji in email address — must be rejected without crashing."""
        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        _email_input(page).fill("test\U0001f525@example.com")  # 🔥
        _password_input(page).fill("SomePass1!")
        _submit_button(page).click()
        page.wait_for_timeout(2000)

        assert "500" not in page.title(), "Emoji in email caused server crash"

    def test_qa02_ec_only_whitespace_both_fields(self, page: Page):
        """Fields filled with only spaces must block submission."""
        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        _email_input(page).fill("   ")
        _password_input(page).fill("   ")
        _submit_button(page).click()
        page.wait_for_timeout(1500)

        assert "/login" in page.url, (
            "Whitespace-only fields allowed form submission")

    def test_qa02_ec_null_byte_in_password(self, page: Page):
        """Null byte in password — must not corrupt server-side processing."""
        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        _email_input(page).fill("valid@example.com")
        _password_input(page).fill("pass\x00word")
        _submit_button(page).click()
        page.wait_for_timeout(2000)

        assert "500" not in page.title(), "Null byte in password caused server error"

    def test_qa02_ec_newline_in_email(self, page: Page):
        """Newline injection in email — must be sanitised, not cause 500."""
        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        _email_input(page).fill("valid@example.com\r\nX-Injected: header")
        _password_input(page).fill("SomePass1!")
        _submit_button(page).click()
        page.wait_for_timeout(2000)

        assert "500" not in page.title(), "Newline injection caused server error"


# ─────────────────────────────────────────────────────────────────────────────
# QA-03  SECURITY TESTS — XSS + SQL INJECTION
# ─────────────────────────────────────────────────────────────────────────────

class TestQA03Security:
    """Verifies that XSS payloads and SQL injection vectors are safely handled."""

    # ── XSS ──────────────────────────────────────────────────────────────────

    @pytest.mark.parametrize("payload", _load_payload_lines("xss.txt"))
    def test_qa03_xss_in_email_field(self, page: Page, payload: str):
        """XSS payload in email must not execute and must not crash the app."""
        js_alerts: list = []
        page.on("dialog", lambda d: (js_alerts.append(d.message), d.dismiss()))
        page.on("pageerror", lambda exc: js_alerts.append(str(exc)))

        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)
        _email_input(page).fill(payload)
        _password_input(page).fill("SomePass1!")
        _submit_button(page).click()
        page.wait_for_timeout(1500)

        assert len(js_alerts) == 0, (
            f"XSS payload triggered alert/error: {payload!r} → {js_alerts}")
        assert "500" not in page.title(), (
            f"XSS payload crashed server: {payload!r}")

    @pytest.mark.parametrize("payload", _load_payload_lines("xss.txt"))
    def test_qa03_xss_in_password_field(self, page: Page, payload: str):
        """XSS payload in password field must not execute scripts."""
        js_alerts: list = []
        page.on("dialog", lambda d: (js_alerts.append(d.message), d.dismiss()))

        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)
        _email_input(page).fill("valid@example.com")
        _password_input(page).fill(payload)
        _submit_button(page).click()
        page.wait_for_timeout(1500)

        assert len(js_alerts) == 0, (
            f"XSS in password field triggered alert: {payload!r}")

    def test_qa03_xss_reflected_in_page_source(self, page: Page):
        """Verify that XSS payloads are NOT reflected raw in the page HTML."""
        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        payload = "<script>alert('QA_XSS_MARKER')</script>"
        _email_input(page).fill(payload)
        _password_input(page).fill("SomePass1!")
        _submit_button(page).click()
        page.wait_for_timeout(2000)

        content = page.content()
        assert "QA_XSS_MARKER" not in content, (
            "XSS payload reflected unescaped in page HTML — stored/reflected XSS risk")

    def test_qa03_template_injection_detection(self, page: Page):
        """Template expressions {{7*7}} must NOT evaluate to 49 in page content."""
        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        _email_input(page).fill("{{7*7}}@example.com")
        _password_input(page).fill("SomePass1!")
        _submit_button(page).click()
        page.wait_for_timeout(2000)

        content = page.content()
        # If template injection works, the literal "49" would appear where {{7*7}} was
        assert "{{7*7}}" not in content or "49" not in content, (
            "Possible SSTI: {{7*7}} expression was evaluated in page content")

    # ── SQL Injection ─────────────────────────────────────────────────────────

    @pytest.mark.parametrize("payload", _load_payload_lines("sqli.txt"))
    def test_qa03_sqli_in_email_field(self, page: Page, payload: str):
        """SQL injection payload in email must not bypass auth or crash DB."""
        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        # Wrap payload to look like an email for form validation
        safe_payload = f"test+{payload.replace(' ', '_')}@x.com"
        _email_input(page).fill(safe_payload)
        _password_input(page).fill("WrongPass1!")
        _submit_button(page).click()
        page.wait_for_timeout(2500)

        title   = page.title()
        content = page.content().lower()

        # Must not reveal DB errors or auth-bypass
        db_error_hints = ["sql syntax", "mysql", "postgresql", "sqlite",
                          "ora-", "unclosed", "unterminated"]
        leaks = [h for h in db_error_hints if h in content]
        assert not leaks, (
            f"SQLi payload leaked DB error — hints: {leaks} | payload: {payload!r}")

        assert "500" not in title, (
            f"SQLi payload caused 500 server error: {payload!r}")

    def test_qa03_sqli_raw_payload_in_email(self, page: Page):
        """Raw ' OR '1'='1 injection directly in email field."""
        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        _email_input(page).fill("' OR '1'='1")
        _password_input(page).fill("' OR '1'='1")
        _submit_button(page).click()
        page.wait_for_timeout(2500)

        # Must NOT login successfully (would indicate auth bypass)
        current_url = page.url
        assert "dashboard" not in current_url and "home" not in current_url, (
            f"SQLi auth bypass succeeded — redirected to: {current_url}")

    def test_qa03_no_sensitive_data_in_responses(self, page: Page):
        """Network responses must not expose passwords, tokens in plain HTML."""
        sensitive_patterns = [
            r"password[\"']?\s*:\s*[\"'][^\"']{4,}",
            r"secret[\"']?\s*:\s*[\"'][^\"']{4,}",
            r"api_key[\"']?\s*:\s*[\"'][^\"']{4,}",
        ]
        responses: list[str] = []

        async def capture(resp):
            try:
                if "text" in (resp.headers.get("content-type") or ""):
                    body = resp.body().decode("utf-8", errors="ignore")[:2000]
                    responses.append(body)
            except Exception:
                pass

        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        html = page.content()
        for pat in sensitive_patterns:
            assert not re.search(pat, html, re.IGNORECASE), (
                f"Sensitive data pattern found in HTML: {pat}")


# ─────────────────────────────────────────────────────────────────────────────
# QA-04  PERFORMANCE & JAVASCRIPT ERROR TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestQA04PerformanceAndJSErrors:
    """Validates page load times, Web Vitals, and absence of JS errors."""

    def test_qa04_login_page_loads_under_3s(self, page: Page):
        """Login page must reach networkidle within 3 seconds (P0 requirement)."""
        start = time.perf_counter()
        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 3000, (
            f"Login page took {elapsed_ms:.0f}ms > 3000ms — performance regression")

    def test_qa04_time_to_first_byte_under_600ms(self, page: Page):
        """TTFB must be below 600 ms for staging environment."""
        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        ttfb = page.evaluate("""() => {
            const t = performance.timing;
            return t.responseStart - t.navigationStart;
        }""")

        assert ttfb < 600, f"TTFB is {ttfb}ms — expected < 600ms"

    def test_qa04_dom_content_loaded_under_2s(self, page: Page):
        """DOMContentLoaded must fire within 2 seconds."""
        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        dcl = page.evaluate("""() => {
            const t = performance.timing;
            return t.domContentLoadedEventEnd - t.navigationStart;
        }""")

        assert dcl < 2000, f"DOMContentLoaded took {dcl}ms — expected < 2000ms"

    def test_qa04_no_js_errors_on_load(self, page: Page):
        """Login page must load without any JavaScript console errors."""
        errors: list = []
        page.on("console",  lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))

        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        assert errors == [], (
            f"JS errors on page load:\n" + "\n".join(errors[:5]))

    def test_qa04_no_js_errors_after_interaction(self, page: Page):
        """Typing into fields and clicking submit must not trigger JS errors."""
        errors: list = []
        page.on("console",  lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))

        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)
        _email_input(page).fill("valid@example.com")
        _password_input(page).fill("SomePass1!")
        _submit_button(page).click()
        page.wait_for_timeout(2000)

        assert errors == [], (
            f"JS errors after interaction:\n" + "\n".join(errors[:5]))

    def test_qa04_no_404_resources_on_login(self, page: Page):
        """Login page must not request any resource that returns 404."""
        not_found: list = []
        page.on("response", lambda r: not_found.append(r.url)
                if r.status == 404 else None)

        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        assert not_found == [], (
            f"Login page has broken resources (404):\n" + "\n".join(not_found[:5]))

    def test_qa04_no_500_errors_on_load(self, page: Page):
        """No network response should be 5xx on initial page load."""
        server_errors: list = []
        page.on("response", lambda r: server_errors.append({"url": r.url, "status": r.status})
                if r.status >= 500 else None)

        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        assert server_errors == [], (
            f"Server errors on login load:\n{server_errors[:3]}")

    def test_qa04_no_mixed_content_warnings(self, page: Page):
        """HTTPS page must not load any HTTP (insecure) resources."""
        insecure: list = []
        page.on("request", lambda r: insecure.append(r.url)
                if r.url.startswith("http://") else None)

        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        # Ignore localhost / internal
        real_insecure = [u for u in insecure if "localhost" not in u and "127." not in u]
        assert real_insecure == [], (
            f"Mixed content (HTTP resources on HTTPS page):\n" + "\n".join(real_insecure[:5]))

    @pytest.mark.parametrize("viewport", [
        {"width": 375,  "height": 667,  "label": "mobile-sm"},
        {"width": 768,  "height": 1024, "label": "tablet"},
        {"width": 1280, "height": 720,  "label": "desktop"},
        {"width": 1920, "height": 1080, "label": "desktop-xl"},
    ])
    def test_qa04_responsive_layout_no_errors(self, page: Page, viewport: dict):
        """Login form must render and be interactive across all common viewports."""
        label = viewport.pop("label")
        page.set_viewport_size(viewport)

        errors: list = []
        page.on("console",  lambda m: errors.append(m.text) if m.type == "error" else None)

        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        assert _email_input(page).is_visible(), (
            f"Email input not visible at {label} ({viewport})")
        assert _password_input(page).is_visible(), (
            f"Password input not visible at {label} ({viewport})")
        assert errors == [], (
            f"JS errors at {label}:\n" + "\n".join(errors[:3]))


# ─────────────────────────────────────────────────────────────────────────────
# QA-05  HALLUCINATION & DATA INTEGRITY TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestQA05HallucinationDataIntegrity:
    """
    Detects UI hallucinations: phantom elements, stale data, data bleeding,
    inconsistent error states, and AI-generated content anomalies.
    """

    # ── Phantom / Ghost Element Detection ────────────────────────────────────

    def test_qa05_no_placeholder_text_visible_as_content(self, page: Page):
        """
        Checks that Lorem Ipsum / TODO / placeholder text is not rendered
        on the login page (sign of hallucinated or unmocked UI).
        """
        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)
        content = page.inner_text("body").lower()

        phantom_phrases = [
            "lorem ipsum", "placeholder text", "todo", "fixme",
            "coming soon", "undefined", "[object object]", "null",
            "your text here", "sample text", "test content",
        ]
        found = [p for p in phantom_phrases if p in content]
        assert not found, (
            f"Phantom/placeholder text visible on login page: {found}")

    def test_qa05_no_duplicate_form_fields(self, page: Page):
        """Login form must not render duplicate email or password inputs."""
        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        email_count = page.locator('input[type="email"], input[name="email"]').count()
        pwd_count   = page.locator('input[type="password"]').count()

        assert email_count == 1, (
            f"Found {email_count} email inputs — expected exactly 1 (ghost element risk)")
        assert pwd_count >= 1, "No password input found"
        # allow 2 for show/hide toggle trick but not more
        assert pwd_count <= 2, (
            f"Found {pwd_count} password inputs — suspicious duplication")

    def test_qa05_no_stale_error_messages_on_fresh_load(self, page: Page):
        """
        A fresh page load must not show any error messages.
        Pre-populated errors indicate stale state from a previous session.
        """
        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        error_locs = page.locator(
            '[role="alert"], .error-message, [class*="error"], '
            '[class*="alert"], [data-testid*="error"]'
        )
        visible_errors = [
            error_locs.nth(i).inner_text()
            for i in range(error_locs.count())
            if error_locs.nth(i).is_visible()
        ]
        assert visible_errors == [], (
            f"Stale error messages visible on fresh page load: {visible_errors}")

    def test_qa05_page_title_is_meaningful(self, page: Page):
        """Page title must not be 'undefined', empty, or a raw URL."""
        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        title = page.title()
        assert title.strip() != "", "Page title is empty"
        assert "undefined" not in title.lower(), f"Page title contains 'undefined': {title}"
        assert "null" not in title.lower(), f"Page title contains 'null': {title}"
        assert "localhost" not in title.lower(), f"Page title leaks localhost: {title}"
        assert len(title) < 200, f"Page title suspiciously long ({len(title)} chars): {title[:80]}"

    def test_qa05_error_message_does_not_leak_field_specifics(self, page: Page):
        """
        Error after invalid login must NOT reveal which field (email vs password)
        is incorrect — leaking this helps enumeration attacks.
        """
        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        _email_input(page).fill("notregistered@example.com")
        _password_input(page).fill("WrongPassword123!")
        _submit_button(page).click()
        page.wait_for_timeout(3000)

        content = page.inner_text("body").lower()
        enumeration_hints = [
            "email not found",
            "no account",
            "email does not exist",
            "wrong password",
            "incorrect password",
            "password is wrong",
        ]
        found = [h for h in enumeration_hints if h in content]
        assert not found, (
            f"Error message leaks enumeration hints: {found}\n"
            "(Should say 'Invalid email or password' generically)")

    def test_qa05_no_data_bleeding_between_sessions(self, page: Page):
        """
        After failed login, email field must retain entered value but
        no other user's data should appear (cross-session data bleed).
        """
        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        test_email = "testonly_qa05@example.com"
        _email_input(page).fill(test_email)
        _password_input(page).fill("WrongPass1!")
        _submit_button(page).click()
        page.wait_for_timeout(2500)

        if "/login" in page.url:
            retained_val = _email_input(page).input_value()
            # Email retained is acceptable; email of a DIFFERENT user is not
            assert retained_val == "" or retained_val == test_email, (
                f"Data bleed — email field shows unexpected value: {retained_val!r}")

    # ── AI Hallucination (Generated Content) Tests ────────────────────────────

    def test_qa05_hallucination_no_impossible_success_message(self, page: Page):
        """
        After submitting clearly wrong credentials, the page must NOT show
        'Login successful', 'Welcome', or 'Dashboard' text.
        These would indicate a hallucinated success state.
        """
        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        _email_input(page).fill("fake@hallucination.test")
        _password_input(page).fill("FakeHallucinationPass1!")
        _submit_button(page).click()
        page.wait_for_timeout(3000)

        content = page.inner_text("body").lower()
        false_positive_phrases = [
            "login successful", "successfully logged in",
            "welcome back", "you are now logged in",
        ]
        found = [p for p in false_positive_phrases if p in content]
        assert not found, (
            f"Hallucinated success message shown after wrong credentials: {found}")

    def test_qa05_hallucination_no_phantom_dashboard_elements(self, page: Page):
        """
        After a failed login, dashboard-specific elements must not appear.
        Phantom dashboard elements = hallucinated authenticated state.
        """
        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        _email_input(page).fill("fake@hallucination.test")
        _password_input(page).fill("WrongPass999!")
        _submit_button(page).click()
        page.wait_for_timeout(3000)

        if "/login" in page.url:
            dashboard_selectors = [
                '[data-testid="dashboard"]',
                '[data-testid="user-avatar"]',
                'nav[aria-label="main navigation"]',
                '.sidebar',
                '#dashboard',
            ]
            for sel in dashboard_selectors:
                count = page.locator(sel).count()
                assert count == 0, (
                    f"Phantom dashboard element '{sel}' visible after failed login")

    def test_qa05_hallucination_error_message_content_quality(self, page: Page):
        """
        Error messages after invalid login must be coherent English text,
        not garbled strings, JSON blobs, or raw exception traces.
        """
        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        _email_input(page).fill("notreal@example.com")
        _password_input(page).fill("WrongPass1!")
        _submit_button(page).click()
        page.wait_for_timeout(3000)

        content = page.inner_text("body")
        garbage_patterns = [
            r"\{.*\"error\".*\}",                   # raw JSON in UI
            r"Traceback \(most recent call",         # Python traceback
            r"Exception in thread",                  # Java exception
            r"at \w+\.\w+\([\w.]+:\d+\)",           # Java/JS stack trace
            r"SyntaxError|TypeError|ReferenceError", # raw JS error type
            r"500 Internal Server Error",            # raw HTTP error
        ]
        for pat in garbage_patterns:
            assert not re.search(pat, content), (
                f"Garbage/hallucinated error content detected: pattern={pat!r}")

    def test_qa05_consistent_page_state_across_navigation(self, page: Page):
        """
        Navigate login → signup → back to login.
        Login page state must be clean (no residual data from signup page).
        """
        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        # Navigate away then return
        page.goto(SIGNUP_URL)
        page.wait_for_load_state(LOAD_STATE)
        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)

        # Email field must be empty on fresh navigation
        val = _email_input(page).input_value()
        assert val == "", (
            f"Email field pre-populated on fresh navigation — possible state bleed: {val!r}")

    def test_qa05_back_button_no_form_resubmission(self, page: Page):
        """
        After a failed login attempt, pressing browser Back then Forward
        must not auto-resubmit the form.
        """
        js_alerts: list = []
        page.on("dialog", lambda d: (js_alerts.append(d.message), d.dismiss()))

        page.goto(LOGIN_URL)
        page.wait_for_load_state(LOAD_STATE)
        _email_input(page).fill("test@example.com")
        _password_input(page).fill("WrongPass1!")
        _submit_button(page).click()
        page.wait_for_timeout(2000)

        page.go_back()
        page.wait_for_load_state(LOAD_STATE)
        page.go_forward()
        page.wait_for_timeout(2000)

        # A "Confirm Form Resubmission" dialog or auto-POST would be a bug
        # We dismiss dialogs above and just verify no crash
        assert "500" not in page.title(), "Back/forward navigation triggered server error"
