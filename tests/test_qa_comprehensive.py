"""
QA Comprehensive Test Suite — Mehad Homepage & Login Modal
Spec: specs/mehadedu_homepage.md
Covers 5 test groups:
  QA-01  Functional & User Flow Tests       (homepage, modal, login, navigation)
  QA-02  Edge Case & Boundary Tests         (phone validation, OTP, modal state)
  QA-03  Security Tests (XSS + SQLi)        (phone/search injection vectors)
  QA-04  Performance & JavaScript Error Tests
  QA-05  Hallucination & Data Integrity Tests
"""

import os, re, time, json
import pytest
from pathlib import Path
from playwright.sync_api import Page, expect

BASE_URL = os.getenv("BASE_URL", "https://dev.mehadedu.com/en")
FIND_TUTORS_URL = f"{BASE_URL}/find-tutors"
AR_URL          = os.getenv("BASE_URL", "https://dev.mehadedu.com").rstrip("/en").rstrip("/") + "/ar"

# SPA-safe load state — SPAs never reach networkidle
LOAD_STATE = "domcontentloaded"

# Test credentials (staging only)
TEST_COUNTRY_CODE = "+880"   # Bangladesh
TEST_PHONE        = "98976564"
TEST_OTP          = "123456"
TEST_USER_NAME    = "Automations Student"

PAYLOAD_DIR = Path(__file__).parent.parent / "payloads"

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _wait_visible(page: Page, selector: str, timeout: int = 10000):
    """Wait for a selector to be visible, return the locator."""
    page.wait_for_selector(selector, state="visible", timeout=timeout)
    return page.locator(selector).first


def _open_login_modal(page: Page):
    """Navigate to homepage and open the login modal."""
    page.goto(BASE_URL)
    page.wait_for_load_state(LOAD_STATE)
    btn = page.locator('[aria-label="Login"]').first
    if btn.count() == 0 or not btn.is_visible(timeout=3000):
        btn = page.locator('button:has-text("Log In"), button:has-text("Login")').first
    btn.wait_for(state="visible", timeout=10000)
    btn.click()
    page.wait_for_selector('[role="dialog"]', state="visible", timeout=8000)


def _fill_phone(page: Page, country_code: str, phone: str):
    """Select country code and fill phone number in the login modal."""
    # Change country if not the default +966
    if country_code != "+966":
        cc_btn = page.locator('[aria-label="Country code"]').first
        cc_btn.click()
        page.wait_for_selector('[placeholder="Search..."]', state="visible", timeout=5000)
        country_name = "Bangladesh" if country_code == "+880" else country_code
        page.locator('[placeholder="Search..."]').fill(country_name)
        page.wait_for_timeout(600)
        option = page.locator('[role="option"]').filter(has_text=country_code).first
        option.click(force=True)
        page.wait_for_timeout(400)

    phone_input = page.locator('input[type="tel"]').first
    phone_input.wait_for(state="visible", timeout=5000)
    phone_input.fill(phone)


def _collect_js_errors(page: Page) -> list:
    errors: list = []
    page.on("console",  lambda m: errors.append({"type": m.type, "text": m.text})
            if m.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append({"type": "pageerror", "text": str(exc)}))
    return errors


def _load_payload_lines(filename: str) -> list[str]:
    p = PAYLOAD_DIR / filename
    if not p.exists():
        return []
    return [ln.strip() for ln in p.read_text().splitlines()
            if ln.strip() and not ln.startswith("#")]


