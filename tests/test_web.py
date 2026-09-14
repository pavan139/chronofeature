import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from xml.etree import ElementTree

import pytest
from fastapi.testclient import TestClient
from gunamilan.api import app
from gunamilan.web import catalogs
from gunamilan import geocode as lookup
from gunamilan.ephemeris import BirthData, cast_chart
import datetime as dt

client = TestClient(app)
BIRTH = {"name": "Test", "date": "1992-03-14", "time": "07:25",
         "latitude": 17.385, "longitude": 78.4867, "timezone": "Asia/Kolkata"}
MATCH = {"groom": BIRTH, "bride": {**BIRTH, "name": "Other", "date": "1994-11-02"},
         "system": "both", "ayanamsa": "lahiri"}

def test_every_language_has_complete_keys():
    data = catalogs()
    assert len(data) == 23
    for code, messages in data.items():
        assert set(messages) == set(data["en"])
        assert messages["code"] == code
        assert all(isinstance(value, (str, bool)) and value != "" for value in messages.values())

@pytest.mark.parametrize("code", list(catalogs()))
@pytest.mark.parametrize("route", ["", "porutham/", "birth-chart/"])
def test_localized_routes_render_before_javascript(code, route):
    response = client.get("/" + code + "/" + route)
    assert response.status_code == 200
    assert '<html lang="' + code + '"' in response.text
    assert catalogs()[code]["calculate"] in response.text
    assert response.headers["content-language"] == code
    assert "noindex" in response.headers["x-robots-tag"]

def test_invalid_locale_and_route_return_real_404():
    assert client.get("/zz/").status_code == 404
    assert client.get("/en/not-a-page/").status_code == 404

@pytest.mark.parametrize("route,steps", [("", 3), ("porutham/", 3), ("birth-chart/", 2)])
def test_guided_controls_are_server_rendered(route, steps):
    html = client.get("/en/" + route).text
    assert html.count('data-flow-step="') == steps
    assert 'id="review-step"' in html and 'id="review-people"' in html
    assert 'id="try-example"' in html and 'id="undo-reset"' in html
    assert 'aria-current="step"' in html
    assert '/static/flow.css' in html
    assert 'id="download-pdf"' in html and 'class="export-menu"' in html

def test_guided_styles_keep_zoom_and_respect_motion_preferences():
    css = client.get("/static/flow.css")
    assert css.status_code == 200
    assert "prefers-reduced-motion: no-preference" in css.text
    assert "font-variant-numeric: tabular-nums" in css.text
    assert "transition: all" not in css.text
    assert "maximum-scale" not in client.get("/en/").text

def test_report_uses_engine_and_does_not_cache():
    r = client.post("/match/full", json=MATCH)
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data["ashtakoota"]["kootas"]) == 8
    assert len(data["porutham"]["poruthams"]) == 10
    assert data["ashtakoota"]["total"] == sum(k["score"] for k in data["ashtakoota"]["kootas"])
    assert "no-store" in r.headers["cache-control"]
    assert "noindex" in r.headers["x-robots-tag"]
    assert "set-cookie" not in r.headers

def test_unknown_time_is_explicit():
    r = client.post("/chart", json={**BIRTH, "time": None})
    assert r.status_code == 200
    assert r.json()["ascendant"] is None
    assert r.json()["accuracy_warning"]

def test_invalid_timezone_is_validation_error_not_server_error():
    r = client.post("/chart", json={**BIRTH, "timezone": "Not/A_Timezone"})
    assert r.status_code == 422

def test_offset_birth_time_is_rejected():
    assert client.post("/chart", json={**BIRTH, "time": "12:00:00+05:30"}).status_code == 422

def test_missing_place_database_has_recoverable_response(monkeypatch, tmp_path):
    import importlib
    geocoder = importlib.import_module("gunamilan.geocode")
    geocoder._connection.cache_clear()
    monkeypatch.setattr(geocoder, "DB_PATH", tmp_path / "missing.db")
    try:
        assert client.get("/places?q=Delhi").status_code == 503
        assert client.post("/chart", json=BIRTH).status_code == 200
    finally:
        geocoder._connection.cache_clear()

def test_indic_vowel_marks_survive_normalization():
    from build_places import fold, spellings
    from importlib import import_module
    f = import_module("gunamilan.geocode").fold
    assert fold("Sitapur") == f("Sītāpur")
    for name in ["हैदराबाद", "திருச்சிராப்பள்ளி", "విశాఖపట్నం", "കൊച്ചി"]:
        assert fold(name) == name
        assert f(name) == name
    row = [""] * 19
    row[1], row[2], row[3] = "Chennai", "Chennai", "சென்னை,चेन्नई"
    assert "சென்னை" in spellings(row, True)
    assert "चेन्नई" in spellings(row, True)

def test_canonical_and_sitemap_use_configured_origin(monkeypatch):
    monkeypatch.setenv("SITE_URL", "https://astro.example.org")
    monkeypatch.setenv("INDEXABLE", "true")
    monkeypatch.setenv("INDEX_LOCALES", "en,hi,ta")
    r = client.get("/hi/")
    assert 'rel="canonical" href="https://astro.example.org/hi/"' in r.text
    assert 'hreflang="ta"' in r.text
    assert 'hreflang="x-default"' in r.text
    assert r.headers["x-robots-tag"] == "index, follow"
    tree = ElementTree.fromstring(client.get("/sitemap.xml").text)
    assert len(list(tree)) == 9
    assert "https://astro.example.org/sitemap.xml" in client.get("/robots.txt").text
    assert client.get("/ur/").headers["x-robots-tag"].startswith("noindex")

def test_parallel_ayanamsas_match_serial_results():
    birth = BirthData("Parallel", dt.date(1992, 3, 14), dt.time(7, 25), 17.385, 78.4867)
    modes = ["lahiri", "raman", "krishnamurti", "fagan_bradley"] * 5
    expected = {m: cast_chart(birth, m).moon.longitude for m in set(modes)}
    with ThreadPoolExecutor(max_workers=4) as pool:
        actual = list(pool.map(lambda m: cast_chart(birth, m).moon.longitude, modes))
    assert actual == [expected[m] for m in modes]

def test_user_input_is_not_reflected_in_public_document():
    response = client.get("/en/?name=%3Cscript%3Ealert(1)%3C/script%3E")
    assert "alert(1)" not in response.text

def test_manifest_and_structured_metadata_are_machine_readable(monkeypatch):
    manifest = client.get("/manifest.webmanifest")
    assert manifest.status_code == 200
    assert manifest.headers["content-type"].startswith("application/manifest+json")
    assert manifest.json()["start_url"] == "/en/"
    monkeypatch.setenv("SITE_URL", "https://astro.example.org")
    monkeypatch.setenv("INDEXABLE", "true")
    page = client.get("/en/birth-chart/")
    assert 'rel="manifest" href="/manifest.webmanifest"' in page.text
    assert 'name="twitter:description"' in page.text
    start = page.text.index('<script type="application/ld+json"')
    payload = page.text[page.text.index(">", start) + 1:page.text.index("</script>", start)]
    graph = json.loads(payload)["@graph"]
    assert {item["@type"] for item in graph} == {"WebSite", "WebApplication", "WebPage"}
    assert graph[1]["name"] == "Birth chart"
    assert graph[2]["mainEntity"]["@id"].endswith("#app")
