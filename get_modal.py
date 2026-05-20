import os
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    base_url = os.getenv("BASE_URL", "https://example.com")
    page.goto(base_url, wait_until="networkidle")
    
    # Click sign in
    btn = page.locator('button:has-text("Sign in")').first
    btn.click()
    
    # Wait for modal
    modal = page.locator('[role="dialog"], [aria-modal="true"], [class*="modal-content"]').first
    modal.wait_for(state="visible", timeout=10000)
    
    print("Modal is visible")
    inputs = page.locator('input')
    for i in range(inputs.count()):
        el = inputs.nth(i)
        print(f"Input: type={el.get_attribute('type')} placeholder={el.get_attribute('placeholder')}")
        
    browser.close()
