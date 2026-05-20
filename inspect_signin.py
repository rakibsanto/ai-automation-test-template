import os
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    base_url = os.getenv("BASE_URL", "https://example.com")
    page.goto(base_url, wait_until="networkidle")
    
    btns = page.locator('button:has-text("Sign in")')
    print(f"Found {btns.count()} buttons")
    for i in range(btns.count()):
        btn = btns.nth(i)
        print(f"[{i}] visible: {btn.is_visible()}, disabled: {btn.is_disabled()}, html: {btn.evaluate('el => el.outerHTML')}")
        
    browser.close()
