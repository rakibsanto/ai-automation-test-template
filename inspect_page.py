import os
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    response = base_url = os.getenv("BASE_URL", "https://example.com")
    page.goto(base_url, wait_until="domcontentloaded")
    
    print(f"URL: {page.url}")
    print(f"Title: {page.title()}")
    print("Body text:")
    print(page.inner_text('body'))
    
    browser.close()
