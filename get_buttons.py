import os
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    base_url = os.getenv("BASE_URL", "https://example.com")
    page.goto(base_url, wait_until="networkidle")
    
    # Get all buttons and links
    elements = page.query_selector_all('button, a')
    for el in elements:
        text = el.inner_text().strip()
        if text:
            print(f"[{el.evaluate('el => el.tagName')}] {text} (aria-label: {el.get_attribute('aria-label')})")
    
    browser.close()
