from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("https://dev.prowhats.com/en/login")
    print(page.locator("button[type='submit']").inner_text())
    print(page.locator("button").all_inner_texts())
    browser.close()
