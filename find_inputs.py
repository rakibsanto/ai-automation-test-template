import os
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    base_url = os.getenv("BASE_URL", "https://example.com")
    page.goto(base_url, wait_until="networkidle")
    
    inputs = page.locator('input')
    print(f"Found {inputs.count()} inputs")
    for i in range(inputs.count()):
        el = inputs.nth(i)
        print(f"[{i}] type: {el.get_attribute('type')}, placeholder: {el.get_attribute('placeholder')}")
        
    browser.close()