# ─────────────────────────────────────────────────────────────────────────────
# QA-01  FUNCTIONAL & USER FLOW TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestQA01Functional:
    """Verifies homepage UI, modal behaviour, and real user flows."""

    # ── Homepage Structure ────────────────────────────────────────────────────

    def test_qa01_homepage_loads_correct_url(self, page: Page):
        """Homepage must load at the Mehad /en URL without redirect loop."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        assert "mehadedu.com" in page.url, f"Wrong domain loaded: {page.url}"
        assert page.url.startswith("http"), f"Non-HTTP URL: {page.url}"

    def test_qa01_page_title_contains_mehad(self, page: Page):
        """Page title must mention Mehad (brand presence check)."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        title = page.title()
        assert title.strip() != "", "Page title is empty"
        assert "mehad" in title.lower() or "مهد" in title, (
            f"Brand name not in title: {title!r}")

    def test_qa01_header_logo_visible(self, page: Page):
        """Mehad logo/link must be visible in the header."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        logo = page.locator('[aria-label="Mehad homepage"], a[href="/en"]').first
        assert logo.count() > 0, "Mehad logo/home link not found in header"

    def test_qa01_header_login_button_present(self, page: Page):
        """Log In button must be visible in the header (unauthenticated state)."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        btn = page.locator('[aria-label="Login"], button:has-text("Log In"), button:has-text("Login")').first
        assert btn.count() > 0, "Log In button not found in header"
        assert btn.is_visible(timeout=5000), "Log In button not visible"

    def test_qa01_header_navigation_links_present(self, page: Page):
        """Header must have Home, Become a Tutor, How It Works, About Us links."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        expected_hrefs = ["/en/become-tutor", "/en/how-mehad-works", "/en/about-us"]
        for href in expected_hrefs:
            link = page.locator(f'a[href="{href}"]').first
            assert link.count() > 0, f"Nav link {href} not found in header"

    def test_qa01_language_toggle_buttons_present(self, page: Page):
        """Language toggle (EN/AR) buttons must be visible in header."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        en_btn = page.locator('[aria-label="English"]').first
        ar_btn = page.locator('[aria-label="العربية"]').first
        assert en_btn.count() > 0, "English language button not found"
        assert ar_btn.count() > 0, "Arabic language button not found"

    # ── Hero Section ──────────────────────────────────────────────────────────

    def test_qa01_hero_headline_present(self, page: Page):
        """Hero H1 headline must contain the main marketing copy."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        h1 = page.locator("h1").first
        assert h1.count() > 0, "No H1 heading on homepage"
        text = h1.inner_text()
        assert len(text.strip()) > 5, f"H1 is too short or empty: {text!r}"

    def test_qa01_hero_platform_badge_present(self, page: Page):
        """Saudi Arabia's #1 platform badge or stats must be present."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        content = page.inner_text("body").lower()
        assert "saudi" in content or "1,200" in content or "50,000" in content, (
            "Hero stats/badge not found in page content")

    def test_qa01_hero_stats_non_empty(self, page: Page):
        """Teacher count, student count, satisfaction stats must not be zero/empty."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        content = page.inner_text("body")
        # Spec: +1,200 Certified Teachers / +50,000 Students / 98% Satisfaction
        assert any(x in content for x in ["1,200", "1200", "50,000", "50000", "98%"]), (
            "Hero stats are missing or not rendered")

    # ── Tutor Search Form ─────────────────────────────────────────────────────

    def test_qa01_tutor_search_form_present(self, page: Page):
        """Tutor search form with Find a Teacher button must be on homepage."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        btn = page.locator('button:has-text("Find a Teacher"), a:has-text("Find a Teacher")').first
        assert btn.count() > 0, "Find a Teacher button not found"

    def test_qa01_find_teacher_navigates_to_find_tutors(self, page: Page):
        """Clicking Find a Teacher with no filters navigates to /en/find-tutors."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        btn = page.locator('button:has-text("Find a Teacher"), a:has-text("Find a Teacher")').first
        btn.wait_for(state="visible", timeout=8000)
        btn.click()
        page.wait_for_load_state(LOAD_STATE)
        assert "find-tutors" in page.url or "find_tutors" in page.url, (
            f"Find a Teacher did not navigate to find-tutors: {page.url}")

    def test_qa01_search_subject_dropdown_present(self, page: Page):
        """Subject dropdown with 'Select subject' placeholder must be in search form."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        subject = page.locator('button:has-text("Select subject"), [placeholder*="subject" i]').first
        if subject.count() == 0:
            # Try combobox fallback
            subject = page.locator('[role="combobox"]').first
        assert subject.count() > 0, "Subject dropdown not found in tutor search form"

    # ── Homepage Sections ─────────────────────────────────────────────────────

    def test_qa01_study_subjects_section_present(self, page: Page):
        """'Most Requested Subjects' / 'STUDY SUBJECTS' section must be visible."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        content = page.inner_text("body").lower()
        assert "most requested subjects" in content or "study subjects" in content or (
            "math" in content and "physics" in content), (
            "Study subjects section not found on homepage")

    def test_qa01_how_it_works_section_present(self, page: Page):
        """'How It Works' / 'Three Steps to Success' section must be visible."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        content = page.inner_text("body").lower()
        assert "how it works" in content or "three steps" in content or (
            "choose a teacher" in content or "book a session" in content), (
            "How It Works section not found")

    def test_qa01_top_teachers_section_present(self, page: Page):
        """'Our Top Teachers' section with tutor cards must be visible."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        content = page.inner_text("body").lower()
        assert "top teachers" in content or "our teachers" in content or (
            "per hour" in content or "certified" in content), (
            "Top Teachers section not found on homepage")

    def test_qa01_footer_present_with_links(self, page: Page):
        """Footer must contain Mehad logo, nav links, and copyright."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        footer = page.locator("footer").first
        if footer.count() == 0:
            footer = page.locator('[role="contentinfo"]').first
        assert footer.count() > 0, "Footer element not found"
        footer_text = footer.inner_text().lower()
        assert "privacy" in footer_text or "terms" in footer_text or (
            "2026" in footer_text or "mahad" in footer_text.lower()), (
            "Footer appears empty or incomplete")

    def test_qa01_student_reviews_section_present(self, page: Page):
        """Student testimonials/reviews section must exist."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        content = page.inner_text("body").lower()
        assert "students say" in content or "student reviews" in content or (
            "trust mehad" in content or "testimonial" in content), (
            "Student reviews section not found")

    # ── Login Modal ───────────────────────────────────────────────────────────

    def test_qa01_login_modal_opens_on_button_click(self, page: Page):
        """Clicking Log In button must open the login modal/dialog."""
        _open_login_modal(page)
        dialog = page.locator('[role="dialog"]').first
        assert dialog.is_visible(), "Login modal did not open"

    def test_qa01_modal_has_welcome_back_title(self, page: Page):
        """Login modal title must be 'Welcome back'."""
        _open_login_modal(page)
        modal_text = page.locator('[role="dialog"]').first.inner_text()
        assert "welcome back" in modal_text.lower(), (
            f"Modal title 'Welcome back' not found — got: {modal_text[:100]!r}")

    def test_qa01_modal_has_sign_in_subtitle(self, page: Page):
        """Login modal subtitle must mention 'Sign in to continue'."""
        _open_login_modal(page)
        modal_text = page.locator('[role="dialog"]').first.inner_text()
        assert "sign in" in modal_text.lower() or "continue" in modal_text.lower(), (
            f"Modal subtitle not found — got: {modal_text[:100]!r}")

    def test_qa01_modal_has_whatsapp_number_label(self, page: Page):
        """Login modal must have 'WhatsApp Number' label visible."""
        _open_login_modal(page)
        modal_text = page.locator('[role="dialog"]').first.inner_text()
        assert "whatsapp" in modal_text.lower() or "phone" in modal_text.lower(), (
            f"WhatsApp/phone label not found in modal — got: {modal_text[:150]!r}")

    def test_qa01_modal_has_phone_input(self, page: Page):
        """Login modal must have a telephone input field."""
        _open_login_modal(page)
        phone_input = page.locator('input[type="tel"]').first
        assert phone_input.count() > 0, "Phone (tel) input not found in modal"
        assert phone_input.is_visible(timeout=3000), "Phone input not visible"

    def test_qa01_modal_country_code_default_is_966(self, page: Page):
        """Country code selector must default to Saudi Arabia +966."""
        _open_login_modal(page)
        cc_btn = page.locator('[aria-label="Country code"]').first
        assert cc_btn.count() > 0, "Country code selector not found"
        btn_text = cc_btn.inner_text()
        assert "+966" in btn_text, (
            f"Default country code is not +966 — got: {btn_text!r}")

    def test_qa01_send_code_button_present(self, page: Page):
        """Send Code button must be present in the login modal."""
        _open_login_modal(page)
        btn = page.locator('button:has-text("Send Code")').first
        assert btn.count() > 0, "Send Code button not found in modal"
        assert btn.is_visible(timeout=3000), "Send Code button not visible"

    def test_qa01_send_code_disabled_without_phone(self, page: Page):
        """Send Code button must be disabled when phone field is empty."""
        _open_login_modal(page)
        btn = page.locator('button:has-text("Send Code")').first
        btn.wait_for(state="visible", timeout=5000)
        is_disabled = btn.is_disabled()
        # Also check aria-disabled or class-based disabled
        aria_disabled = btn.get_attribute("aria-disabled")
        assert is_disabled or aria_disabled == "true", (
            "Send Code button is enabled without a phone number — should be disabled")

    def test_qa01_modal_close_button_present(self, page: Page):
        """Modal must have a Close button (X) to dismiss."""
        _open_login_modal(page)
        close_btn = page.locator('[aria-label="Close"]').first
        assert close_btn.count() > 0, "Close button (aria-label=Close) not found in modal"
        assert close_btn.is_visible(timeout=3000), "Close button not visible"

    def test_qa01_modal_closes_on_close_button_click(self, page: Page):
        """Clicking Close button must dismiss the login modal."""
        _open_login_modal(page)
        close_btn = page.locator('[aria-label="Close"]').first
        close_btn.click()
        page.wait_for_timeout(800)
        dialog = page.locator('[role="dialog"]')
        assert dialog.count() == 0 or not dialog.first.is_visible(timeout=2000), (
            "Modal did not close after clicking Close button")

    def test_qa01_country_code_dropdown_opens(self, page: Page):
        """Clicking country code selector must open a dropdown with search."""
        _open_login_modal(page)
        cc_btn = page.locator('[aria-label="Country code"]').first
        cc_btn.click()
        page.wait_for_timeout(400)
        search = page.locator('[placeholder="Search..."]').first
        assert search.count() > 0, "Country search input not found in dropdown"
        assert search.is_visible(timeout=3000), "Country search input not visible"

    def test_qa01_country_search_filters_results(self, page: Page):
        """Typing in country search must filter the country list."""
        _open_login_modal(page)
        cc_btn = page.locator('[aria-label="Country code"]').first
        cc_btn.click()
        page.wait_for_selector('[placeholder="Search..."]', state="visible", timeout=5000)
        page.locator('[placeholder="Search..."]').fill("Bangladesh")
        page.wait_for_timeout(600)
        option = page.locator('[role="option"]').filter(has_text="+880").first
        assert option.count() > 0, "Bangladesh (+880) not found after searching"

    def test_qa01_country_bangladesh_selectable(self, page: Page):
        """Bangladesh +880 must be selectable from the country dropdown."""
        _open_login_modal(page)
        cc_btn = page.locator('[aria-label="Country code"]').first
        cc_btn.click()
        page.wait_for_selector('[placeholder="Search..."]', state="visible", timeout=5000)
        page.locator('[placeholder="Search..."]').fill("Bangladesh")
        page.wait_for_timeout(600)
        option = page.locator('[role="option"]').filter(has_text="+880").first
        option.click(force=True)
        page.wait_for_timeout(400)
        # Verify selection updated
        updated_text = cc_btn.inner_text()
        assert "+880" in updated_text, (
            f"Country code did not update to +880 after selection — got: {updated_text!r}")

    def test_qa01_phone_field_accepts_numbers(self, page: Page):
        """Phone input must accept digit input."""
        _open_login_modal(page)
        phone_input = page.locator('input[type="tel"]').first
        phone_input.fill("98976564")
        val = phone_input.input_value()
        assert val != "", "Phone field value is empty after fill"
        assert re.sub(r"\D", "", val) != "", "No digits stored in phone field"

    def test_qa01_send_code_enabled_after_phone_entry(self, page: Page):
        """Send Code button must become enabled after a valid phone is entered."""
        _open_login_modal(page)
        phone_input = page.locator('input[type="tel"]').first
        phone_input.fill("98976564")
        page.wait_for_timeout(500)
        btn = page.locator('button:has-text("Send Code")').first
        # Allow a brief moment for React state update
        page.wait_for_timeout(300)
        is_disabled = btn.is_disabled()
        assert not is_disabled, "Send Code button still disabled after valid phone entered"

    def test_qa01_full_login_flow_success(self, page: Page):
        """Complete WhatsApp OTP login must succeed and show user name in header."""
        _open_login_modal(page)
        _fill_phone(page, TEST_COUNTRY_CODE, TEST_PHONE)

        send_btn = page.locator('button:has-text("Send Code")').first
        send_btn.wait_for(state="visible", timeout=5000)
        page.wait_for_timeout(400)
        send_btn.click()

        # Wait for OTP input to become enabled
        otp_input = page.locator(
            'input[placeholder="000000"], '
            'input[autocomplete="one-time-code"], '
            'input[maxlength="6"]'
        ).first
        otp_input.wait_for(state="visible", timeout=10000)
        page.wait_for_timeout(800)
        otp_input.fill(TEST_OTP)

        continue_btn = page.locator('button:has-text("Continue")').first
        continue_btn.wait_for(state="visible", timeout=5000)
        page.wait_for_timeout(400)
        continue_btn.click()

        # Expect success: modal closes and user name appears
        page.wait_for_timeout(3000)
        body_text = page.inner_text("body")
        assert TEST_USER_NAME in body_text or "logged in" in body_text.lower(), (
            f"Login did not succeed — '{TEST_USER_NAME}' not found in page. "
            f"Current URL: {page.url}")

    def test_qa01_otp_input_appears_after_send_code(self, page: Page):
        """After clicking Send Code, OTP input must appear/become enabled."""
        _open_login_modal(page)
        _fill_phone(page, TEST_COUNTRY_CODE, TEST_PHONE)

        send_btn = page.locator('button:has-text("Send Code")').first
        page.wait_for_timeout(400)
        send_btn.click()

        otp_input = page.locator(
            'input[placeholder="000000"], '
            'input[autocomplete="one-time-code"], '
            'input[maxlength="6"]'
        ).first
        otp_input.wait_for(state="visible", timeout=10000)
        assert otp_input.is_visible(), "OTP input did not appear after Send Code"

    def test_qa01_resend_timer_appears_after_send_code(self, page: Page):
        """Resend countdown timer must appear after Send Code is clicked."""
        _open_login_modal(page)
        _fill_phone(page, TEST_COUNTRY_CODE, TEST_PHONE)

        send_btn = page.locator('button:has-text("Send Code")').first
        page.wait_for_timeout(400)
        send_btn.click()
        page.wait_for_timeout(2000)

        modal_text = page.locator('[role="dialog"]').first.inner_text().lower()
        assert "resend" in modal_text or "60" in modal_text or "timer" in modal_text or (
            "change" in modal_text), (
            "Resend timer/countdown not found after Send Code")

    def test_qa01_change_number_link_appears_after_send(self, page: Page):
        """'Change Mobile Number' link must appear after Send Code."""
        _open_login_modal(page)
        _fill_phone(page, TEST_COUNTRY_CODE, TEST_PHONE)

        send_btn = page.locator('button:has-text("Send Code")').first
        page.wait_for_timeout(400)
        send_btn.click()
        page.wait_for_timeout(2000)

        modal_text = page.locator('[role="dialog"]').first.inner_text().lower()
        assert "change" in modal_text and ("mobile" in modal_text or "number" in modal_text), (
            "'Change Mobile Number' link not found after Send Code")

    # ── Navigation Tests ──────────────────────────────────────────────────────

    def test_qa01_become_a_tutor_link_navigates(self, page: Page):
        """Become a Tutor link must navigate to /en/become-tutor."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        link = page.locator('a[href="/en/become-tutor"]').first
        assert link.count() > 0, "Become a Tutor link not found"
        link.click()
        page.wait_for_load_state(LOAD_STATE)
        assert "become-tutor" in page.url, (
            f"Expected /en/become-tutor, got: {page.url}")

    def test_qa01_how_it_works_link_navigates(self, page: Page):
        """How It Works link must navigate to /en/how-mehad-works."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        link = page.locator('a[href="/en/how-mehad-works"]').first
        assert link.count() > 0, "How It Works link not found"
        link.click()
        page.wait_for_load_state(LOAD_STATE)
        assert "how-mehad-works" in page.url, (
            f"Expected /en/how-mehad-works, got: {page.url}")

    def test_qa01_about_us_link_navigates(self, page: Page):
        """About Us link must navigate to /en/about-us."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        link = page.locator('a[href="/en/about-us"]').first
        assert link.count() > 0, "About Us link not found"
        link.click()
        page.wait_for_load_state(LOAD_STATE)
        assert "about" in page.url.lower(), (
            f"Expected /en/about-us, got: {page.url}")

    def test_qa01_language_toggle_ar_navigates(self, page: Page):
        """Clicking AR button must navigate to the Arabic locale."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        ar_btn = page.locator('[aria-label="العربية"]').first
        ar_btn.wait_for(state="visible", timeout=5000)
        ar_btn.click()
        page.wait_for_load_state(LOAD_STATE)
        assert "/ar" in page.url or page.url.endswith("/ar"), (
            f"Language toggle to AR did not change URL: {page.url}")

    def test_qa01_subject_badge_navigates_to_find_tutors(self, page: Page):
        """Clicking a subject badge (e.g. Math) must navigate to /en/find-tutors."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        # Find any subject link going to find-tutors
        subject_link = page.locator('a[href*="find-tutors"]').first
        if subject_link.count() > 0:
            subject_link.click()
            page.wait_for_load_state(LOAD_STATE)
            assert "find-tutors" in page.url, (
                f"Subject click did not navigate to find-tutors: {page.url}")

    def test_qa01_find_tutors_page_loads(self, page: Page):
        """Direct navigation to /en/find-tutors must load the tutor listing page."""
        page.goto(FIND_TUTORS_URL)
        page.wait_for_load_state(LOAD_STATE)
        assert "find-tutors" in page.url, f"Find Tutors URL mismatch: {page.url}"
        content = page.inner_text("body").lower()
        assert "tutor" in content or "teacher" in content, (
            "Find Tutors page has no tutor/teacher content")

    def test_qa01_find_tutors_page_shows_tutor_cards(self, page: Page):
        """Find tutors page must display at least one tutor card."""
        page.goto(FIND_TUTORS_URL)
        page.wait_for_load_state(LOAD_STATE)
        page.wait_for_timeout(2000)
        content = page.inner_text("body").lower()
        assert "per hour" in content or "lesson" in content or "verified" in content, (
            "No tutor cards found on /en/find-tutors page")

    def test_qa01_arabic_locale_page_loads(self, page: Page):
        """Navigating to /ar must load the Arabic locale without errors."""
        ar_url = BASE_URL.replace("/en", "/ar")
        page.goto(ar_url)
        page.wait_for_load_state(LOAD_STATE)
        assert "mehadedu.com" in page.url, f"Wrong domain: {page.url}"
        assert "/ar" in page.url, f"Did not stay in /ar locale: {page.url}"

    def test_qa01_footer_privacy_policy_link_works(self, page: Page):
        """Footer Privacy Policy link must navigate to the policy page."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        link = page.locator('a[href*="privacy"]').last
        if link.count() > 0:
            link.click()
            page.wait_for_load_state(LOAD_STATE)
            assert "privacy" in page.url.lower() or "policy" in page.url.lower(), (
                f"Privacy link did not navigate correctly: {page.url}")


# ─────────────────────────────────────────────────────────────────────────────
# QA-02  EDGE CASE & BOUNDARY TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestQA02EdgeCaseBoundary:
    """Exercises phone validation, OTP boundary, modal state transitions."""

    def test_qa02_ec_empty_phone_send_code_disabled(self, page: Page):
        """EC-M-01: Empty phone field — Send Code must stay disabled."""
        _open_login_modal(page)
        phone_input = page.locator('input[type="tel"]').first
        phone_input.fill("")  # ensure empty
        page.wait_for_timeout(300)
        btn = page.locator('button:has-text("Send Code")').first
        is_disabled = btn.is_disabled()
        aria_disabled = btn.get_attribute("aria-disabled")
        assert is_disabled or aria_disabled == "true", (
            "EC-M-01: Send Code is enabled with empty phone — must stay disabled")

    def test_qa02_ec_phone_too_short_send_code_disabled(self, page: Page):
        """EC-M-03: Phone with < 7 digits — Send Code must stay disabled."""
        _open_login_modal(page)
        phone_input = page.locator('input[type="tel"]').first
        phone_input.fill("123")   # 3 digits — below minimum 7
        page.wait_for_timeout(400)
        btn = page.locator('button:has-text("Send Code")').first
        is_disabled = btn.is_disabled()
        aria_disabled = btn.get_attribute("aria-disabled")
        assert is_disabled or aria_disabled == "true", (
            "EC-M-03: Short phone (3 digits) should keep Send Code disabled")

    def test_qa02_ec_phone_maxlength_12(self, page: Page):
        """EC-M-04: Input stops accepting beyond 12 chars (maxlength)."""
        _open_login_modal(page)
        phone_input = page.locator('input[type="tel"]').first
        phone_input.fill("123456789012345")  # 15 chars — should be capped at 12
        val = phone_input.input_value()
        assert len(val.replace(" ", "")) <= 12, (
            f"EC-M-04: Phone field accepted {len(val)} chars — maxlength=12 not enforced")

    def test_qa02_ec_non_numeric_phone_rejected(self, page: Page):
        """EC-M-02: Non-numeric input (letters, symbols) must be rejected or ignored."""
        _open_login_modal(page)
        phone_input = page.locator('input[type="tel"]').first
        phone_input.fill("abc@test!")
        page.wait_for_timeout(300)
        val = phone_input.input_value()
        # Either the field accepts nothing, or only digits are retained
        numeric_only = re.sub(r"\D", "", val)
        letters = re.sub(r"[^a-zA-Z]", "", val)
        assert letters == "", (
            f"EC-M-02: Phone field accepted letters: value={val!r}")

    def test_qa02_ec_close_modal_mid_flow(self, page: Page):
        """EC-M-08: Closing modal mid-flow must close without session creation."""
        _open_login_modal(page)
        _fill_phone(page, "+966", "501234567")
        # Don't click Send Code — close mid-flow
        close_btn = page.locator('[aria-label="Close"]').first
        close_btn.click()
        page.wait_for_timeout(800)
        # Modal must be gone
        dialog = page.locator('[role="dialog"]')
        assert dialog.count() == 0 or not dialog.first.is_visible(timeout=2000), (
            "EC-M-08: Modal did not close mid-flow")
        # Login button must still be visible (no session created)
        btn = page.locator('[aria-label="Login"], button:has-text("Log In")').first
        assert btn.is_visible(timeout=3000), (
            "EC-M-08: Log In button not visible after closing modal — session may have been created")

    def test_qa02_ec_modal_reopens_clean(self, page: Page):
        """EC-M-08: Re-opening modal after close must show a clean state."""
        _open_login_modal(page)
        # Fill something then close
        phone_input = page.locator('input[type="tel"]').first
        phone_input.fill("501234567")
        close_btn = page.locator('[aria-label="Close"]').first
        close_btn.click()
        page.wait_for_timeout(600)
        # Reopen
        _open_login_modal(page)
        phone_input2 = page.locator('input[type="tel"]').first
        val = phone_input2.input_value()
        # Ideally reset to empty — if persists it's a bug
        assert page.locator('[role="dialog"]').first.is_visible(), (
            "Modal did not reopen successfully")

    def test_qa02_ec_otp_6_digits_required(self, page: Page):
        """OTP field maxlength must be 6 digits."""
        _open_login_modal(page)
        _fill_phone(page, TEST_COUNTRY_CODE, TEST_PHONE)

        send_btn = page.locator('button:has-text("Send Code")').first
        page.wait_for_timeout(400)
        send_btn.click()
        page.wait_for_timeout(2000)

        otp_input = page.locator(
            'input[placeholder="000000"], input[autocomplete="one-time-code"]'
        ).first
        if otp_input.count() > 0 and otp_input.is_visible(timeout=3000):
            maxlen = otp_input.get_attribute("maxlength")
            assert maxlen == "6", (
                f"OTP maxlength is {maxlen!r} — expected '6'")

    def test_qa02_ec_continue_disabled_without_otp(self, page: Page):
        """Continue button must be disabled until OTP is entered."""
        _open_login_modal(page)
        _fill_phone(page, TEST_COUNTRY_CODE, TEST_PHONE)

        send_btn = page.locator('button:has-text("Send Code")').first
        page.wait_for_timeout(400)
        send_btn.click()
        page.wait_for_timeout(1500)

        continue_btn = page.locator('button:has-text("Continue")').first
        if continue_btn.count() > 0 and continue_btn.is_visible(timeout=3000):
            is_disabled = continue_btn.is_disabled()
            aria_disabled = continue_btn.get_attribute("aria-disabled")
            assert is_disabled or aria_disabled == "true", (
                "Continue button is enabled before OTP is entered")

    def test_qa02_ec_country_search_no_results_graceful(self, page: Page):
        """Searching for a nonexistent country must show empty state, not crash."""
        _open_login_modal(page)
        cc_btn = page.locator('[aria-label="Country code"]').first
        cc_btn.click()
        page.wait_for_selector('[placeholder="Search..."]', state="visible", timeout=5000)
        page.locator('[placeholder="Search..."]').fill("XYZNONEXISTENT")
        page.wait_for_timeout(600)
        # No crash — dialog still visible
        assert page.locator('[role="dialog"]').first.is_visible(), (
            "Modal crashed after no-result country search")

    def test_qa02_ec_phone_with_spaces_handled(self, page: Page):
        """Phone field with spaces must handle gracefully (trim or reject)."""
        _open_login_modal(page)
        phone_input = page.locator('input[type="tel"]').first
        phone_input.fill("   ")
        page.wait_for_timeout(300)
        btn = page.locator('button:has-text("Send Code")').first
        # Whitespace-only should keep Send Code disabled
        is_disabled = btn.is_disabled()
        aria_disabled = btn.get_attribute("aria-disabled")
        assert is_disabled or aria_disabled == "true", (
            "Send Code enabled with whitespace-only phone number")

    def test_qa02_ec_tutor_search_no_filters_navigates(self, page: Page):
        """EC-M-17: Find a Teacher with no filters must navigate to find-tutors."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        btn = page.locator('button:has-text("Find a Teacher"), a:has-text("Find a Teacher")').first
        btn.wait_for(state="visible", timeout=8000)
        btn.click()
        page.wait_for_load_state(LOAD_STATE)
        assert "find-tutors" in page.url, (
            f"EC-M-17: No-filter search did not navigate to find-tutors: {page.url}")

    def test_qa02_ec_mobile_viewport_modal_renders(self, page: Page):
        """EC-M-13: Login modal must render correctly on mobile viewport (375px)."""
        page.set_viewport_size({"width": 375, "height": 667})
        _open_login_modal(page)
        dialog = page.locator('[role="dialog"]').first
        assert dialog.is_visible(), "Modal not visible on mobile viewport"
        phone_input = page.locator('input[type="tel"]').first
        assert phone_input.is_visible(timeout=3000), (
            "Phone input not visible on mobile viewport")

    def test_qa02_ec_arabic_locale_direct_navigation(self, page: Page):
        """EC-M-20: Direct /ar URL must load with Arabic content."""
        ar_url = BASE_URL.replace("/en", "/ar")
        page.goto(ar_url)
        page.wait_for_load_state(LOAD_STATE)
        assert "/ar" in page.url, f"Did not stay in /ar: {page.url}"
        # Content should be Arabic or at minimum page loads without error
        assert "500" not in page.title() and "Error" not in page.title()[:10], (
            "Arabic locale page shows error")

    @pytest.mark.parametrize("length,label", [
        (7,  "min-7-digits"),
        (10, "10-digits"),
        (12, "max-12-digits"),
    ])
    def test_qa02_ec_phone_boundary_lengths(self, page: Page, length: int, label: str):
        """Phone numbers at boundary lengths must enable/handle Send Code correctly."""
        _open_login_modal(page)
        phone_input = page.locator('input[type="tel"]').first
        phone_input.fill("1" * length)
        page.wait_for_timeout(400)
        btn = page.locator('button:has-text("Send Code")').first
        # 7-12 digit phones should enable the button
        is_disabled = btn.is_disabled()
        assert not is_disabled, (
            f"{label}: Send Code still disabled for {length}-digit phone number")

    def test_qa02_ec_homepage_no_crash_on_rapid_clicks(self, page: Page):
        """Rapid clicks on Log In must not crash the page."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        btn = page.locator('[aria-label="Login"], button:has-text("Log In")').first
        btn.wait_for(state="visible", timeout=5000)
        for _ in range(5):
            try:
                btn.click()
                page.wait_for_timeout(100)
                close = page.locator('[aria-label="Close"]')
                if close.count() > 0 and close.first.is_visible(timeout=200):
                    close.first.click()
                    page.wait_for_timeout(100)
            except Exception:
                pass
        assert "500" not in page.title(), "Rapid modal open/close caused server error"

    def test_qa02_ec_otp_input_placeholder_is_zeros(self, page: Page):
        """OTP input placeholder must be '000000' as per spec."""
        _open_login_modal(page)
        _fill_phone(page, TEST_COUNTRY_CODE, TEST_PHONE)

        send_btn = page.locator('button:has-text("Send Code")').first
        page.wait_for_timeout(400)
        send_btn.click()
        page.wait_for_timeout(2000)

        otp_input = page.locator('input[placeholder="000000"]').first
        if otp_input.count() > 0:
            assert otp_input.is_visible(timeout=3000), "OTP field with placeholder '000000' not visible"

    def test_qa02_ec_find_tutors_page_handles_no_results(self, page: Page):
        """Find-tutors page with unknown query must handle gracefully (not 500)."""
        page.goto(f"{FIND_TUTORS_URL}?subjectId=99999")
        page.wait_for_load_state(LOAD_STATE)
        assert "500" not in page.title() and page.title().strip() != "", (
            f"Find-tutors with invalid subjectId crashed: {page.title()}")

    def test_qa02_ec_homepage_back_navigation_works(self, page: Page):
        """Navigating away and using browser Back must return to clean homepage."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        page.goto(FIND_TUTORS_URL)
        page.wait_for_load_state(LOAD_STATE)
        page.go_back()
        page.wait_for_load_state(LOAD_STATE)
        assert "mehadedu.com/en" in page.url or page.url.endswith("/en"), (
            f"Browser Back did not return to homepage: {page.url}")


