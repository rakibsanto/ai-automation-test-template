from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("https://dev.prowhats.com/en/login", wait_until="networkidle")
    print(page.locator("body").inner_html())
    browser.close()
