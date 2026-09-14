"""Browser checks exercise real calculations and save private CI screenshots."""
from pathlib import Path
import json
from pypdf import PdfReader
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
    page.emulate_media(reduced_motion="reduce")
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
    # A locale change must preserve the calculated result, not just the inputs.
    score_before = page.locator(".score-value").all_text_contents()
    page.locator(".language-menu summary").click()
    page.locator('.locale-link[lang="ta"]').click()
    page.wait_for_url("**/ta/")
    assert page.locator("#reading").is_visible()
    assert page.locator(".score-value").all_text_contents() == score_before
    page.locator("#toggle-details").click()
    assert page.locator("#report-content details:not([open])").count() == 0
    page.locator("#toggle-details").click()
    assert page.locator("#report-content details[open]").count() == 0
    with page.expect_download() as download:
        page.locator("#download-json").click()
    json_path = ARTIFACTS / "download-match.json"
    download.value.save_as(str(json_path))
    exported = json.loads(json_path.read_text())
    assert exported["inputs"]["groom"]["name"] == "Test A"
    assert exported["locale"] == "ta" and exported["schemaVersion"] == 1
    with page.expect_download(timeout=60000) as download:
        page.locator("#download-pdf").click()
    assert download.value.suggested_filename == "astro-match.pdf"
    pdf_path = ARTIFACTS / "download-match-ta.pdf"
    download.value.save_as(str(pdf_path))
    assert len(PdfReader(pdf_path).pages) >= 4
    # A failed export leaves the valid report visible and can be retried.
    page.route("**/reports/*.pdf?*", lambda route: route.fulfill(status=503, body="unavailable"))
    page.locator("#download-pdf").click()
    page.locator("#export-error").wait_for(state="visible")
    assert page.locator("#reading").is_visible()
    assert page.locator("#download-pdf").is_enabled()
    page.unroute("**/reports/*.pdf?*")
    page.locator(".language-menu summary").click()
    page.locator('.locale-link[lang="hi"]').click()
    page.wait_for_url("**/hi/")
    assert page.locator("#reading").is_visible()
    page.locator("#reading").screenshot(path=str(ARTIFACTS / "report-tools.png"))
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
    with page.expect_download(timeout=60000) as download:
        page.locator("#download-pdf").click()
    assert download.value.suggested_filename == "astro-chart.pdf"
    download.value.save_as(str(ARTIFACTS / "download-chart-en.pdf"))
    page.locator("#groom-name").fill("Changed input")
    assert page.locator("#reading").is_hidden()
    page.locator(".language-menu summary").click()
    page.locator('.locale-link[lang="hi"]').click()
    page.wait_for_url("**/hi/birth-chart/")
    assert page.locator("#reading").is_hidden()
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
print("Browser flows passed: real reports, PDF/JSON downloads, export recovery, report-preserving locale handoff, expand/collapse, unknown time, mobile overflow, RTL, keyboard places.")