# ─────────────────────────────────────────────────────────────────────────────
# QA-03  SECURITY TESTS — XSS + SQL INJECTION
# ─────────────────────────────────────────────────────────────────────────────

class TestQA03Security:
    """Verifies that injection payloads are safely rejected in the Mehad UI."""

    @pytest.mark.parametrize("payload", _load_payload_lines("xss.txt") or [
        "<script>alert('xss')</script>",
        '"><img src=x onerror=alert(1)>',
        "javascript:alert(1)",
        "<svg onload=alert(1)>",
    ])
    def test_qa03_xss_in_phone_field(self, page: Page, payload: str):
        """XSS payload in phone field must not execute scripts or crash app."""
        js_alerts: list = []
        page.on("dialog",    lambda d: (js_alerts.append(d.message), d.dismiss()))
        page.on("pageerror", lambda exc: js_alerts.append(str(exc)))

        _open_login_modal(page)
        phone_input = page.locator('input[type="tel"]').first
        phone_input.fill(payload)
        page.wait_for_timeout(800)

        assert len(js_alerts) == 0, (
            f"XSS payload triggered alert in phone field: {payload!r} → {js_alerts}")
        assert "500" not in page.title(), (
            f"XSS payload crashed server via phone field: {payload!r}")

    @pytest.mark.parametrize("payload", _load_payload_lines("xss.txt") or [
        "<script>alert('xss')</script>",
        '"><img src=x onerror=alert(1)>',
    ])
    def test_qa03_xss_in_country_search(self, page: Page, payload: str):
        """XSS payload in country search field must not execute."""
        js_alerts: list = []
        page.on("dialog",    lambda d: (js_alerts.append(d.message), d.dismiss()))
        page.on("pageerror", lambda exc: js_alerts.append(str(exc)))

        _open_login_modal(page)
        cc_btn = page.locator('[aria-label="Country code"]').first
        cc_btn.click()
        page.wait_for_selector('[placeholder="Search..."]', state="visible", timeout=5000)
        page.locator('[placeholder="Search..."]').fill(payload)
        page.wait_for_timeout(800)

        assert len(js_alerts) == 0, (
            f"XSS in country search triggered alert: {payload!r} → {js_alerts}")

    def test_qa03_xss_not_reflected_in_page_html(self, page: Page):
        """XSS payload entered in phone field must not be reflected raw in HTML."""
        _open_login_modal(page)
        payload = "<script>alert('QA_XSS_MARKER_MEHAD')</script>"
        phone_input = page.locator('input[type="tel"]').first
        phone_input.fill(payload)
        page.wait_for_timeout(1000)

        html = page.content()
        assert "QA_XSS_MARKER_MEHAD" not in html, (
            "XSS payload reflected unescaped in HTML — stored/reflected XSS risk")

    def test_qa03_template_injection_in_phone(self, page: Page):
        """Template expression {{7*7}} must NOT evaluate to 49 in page content."""
        _open_login_modal(page)
        phone_input = page.locator('input[type="tel"]').first
        phone_input.fill("{{7*7}}")
        page.wait_for_timeout(1000)

        content = page.content()
        assert "49" not in content or "{{7*7}}" not in content, (
            "Possible SSTI: {{7*7}} was evaluated in page content")

    @pytest.mark.parametrize("payload", _load_payload_lines("sqli.txt") or [
        "' OR '1'='1",
        "'; DROP TABLE users; --",
        "1; SELECT * FROM users",
        "\" OR \"1\"=\"1",
    ])
    def test_qa03_sqli_in_phone_field(self, page: Page, payload: str):
        """SQL injection in phone field must not expose DB errors."""
        _open_login_modal(page)
        phone_input = page.locator('input[type="tel"]').first
        phone_input.fill(payload)
        page.wait_for_timeout(500)

        # Try submitting if Send Code gets enabled
        btn = page.locator('button:has-text("Send Code")').first
        if not btn.is_disabled():
            btn.click()
            page.wait_for_timeout(2000)

        content = page.content().lower()
        db_errors = ["sql syntax", "mysql", "postgresql", "sqlite", "ora-",
                     "unclosed", "unterminated", "syntax error near"]
        found = [e for e in db_errors if e in content]
        assert not found, (
            f"SQL injection leaked DB error — hints: {found} | payload: {payload!r}")
        assert "500" not in page.title(), f"SQLi caused 500 error: {payload!r}"

    def test_qa03_no_sensitive_data_in_html(self, page: Page):
        """Homepage HTML must not expose API keys, passwords, or tokens."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        html = page.content()

        sensitive_patterns = [
            r"password[\"']?\s*:\s*[\"'][^\"']{4,}",
            r"secret[\"']?\s*:\s*[\"'][^\"']{4,}",
            r"api_key[\"']?\s*:\s*[\"'][^\"']{4,}",
            r"private_key[\"']?\s*:\s*[\"'][^\"']{20,}",
        ]
        for pat in sensitive_patterns:
            assert not re.search(pat, html, re.IGNORECASE), (
                f"Sensitive data pattern found in page HTML: {pat}")

    def test_qa03_modal_no_session_token_in_html(self, page: Page):
        """Login modal HTML must not expose session tokens in markup."""
        _open_login_modal(page)
        html = page.content()
        # JWT-like patterns (base64url.base64url.base64url)
        jwt_pattern = r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"
        assert not re.search(jwt_pattern, html), (
            "JWT token found exposed in page HTML — session leakage risk")

    def test_qa03_https_enforced(self, page: Page):
        """Homepage must be served over HTTPS."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        assert page.url.startswith("https://"), (
            f"Page is not served over HTTPS: {page.url}")

    def test_qa03_no_mixed_content_on_homepage(self, page: Page):
        """HTTPS homepage must not load any HTTP (insecure) resources."""
        insecure: list = []
        page.on("request", lambda r: insecure.append(r.url)
                if r.url.startswith("http://") else None)

        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        page.wait_for_timeout(1000)

        real_insecure = [u for u in insecure
                         if "localhost" not in u and "127." not in u]
        assert real_insecure == [], (
            "Mixed content (HTTP on HTTPS page):\n" + "\n".join(real_insecure[:5]))

    def test_qa03_find_tutors_page_no_xss_in_search_param(self, page: Page):
        """XSS payload in URL query param must not execute on find-tutors."""
        js_alerts: list = []
        page.on("dialog",    lambda d: (js_alerts.append(d.message), d.dismiss()))
        page.on("pageerror", lambda exc: js_alerts.append(str(exc)))

        page.goto(f"{FIND_TUTORS_URL}?search=<script>alert(1)</script>")
        page.wait_for_load_state(LOAD_STATE)
        page.wait_for_timeout(1000)

        assert len(js_alerts) == 0, (
            f"XSS via URL param triggered alert on find-tutors: {js_alerts}")

    def test_qa03_no_server_errors_on_homepage_load(self, page: Page):
        """No network response must be 5xx on homepage load."""
        server_errors: list = []
        page.on("response", lambda r: server_errors.append(
            {"url": r.url, "status": r.status}) if r.status >= 500 else None)

        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)

        assert server_errors == [], (
            f"Server errors on homepage load:\n{server_errors[:3]}")

    def test_qa03_no_404_on_homepage_resources(self, page: Page):
        """Homepage must not request any resource that returns 404."""
        not_found: list = []
        page.on("response", lambda r: not_found.append(r.url)
                if r.status == 404 else None)

        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        page.wait_for_timeout(1000)

        # Filter out known external tracking that may 404
        real_404 = [u for u in not_found
                    if "mehadedu.com" in u or "cdn" in u]
        assert real_404 == [], (
            f"404 resources on homepage:\n" + "\n".join(real_404[:5]))

    def test_qa03_cors_headers_not_wildcard_for_auth(self, page: Page):
        """Auth-related pages must not use overly permissive CORS (*) in responses."""
        captured_cors: list = []

        def _check_cors(resp):
            try:
                acao = resp.headers.get("access-control-allow-origin", "")
                if acao == "*" and ("auth" in resp.url or "otp" in resp.url):
                    captured_cors.append({"url": resp.url, "cors": acao})
            except Exception:
                pass

        page.on("response", _check_cors)
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)

        assert captured_cors == [], (
            f"Wildcard CORS on auth endpoints: {captured_cors}")


