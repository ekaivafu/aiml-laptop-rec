from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("https://www.smartprix.com/laptops?page=1", wait_until="domcontentloaded")
    try:
        page.wait_for_timeout(5000) # Wait 5s for page to load
        hrefs = page.eval_on_selector_all("a", "elements => elements.map(e => e.getAttribute('href'))")
        for h in hrefs:
            if h and len(h) > 10:
                print(h)
    except Exception as e:
        print(f"Error: {e}")
    browser.close()
