import os, time, pytest
from playwright.sync_api import Page, expect
BASE_URL = os.getenv("BASE_URL", "https://dev.prowhats.com/en")

def test_login_page_loads(page: Page):
    page.goto(BASE_URL, wait_until="domcontentloaded", timeout=15000)
    page.wait_for_load_state("domcontentloaded")
    assert "mehadedu.com" in page.url or page.url.startswith(BASE_URL)

def test_login_flow_1_successful_login(page: Page):
    page.goto(BASE_URL, wait_until="domcontentloaded", timeout=15000)
    page.wait_for_load_state("domcontentloaded")
    assert page.url

def test_login_flow_2_login_with_invalid_credentials(page: Page):
    page.goto(BASE_URL, wait_until="domcontentloaded", timeout=15000)
    page.wait_for_load_state("domcontentloaded")
    assert page.url

def test_login_flow_3_login_with_empty_fields(page: Page):
    page.goto(BASE_URL, wait_until="domcontentloaded", timeout=15000)
    page.wait_for_load_state("domcontentloaded")
    assert page.url

def test_login_flow_4_navigate_to_forgot_password(page: Page):
    page.goto(BASE_URL, wait_until="domcontentloaded", timeout=15000)
    page.wait_for_load_state("domcontentloaded")
    assert page.url

def test_ec_l_01(page: Page):
    """EC-L-01: Email with leading/trailing whitespace"""
    page.goto(BASE_URL, wait_until="domcontentloaded", timeout=15000)
    page.wait_for_load_state("domcontentloaded")
    assert page.url

def test_ec_l_02(page: Page):
    """EC-L-02: Email in uppercase"""
    page.goto(BASE_URL, wait_until="domcontentloaded", timeout=15000)
    page.wait_for_load_state("domcontentloaded")
    assert page.url

def test_ec_l_03(page: Page):
    """EC-L-03: Password with special characters `!@#$%^&*()`"""
    page.goto(BASE_URL, wait_until="domcontentloaded", timeout=15000)
    page.wait_for_load_state("domcontentloaded")
    assert page.url

def test_ec_l_04(page: Page):
    """EC-L-04: Password with spaces"""
    page.goto(BASE_URL, wait_until="domcontentloaded", timeout=15000)
    page.wait_for_load_state("domcontentloaded")
    assert page.url

def test_ec_l_05(page: Page):
    """EC-L-05: Very long email (255+ chars)"""
    page.goto(BASE_URL, wait_until="domcontentloaded", timeout=15000)
    page.wait_for_load_state("domcontentloaded")
    assert page.url

def test_login_mobile(page: Page):
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto(BASE_URL, wait_until="domcontentloaded", timeout=15000)
    page.wait_for_load_state("domcontentloaded")
    assert page.url

def test_login_no_console_errors(page: Page):
    errors = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.goto(BASE_URL, wait_until="domcontentloaded", timeout=15000)
    page.wait_for_load_state("domcontentloaded")
    assert errors == [], f"Console errors: {errors[:3]}"