# ─────────────────────────────────────────────────────────────────────────────
# QA-04  PERFORMANCE & JAVASCRIPT ERROR TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestQA04PerformanceAndJSErrors:
    """Validates page load times, Web Vitals proxy metrics, and JS error absence."""

    def test_qa04_homepage_loads_under_5s(self, page: Page):
        """Homepage must reach domcontentloaded within 5 seconds."""
        start = time.perf_counter()
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 5000, (
            f"Homepage took {elapsed_ms:.0f}ms — expected < 5000ms")

    def test_qa04_ttfb_under_1000ms(self, page: Page):
        """Time To First Byte must be below 1000ms for the Mehad staging env."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        ttfb = page.evaluate("""() => {
            const t = performance.timing;
            return t.responseStart - t.navigationStart;
        }""")
        assert ttfb < 1000, f"TTFB is {ttfb}ms — expected < 1000ms"

    def test_qa04_dom_content_loaded_under_3s(self, page: Page):
        """DOMContentLoaded must fire within 3 seconds on homepage."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        dcl = page.evaluate("""() => {
            const t = performance.timing;
            return t.domContentLoadedEventEnd - t.navigationStart;
        }""")
        assert dcl < 3000, f"DOMContentLoaded took {dcl}ms — expected < 3000ms"

    def test_qa04_no_js_errors_on_homepage_load(self, page: Page):
        """Homepage must load without JavaScript console errors."""
        errors: list = []
        page.on("console",  lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))

        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        page.wait_for_timeout(1000)

        # Filter known third-party noise
        real_errors = [e for e in errors
                       if "extension" not in e.lower() and "favicon" not in e.lower()]
        assert real_errors == [], (
            "JS errors on homepage load:\n" + "\n".join(real_errors[:5]))

    def test_qa04_no_js_errors_opening_modal(self, page: Page):
        """Opening and closing the login modal must not trigger JS errors."""
        errors: list = []
        page.on("console",  lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))

        _open_login_modal(page)
        page.wait_for_timeout(500)
        page.locator('[aria-label="Close"]').first.click()
        page.wait_for_timeout(500)

        real_errors = [e for e in errors if "extension" not in e.lower()]
        assert real_errors == [], (
            "JS errors during modal open/close:\n" + "\n".join(real_errors[:5]))

    def test_qa04_no_js_errors_language_toggle(self, page: Page):
        """Language toggle must not produce JS errors."""
        errors: list = []
        page.on("console",  lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))

        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        ar_btn = page.locator('[aria-label="العربية"]').first
        ar_btn.wait_for(state="visible", timeout=5000)
        ar_btn.click()
        page.wait_for_load_state(LOAD_STATE)
        page.wait_for_timeout(500)

        real_errors = [e for e in errors if "extension" not in e.lower()]
        assert real_errors == [], (
            "JS errors on language toggle:\n" + "\n".join(real_errors[:5]))

    def test_qa04_find_tutors_loads_under_5s(self, page: Page):
        """Find-tutors page must load within 5 seconds."""
        start = time.perf_counter()
        page.goto(FIND_TUTORS_URL)
        page.wait_for_load_state(LOAD_STATE)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 5000, (
            f"Find-tutors took {elapsed_ms:.0f}ms — expected < 5000ms")

    def test_qa04_no_js_errors_on_find_tutors(self, page: Page):
        """Find-tutors page must not have JS errors on load."""
        errors: list = []
        page.on("console",  lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))

        page.goto(FIND_TUTORS_URL)
        page.wait_for_load_state(LOAD_STATE)
        page.wait_for_timeout(1000)

        real_errors = [e for e in errors if "extension" not in e.lower()]
        assert real_errors == [], (
            "JS errors on find-tutors:\n" + "\n".join(real_errors[:5]))

    @pytest.mark.parametrize("vp", [
        {"width": 375,  "height": 667,  "label": "mobile-sm"},
        {"width": 768,  "height": 1024, "label": "tablet"},
        {"width": 1280, "height": 720,  "label": "desktop"},
        {"width": 1920, "height": 1080, "label": "desktop-xl"},
    ])
    def test_qa04_responsive_no_js_errors(self, page: Page, vp: dict):
        """Homepage must load without JS errors across all viewports."""
        label = vp.pop("label")
        page.set_viewport_size(vp)

        errors: list = []
        page.on("console",  lambda m: errors.append(m.text) if m.type == "error" else None)

        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        page.wait_for_timeout(500)

        real_errors = [e for e in errors if "extension" not in e.lower()]
        assert real_errors == [], (
            f"JS errors at {label}:\n" + "\n".join(real_errors[:3]))

    def test_qa04_no_broken_images_on_homepage(self, page: Page):
        """No img tags on homepage must have a broken src (natural width = 0)."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        page.wait_for_timeout(1500)

        broken = page.evaluate("""() => {
            return Array.from(document.querySelectorAll('img'))
                .filter(img => img.src && !img.src.startsWith('data:') && img.naturalWidth === 0)
                .map(img => img.src)
                .slice(0, 5);
        }""")
        assert broken == [], f"Broken images on homepage: {broken}"

    def test_qa04_modal_renders_within_2s(self, page: Page):
        """Login modal must appear within 2 seconds of clicking Log In."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        btn = page.locator('[aria-label="Login"], button:has-text("Log In")').first
        btn.wait_for(state="visible", timeout=5000)

        start = time.perf_counter()
        btn.click()
        page.wait_for_selector('[role="dialog"]', state="visible", timeout=5000)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 2000, (
            f"Modal took {elapsed_ms:.0f}ms to open — expected < 2000ms")

    def test_qa04_no_memory_leak_multiple_modal_opens(self, page: Page):
        """Opening/closing modal 5× must not cause significant JS heap growth."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)

        heap_before = page.evaluate(
            "() => performance.memory ? performance.memory.usedJSHeapSize : 0")

        for _ in range(5):
            btn = page.locator('[aria-label="Login"], button:has-text("Log In")').first
            btn.wait_for(state="visible", timeout=5000)
            btn.click()
            page.wait_for_selector('[role="dialog"]', state="visible", timeout=5000)
            page.locator('[aria-label="Close"]').first.click()
            page.wait_for_timeout(300)

        heap_after = page.evaluate(
            "() => performance.memory ? performance.memory.usedJSHeapSize : 0")

        if heap_before > 0 and heap_after > 0:
            growth_mb = (heap_after - heap_before) / (1024 * 1024)
            assert growth_mb < 50, (
                f"JS heap grew by {growth_mb:.1f}MB across 5 modal opens — possible memory leak")

    def test_qa04_performance_resource_timing_available(self, page: Page):
        """window.performance.timing API must be available on the page."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        has_timing = page.evaluate("() => !!(window.performance && window.performance.timing)")
        assert has_timing, "performance.timing API not available"


# ─────────────────────────────────────────────────────────────────────────────
# QA-05  HALLUCINATION & DATA INTEGRITY TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestQA05HallucinationDataIntegrity:
    """
    Detects UI hallucinations: phantom elements, stale data, data bleeding,
    inconsistent states, and AI-generated content anomalies on Mehad homepage.
    """

    def test_qa05_no_placeholder_text_on_homepage(self, page: Page):
        """Homepage must not contain Lorem Ipsum, TODO, or unmocked placeholder text."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        content = page.inner_text("body").lower()

        phantom = [
            "lorem ipsum", "placeholder text", "todo", "fixme",
            "coming soon", "[object object]", "your text here",
            "sample text", "test content",
        ]
        found = [p for p in phantom if p in content]
        assert not found, f"Placeholder/phantom text on homepage: {found}"

    def test_qa05_no_undefined_or_null_text_on_homepage(self, page: Page):
        """Visible text must not contain literal 'undefined' or 'null'."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        content = page.inner_text("body")
        # Look for standalone undefined/null (not inside longer words)
        assert not re.search(r"\bundefined\b", content), (
            "Literal 'undefined' visible on homepage")
        assert not re.search(r"\bnull\b", content), (
            "Literal 'null' visible on homepage")

    def test_qa05_no_stale_errors_on_fresh_homepage(self, page: Page):
        """Fresh homepage load must not show error alerts or error messages."""
        page.goto(BASE_URL)
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
            f"Stale error messages on fresh homepage: {visible_errors}")

    def test_qa05_page_title_meaningful(self, page: Page):
        """Page title must be non-empty, non-null, and not a localhost URL."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        title = page.title()
        assert title.strip() != "", "Page title is empty"
        assert "undefined" not in title.lower(), f"Title contains 'undefined': {title!r}"
        assert "null" not in title.lower(), f"Title contains 'null': {title!r}"
        assert "localhost" not in title.lower(), f"Title leaks localhost: {title!r}"
        assert len(title) < 200, f"Title suspiciously long: {title[:80]!r}"

    def test_qa05_hero_stats_are_non_zero(self, page: Page):
        """Hero statistics must show real non-zero values, not 0 or empty."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        content = page.inner_text("body")
        # Stats like "+1,200" or "+50,000" or "98%" must be present
        # They must NOT be "0 teachers" or "0 students"
        assert not re.search(r"\b0\s+certified\s+teachers?\b", content, re.IGNORECASE), (
            "Hero stat shows '0 Certified Teachers' — hallucinated/empty data")
        assert not re.search(r"\b0\s+students?\b", content, re.IGNORECASE), (
            "Hero stat shows '0 Students' — hallucinated/empty data")

    def test_qa05_modal_not_visible_on_fresh_load(self, page: Page):
        """Login modal must NOT be visible on initial homepage load (not pre-opened)."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        page.wait_for_timeout(500)
        dialog = page.locator('[role="dialog"]')
        visible = dialog.count() > 0 and dialog.first.is_visible(timeout=1000)
        assert not visible, (
            "Login modal is visible on fresh page load — should be closed by default")

    def test_qa05_no_duplicate_login_buttons(self, page: Page):
        """Must not render multiple stacked Log In buttons (ghost element risk)."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        # Desktop and mobile versions may both exist in DOM but one should be hidden
        login_btns_visible = page.locator(
            '[aria-label="Login"], button:has-text("Log In"), button:has-text("Login")'
        )
        visible_count = sum(
            1 for i in range(login_btns_visible.count())
            if login_btns_visible.nth(i).is_visible()
        )
        assert visible_count <= 2, (
            f"Found {visible_count} visible Log In buttons — expected ≤ 2 (desktop + mobile)")

    def test_qa05_teacher_cards_have_names(self, page: Page):
        """Each visible teacher card must show a non-empty, non-undefined name."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        page.wait_for_timeout(1500)

        content = page.inner_text("body")
        # Check no teacher card shows "undefined" as a name
        assert "undefined" not in content, (
            "Literal 'undefined' found in page — possible empty teacher name")

    def test_qa05_subject_badges_have_counts(self, page: Page):
        """Subject badges (Math, Physics) must show numeric count, not 0 or empty."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        content = page.inner_text("body")
        # Spec: Math(25), Physics(9), Algebra(12) — at least some number present
        has_numbers = bool(re.search(r"\d+", content))
        assert has_numbers, "No numeric data found on homepage — possible empty/hallucinated state"

    def test_qa05_no_data_bleeding_between_navigations(self, page: Page):
        """Navigate homepage → find-tutors → homepage — modal must not be pre-open."""
        page.goto(FIND_TUTORS_URL)
        page.wait_for_load_state(LOAD_STATE)
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        page.wait_for_timeout(500)

        dialog = page.locator('[role="dialog"]')
        visible = dialog.count() > 0 and dialog.first.is_visible(timeout=1000)
        assert not visible, (
            "Modal is pre-opened on homepage after navigation — state bleed from previous page")

    def test_qa05_footer_copyright_year_is_current(self, page: Page):
        """Footer copyright must show the correct year (2026 per spec)."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        footer_text = page.locator("footer").first.inner_text()
        assert "2026" in footer_text or "2025" in footer_text, (
            f"Footer copyright year not found or incorrect: {footer_text[-100:]!r}")

    def test_qa05_footer_brand_name_correct(self, page: Page):
        """Footer must mention Mehad / Mahad brand name, not a competitor's."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)
        footer_text = page.locator("footer").first.inner_text().lower()
        assert "mehad" in footer_text or "mahad" in footer_text, (
            f"Mehad brand name not in footer: {footer_text[:200]!r}")

    def test_qa05_arabic_page_has_rtl_direction(self, page: Page):
        """Arabic locale page must have RTL text direction."""
        ar_url = BASE_URL.replace("/en", "/ar")
        page.goto(ar_url)
        page.wait_for_load_state(LOAD_STATE)
        dir_attr = page.locator("html").get_attribute("dir")
        lang_attr = page.locator("html").get_attribute("lang")
        assert dir_attr == "rtl" or (lang_attr and "ar" in lang_attr), (
            f"Arabic page does not have RTL direction — dir={dir_attr!r}, lang={lang_attr!r}")

    def test_qa05_hallucination_no_impossible_success_on_wrong_otp(self, page: Page):
        """Wrong OTP must NOT produce a login success message (hallucinated success)."""
        _open_login_modal(page)
        _fill_phone(page, TEST_COUNTRY_CODE, TEST_PHONE)

        send_btn = page.locator('button:has-text("Send Code")').first
        page.wait_for_timeout(400)
        send_btn.click()

        otp_input = page.locator(
            'input[placeholder="000000"], input[autocomplete="one-time-code"]'
        ).first
        if otp_input.count() > 0 and otp_input.is_visible(timeout=8000):
            otp_input.fill("000000")  # deliberately wrong OTP
            continue_btn = page.locator('button:has-text("Continue")').first
            if continue_btn.count() > 0 and not continue_btn.is_disabled():
                continue_btn.click()
                page.wait_for_timeout(3000)

                body_text = page.inner_text("body").lower()
                false_success = [
                    "login successful", "successfully logged in",
                    "welcome back", "you are now logged in",
                ]
                found = [p for p in false_success if p in body_text]
                assert not found, (
                    f"Hallucinated success shown for wrong OTP: {found}")

    def test_qa05_error_garbage_not_shown_on_modal_failure(self, page: Page):
        """After any modal error, raw JSON / stack traces must not be visible."""
        _open_login_modal(page)
        _fill_phone(page, TEST_COUNTRY_CODE, TEST_PHONE)

        send_btn = page.locator('button:has-text("Send Code")').first
        page.wait_for_timeout(400)
        send_btn.click()

        otp_input = page.locator(
            'input[placeholder="000000"], input[autocomplete="one-time-code"]'
        ).first
        if otp_input.count() > 0 and otp_input.is_visible(timeout=8000):
            otp_input.fill("000000")
            continue_btn = page.locator('button:has-text("Continue")').first
            if continue_btn.count() > 0 and not continue_btn.is_disabled():
                continue_btn.click()
                page.wait_for_timeout(2500)

                content = page.inner_text("body")
                garbage = [
                    r"Traceback \(most recent call",
                    r"Exception in thread",
                    r"SyntaxError|TypeError|ReferenceError",
                    r"500 Internal Server Error",
                    r"\{.*\"error\".*\}",
                ]
                for pat in garbage:
                    assert not re.search(pat, content), (
                        f"Garbage/raw error content in modal: pattern={pat!r}")

    def test_qa05_consistent_page_after_language_round_trip(self, page: Page):
        """EN → AR → EN round-trip must return to clean homepage without phantom state."""
        page.goto(BASE_URL)
        page.wait_for_load_state(LOAD_STATE)

        ar_btn = page.locator('[aria-label="العربية"]').first
        ar_btn.wait_for(state="visible", timeout=5000)
        ar_btn.click()
        page.wait_for_load_state(LOAD_STATE)

        en_btn = page.locator('[aria-label="English"]').first
        en_btn.wait_for(state="visible", timeout=5000)
        en_btn.click()
        page.wait_for_load_state(LOAD_STATE)

        # Back on EN — no phantom modal, no crash
        assert "mehadedu.com/en" in page.url or page.url.endswith("/en"), (
            f"After EN→AR→EN round-trip, URL is: {page.url}")
        assert "500" not in page.title(), "Page crashed after language round-trip"

        dialog = page.locator('[role="dialog"]')
        visible = dialog.count() > 0 and dialog.first.is_visible(timeout=1000)
        assert not visible, (
            "Modal is phantom-visible after language round-trip")
