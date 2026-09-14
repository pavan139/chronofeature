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
    calculations = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("request", lambda request: calculations.append(request.url) if request.method == "POST" and "/match/full" in request.url else None)
    page.goto("http://127.0.0.1:8000/en/")
    page.screenshot(path=str(ARTIFACTS / "desktop.png"), full_page=True)
    page.locator("#theme-toggle").click()
    # Contextual help is keyboard reachable, local and preserves the input.
    help_button = page.locator('[data-person="groom"] [data-help="birth-time"]')
    help_button.click()
    assert page.locator("#help-dialog").is_visible()
    assert page.locator("#help-search").evaluate("e => e === document.activeElement")
    page.locator("#help-search").fill("Nadi")
    assert "Nadi" in page.locator("#help-topic h3").inner_text()
    page.screenshot(path=str(ARTIFACTS / "studio-help.png"))
    page.locator("#help-search").fill("unfindablezzzzz")
    assert "No matching term" in page.locator("#help-topic").inner_text()
    page.keyboard.press("Escape")
    assert not page.locator("#help-dialog").is_visible()
    assert help_button.evaluate("e => e === document.activeElement")
    page.emulate_media(reduced_motion="reduce")
    assert page.evaluate("document.documentElement.dataset.theme") == "dark"
    page.screenshot(path=str(ARTIFACTS / "desktop-dark.png"), full_page=True)
    page.locator("#theme-toggle").click()
    # Future steps cannot bypass validation, and the first invalid input gets focus.
    page.locator('[data-flow-step="2"]').click()
    assert page.locator("#groom-name").get_attribute("aria-invalid") == "true"
    assert page.locator("#groom-name").evaluate("e => e === document.activeElement")
    assert "groom-name-error" in page.locator("#groom-name").get_attribute("aria-describedby")
    page.screenshot(path=str(ARTIFACTS / "flow-error.png"))
    for person, name, day in [("groom", "Test A", "1992-03-14"), ("bride", "Test B", "1994-11-02")]:
        page.locator("#" + person + "-name").fill(name)
        page.locator("#" + person + "-date").fill(day)
        page.locator("#" + person + "-time").fill("07:25")
        if person == "groom":
            page.locator('[data-person="groom"] .coordinates').evaluate("(e) => e.open = true")
            page.locator("#groom-lat").fill("17.385")
            page.locator("#groom-lon").fill("78.4867")
        else:
            page.locator("#same-place").click()
            assert page.locator("#bride-lat").input_value() == "17.385"
            assert page.locator("#bride-tz").input_value() == "Asia/Kolkata"
        page.locator('#birth-form button[type="submit"]').click()
    assert not calculations, "Review must not silently calculate or submit birth details"
    assert page.locator("#review-step").is_visible()
    assert page.locator(".review-card").count() == 2
    page.locator(".review-card .text-button").first.click()
    page.locator("#groom-name").fill("Test A")
    page.locator('#birth-form button[type="submit"]').click()
    assert page.locator("#review-step").is_visible(), "Editing one person must return directly to review"
    page.screenshot(path=str(ARTIFACTS / "flow-review.png"))
    page.locator(".language-menu summary").click()
    page.locator('.locale-link[lang="hi"]').click()
    page.wait_for_url("**/hi/")
    assert page.locator("#groom-name").input_value() == "Test A"
    assert page.locator("#bride-date").input_value() == "1994-11-02"
    assert page.locator("#review-step").is_visible(), "Locale switching must preserve the current step"
    page.locator('#birth-form button[type="submit"]').click()
    page.locator("#reading").wait_for(state="visible")
    assert page.locator(".score-card").count() == 2
    assert page.locator("#reading table").count() == 2
    assert not page.locator("#form-error").is_visible()
    assert page.locator(".workspace").is_hidden()
    assert page.locator(".report-section[open]").count() == 0
    assert page.locator(".analysis-overview").is_visible()
    page.locator(".insight-link").first.click()
    assert page.locator(".report-section[open]").count() == 1
    assert page.locator(".factor[open] .definition").is_visible()
    section = page.locator(".report-section[open]")
    section.locator(".factor-filter input").check()
    assert section.locator('[data-factor-state="full"]:visible').count() == 0
    page.evaluate("window.onbeforeprint()")
    assert section.locator('[data-factor-state][hidden]').count() == 0
    page.evaluate("window.onafterprint()")
    section.locator(".factor-filter input").uncheck()
    page.locator(".report-section[open]>summary").click()
    page.set_viewport_size({"width": 1440, "height": 1100})
    page.screenshot(path=str(ARTIFACTS / "studio-report.png"), full_page=True)
    page.evaluate("navigator.share = data => { window.__shared = data; return Promise.resolve(); }")
    page.locator(".export-menu summary").click()
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
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "Tamil result toolbar overflow"
    page.set_viewport_size({"width": 1440, "height": 1100})
    page.locator("#toggle-details").click()
    assert page.locator("#report-content details:not([open])").count() == 0
    page.locator("#toggle-details").click()
    assert page.locator("#report-content details[open]").count() == 0
    page.locator(".export-menu summary").click()
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
    assert page.locator("#review-unknown").is_visible()
    page.locator('#birth-form button[type="submit"]').click()
    page.locator("#reading").wait_for(state="visible")
    assert page.locator("#reading .notice").count() == 1
    assert page.locator(".chart-highlights").inner_text().find("Not calculated") >= 0
    page.locator(".planet-buttons button", has_text="Mars").click()
    assert page.locator(".planet-buttons button[aria-pressed=true]").inner_text() == "Mars"
    assert "POSITION / Mars" in page.locator(".planet-detail").inner_text()
    assert page.locator(".chart-planet.selected").count() == 1
    page.screenshot(path=str(ARTIFACTS / "studio-chart.png"), full_page=True)
    with page.expect_download(timeout=60000) as download:
        page.locator("#download-pdf").click()
    assert download.value.suggested_filename == "astro-chart.pdf"
    download.value.save_as(str(ARTIFACTS / "download-chart-en.pdf"))
    page.locator("#edit").click()
    page.locator(".review-card button").click()
    page.locator("#groom-name").fill("Changed input")
    assert page.locator("#reading").is_hidden()
    page.locator(".language-menu summary").click()
    page.locator('.locale-link[lang="hi"]').click()
    page.wait_for_url("**/hi/birth-chart/")
    assert page.locator("#reading").is_hidden()
    # Clear is reversible briefly, and a new edit discards the undo snapshot.
    page.locator('button[type="reset"]').click()
    assert page.locator("#groom-name").input_value() == ""
    page.locator("#undo-reset").click()
    assert page.locator("#groom-name").input_value() == "Changed input"
    assert page.locator('input[name="groom-unknown"]').is_checked()
    page.locator('button[type="reset"]').click()
    page.locator("#groom-name").fill("New person")
    assert page.locator("#reset-status").is_hidden()
    # Every catalog must support the complete sample -> review -> result flow on mobile.
    for locale in sorted(path.stem for path in Path("gunamilan/locales").glob("*.json")):
        page.set_viewport_size({"width": 390, "height": 844})
        page.goto("http://127.0.0.1:8000/" + locale + "/")
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), locale
        assert page.locator("h1").is_visible()
        indicator = page.locator(".step-number").first.bounding_box()
        assert indicator["width"] >= 24 and indicator["height"] >= 24, locale + " progress target"
        assert page.locator("#flow-count").evaluate("e => getComputedStyle(e).direction") == "ltr"
        if locale in ["ta", "ur"]:
            page.screenshot(path=str(ARTIFACTS / ("mobile-" + locale + ".png")), full_page=True)
        page.locator("#try-example").click()
        assert page.locator("#sample-notice").is_visible()
        assert page.locator("#review-step").is_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), locale + " review"
        page.locator('#birth-form button[type="submit"]').click()
        page.locator("#reading").wait_for(state="visible")
        assert page.locator("#reading .notice").is_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), locale + " report"
        if locale == "en":
            page.screenshot(path=str(ARTIFACTS / "flow-mobile.png"))
        if locale == "ta":
            page.locator("#reading").screenshot(path=str(ARTIFACTS / "flow-result.png"))
    page.set_viewport_size({"width": 1440, "height": 1100})
    page.goto("http://127.0.0.1:8000/en/")
    page.locator("#groom-place").fill("Hyder")
    page.locator("#groom-places [role=option]").first.wait_for()
    page.locator("#groom-place").press("ArrowDown")
    page.locator("#groom-place").press("Enter")
    assert page.locator("#groom-lat").input_value()
    assert page.locator("#groom-places").is_hidden()
    page.locator("#groom-name").fill("Place search")
    page.locator("#groom-date").fill("1992-03-14")
    page.locator("#groom-time").fill("07:25")
    page.locator('[data-person="groom"] .coordinates summary').click()
    page.locator("#groom-tz").fill("Invalid/Timezone")
    page.locator('#birth-form button[type="submit"]').click()
    assert page.locator("#groom-tz").get_attribute("aria-invalid") == "true"
    page.locator("#groom-tz").fill("Asia/Kolkata")
    page.locator('#birth-form button[type="submit"]').click()
    # Search failure must leave manual coordinates usable.
    page.route("**/places?*", lambda route: route.fulfill(status=503,body='{"detail":"unavailable"}',content_type="application/json"))
    page.locator("#bride-place").fill("missing")
    page.locator("#bride-lat").wait_for(state="visible")
    assert page.locator("#bride-lat").is_visible()
    # Real public guides stay readable without JavaScript. Search is progressive enhancement.
    page.goto("http://127.0.0.1:8000/en/guide/")
    page.locator("#glossary-search").fill("Vimshottari")
    assert page.locator(".glossary-term:visible").count() == 1
    page.locator("#glossary-search").fill("missingzzzz")
    assert page.locator("#glossary-empty").is_visible()
    page.goto("http://127.0.0.1:8000/en/guide/#nadi")
    assert page.locator("#nadi").is_visible()
    page.set_viewport_size({"width":390,"height":844})
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.goto("http://127.0.0.1:8000/en/guide/understand-your-report/")
    assert page.locator(".guide-article h2").first.is_visible()
    page.screenshot(path=str(ARTIFACTS / "studio-guide-mobile.png"), full_page=True)
    no_js = browser.new_context(java_script_enabled=False)
    guide = no_js.new_page()
    guide.goto("http://127.0.0.1:8000/en/guide/")
    assert guide.locator(".glossary-term").count() == 37
    no_js.close()
    assert not errors, errors
    browser.close()
print("Browser flows passed: contextual help and Escape focus, explanation links, review filters and print restoration, graha explorer, SSR guides with/without JS, guided steps, review editing, 23-language mobile flows, real reports and PDF/JSON exports, recovery, RTL and keyboard places.")
