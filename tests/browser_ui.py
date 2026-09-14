"""Browser checks exercise real calculations and save private CI screenshots."""
from pathlib import Path
from playwright.sync_api import sync_playwright

ARTIFACTS = Path("test-results")
ARTIFACTS.mkdir(exist_ok=True)
with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 1100})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto("http://127.0.0.1:8000/en/")
    page.screenshot(path=str(ARTIFACTS / "desktop.png"), full_page=True)
    page.locator("#theme-toggle").click()
    assert page.evaluate("document.documentElement.dataset.theme") == "dark"
    page.screenshot(path=str(ARTIFACTS / "desktop-dark.png"), full_page=True)
    page.locator("#theme-toggle").click()
    for person, name, day in [("groom", "Test A", "1992-03-14"), ("bride", "Test B", "1994-11-02")]:
        page.locator("#" + person + "-name").fill(name)
        page.locator("#" + person + "-date").fill(day)
        page.locator("#" + person + "-time").fill("07:25")
        page.locator('[data-person="' + person + '"] .coordinates').evaluate("(e) => e.open = true")
        page.locator("#" + person + "-lat").fill("17.385")
        page.locator("#" + person + "-lon").fill("78.4867")
    page.locator(".language-menu summary").click()
    page.locator('.locale-link[lang="hi"]').click()
    page.wait_for_url("**/hi/")
    assert page.locator("#groom-name").input_value() == "Test A"
    assert page.locator("#bride-date").input_value() == "1994-11-02"
    page.locator('#birth-form button[type="submit"]').click()
    page.locator("#reading").wait_for(state="visible")
    assert page.locator(".score-card").count() == 2
    assert page.locator("#reading table").count() == 2
    assert not page.locator("#form-error").is_visible()
    page.evaluate("navigator.share = data => { window.__shared = data; return Promise.resolve(); }")
    page.locator("#share-result").click()
    shared = page.evaluate("window.__shared")
    assert "Test A" not in shared["text"] and "Test B" not in shared["text"]
    assert "?" not in shared["url"]
    page.screenshot(path=str(ARTIFACTS / "report-hindi.png"), full_page=True)
    assert page.evaluate("localStorage.length") == 0
    assert page.evaluate("sessionStorage.length") == 0
    assert not page.context.cookies()
    page.goto("http://127.0.0.1:8000/en/birth-chart/")
    page.locator("#groom-name").fill("Unknown time")
    page.locator("#groom-date").fill("1990-06-01")
    page.locator('input[name="groom-unknown"]').check()
    page.locator(".coordinates").evaluate("(e) => e.open = true")
    page.locator("#groom-lat").fill("17.385")
    page.locator("#groom-lon").fill("78.4867")
    page.locator('#birth-form button[type="submit"]').click()
    page.locator("#reading").wait_for(state="visible")
    assert page.locator("#reading .notice").count() == 1
    for locale in ["en", "hi", "ta", "te", "ur", "sat", "mni"]:
        page.set_viewport_size({"width": 390, "height": 844})
        page.goto("http://127.0.0.1:8000/" + locale + "/")
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), locale
        assert page.locator("h1").is_visible()
        if locale in ["ta", "ur"]:
            page.screenshot(path=str(ARTIFACTS / ("mobile-" + locale + ".png")), full_page=True)
    page.set_viewport_size({"width": 1440, "height": 1100})
    page.goto("http://127.0.0.1:8000/en/")
    page.locator("#groom-place").fill("Hyder")
    page.locator("#groom-places [role=option]").first.wait_for()
    page.locator("#groom-place").press("ArrowDown")
    page.locator("#groom-place").press("Enter")
    assert page.locator("#groom-lat").input_value()
    assert page.locator("#groom-places").is_hidden()
    # Search failure must leave manual coordinates usable.
    page.route("**/places?*", lambda route: route.fulfill(status=503,body='{"detail":"unavailable"}',content_type="application/json"))
    page.locator("#bride-place").fill("missing")
    page.locator("#bride-lat").wait_for(state="visible")
    assert page.locator("#bride-lat").is_visible()
    assert not errors, errors
    browser.close()
print("Browser flows passed: real reports, unknown time, locale handoff, mobile overflow, RTL, keyboard places, recoverable search failure.")
