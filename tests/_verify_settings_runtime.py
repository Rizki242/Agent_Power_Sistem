from playwright.sync_api import sync_playwright


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1050})
    errors = []
    page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
    page.goto("http://localhost:5173/settings")
    page.wait_for_load_state("networkidle")
    assert page.get_by_role("heading", name="Settings & System Control").is_visible()
    assert page.get_by_role("heading", name="Sistem siap digunakan").is_visible()
    assert page.get_by_role("heading", name="Lapisan AI").is_visible()
    assert page.get_by_text("Engineering core dikunci").is_visible()
    assert page.get_by_role("button", name="Jalankan health check").is_visible()
    assert not errors, errors
    page.screenshot(path=".tmp-test-runtime/settings-workspace.png", full_page=True)
    browser.close()
