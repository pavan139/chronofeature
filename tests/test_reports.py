"""Real PDF bytes, script fonts, privacy boundaries and failure recovery."""
from io import BytesIO
from pathlib import Path

import pymupdf
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from gunamilan.api import app, BirthInput, chart_endpoint
from gunamilan import reports
from gunamilan.web import catalogs

client = TestClient(app)
BIRTH = {"name": "Sample Person", "date": "1992-03-14", "time": "07:25",
         "latitude": 17.385, "longitude": 78.4867, "timezone": "Asia/Kolkata"}
MATCH = {"groom": BIRTH, "bride": {**BIRTH, "name": "Sample Partner", "date": "1994-11-02"},
         "system": "both", "ayanamsa": "lahiri"}


@pytest.mark.parametrize("locale,name", [("en", "Sample Person"), ("hi", "नमूना व्यक्ति"),
    ("ta", "மாதிரி நபர்"), ("ur", "نمونہ فرد"), ("sat", "ᱱᱟᱢᱩᱱᱟ")])
def test_chart_pdf_download_with_script_fonts(locale, name):
    response = client.post("/reports/chart.pdf?locale=" + locale, json={**BIRTH, "name": name, "time": None})
    assert response.status_code == 200, response.text[:200] if response.status_code != 200 else ""
    assert response.content.startswith(b"%PDF-")
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.headers["content-disposition"] == 'attachment; filename="astro-chart.pdf"'
    assert "no-store" in response.headers["cache-control"]
    assert "noindex" in response.headers["x-robots-tag"]
    assert "set-cookie" not in response.headers
    reader = PdfReader(BytesIO(response.content))
    text = "\n".join(p.extract_text() for p in reader.pages)
    assert "Birth time unknown" in text and "Vimshottari" in text
    assert "Planet condition" in text and "Retrograde" in text
    assert 2 <= len(reader.pages) <= 15
    assert name not in str(reader.metadata)
    target = Path("test-results")
    target.mkdir(exist_ok=True)
    (target / ("sample-chart-" + locale + ".pdf")).write_bytes(response.content)
    document = pymupdf.open(stream=response.content, filetype="pdf")
    for page in document:
        for block in page.get_text("blocks"):
            assert block[0] >= 0 and block[1] >= 0
            assert block[2] <= page.rect.width + 1 and block[3] <= page.rect.height + 1
    document[0].get_pixmap(matrix=pymupdf.Matrix(1.25, 1.25)).save(target / ("pdf-" + locale + ".png"))
    document[-1].get_pixmap(matrix=pymupdf.Matrix(1, 1)).save(target / ("pdf-" + locale + "-last.png"))
    document.close()


def test_match_pdf_contains_full_factors_both_charts_and_exceptions():
    response = client.post("/reports/match.pdf?locale=en", json=MATCH)
    assert response.status_code == 200
    reader = PdfReader(BytesIO(response.content))
    text = "\n".join(p.extract_text() for p in reader.pages)
    for term in ["Ashtakoota", "Dasa Porutham", "Nadi", "Rajju", "Dosha review", "Sample Partner", "Planet condition"]:
        assert term in text
    for term in ["At a glance", "Where points differ", "What this means", "Your calculation", "Chart glossary", "Next steps"]:
        assert term in text
    assert "A traditional reading" not in text
    assert "shared_windows" not in text
    assert 4 <= len(reader.pages) <= 20
    target = Path("test-results")
    target.mkdir(exist_ok=True)
    (target / "sample-match-en.pdf").write_bytes(response.content)
    document = pymupdf.open(stream=response.content, filetype="pdf")
    for index in [0, 1, len(document)-1]:
        document[index].get_pixmap(matrix=pymupdf.Matrix(1.1, 1.1)).save(target / ("pdf-match-" + str(index) + ".png"))
    document.close()


def test_all_catalogs_render_pdf_labels_and_escape_markup():
    birth = {**BIRTH, "name": '<img src="file:///etc/passwd">'}
    result = chart_endpoint(BirthInput(**birth))
    for locale in catalogs():
        html = reports.report_html(result, [birth], "chart", locale, "lahiri")
        assert '<html lang="' + locale + '"' in html
        assert '<img src="file:' not in html
        assert "&lt;img" in html
        assert catalogs()[locale]["chart"] in html


@pytest.mark.parametrize("url", ["file:///etc/passwd", "http://127.0.0.1/", "https://example.org", "data:text/plain,no"])
def test_renderer_rejects_all_resource_fetching(url):
    with pytest.raises(ValueError, match="disabled"):
        reports.deny_resource(url)


def test_pdf_validation_and_concurrency_limit():
    assert client.post("/reports/chart.pdf?locale=xx", json=BIRTH).status_code == 422
    assert client.post("/reports/chart.pdf", json={**BIRTH, "timezone": "Not/A_Zone"}).status_code == 422
    assert client.post("/reports/chart.pdf", json={**BIRTH, "html": "<b>ignored</b>", "date": "1600-01-01"}).status_code == 422
    assert client.get("/reports/chart.pdf").status_code >= 400
    assert reports.PDF_SLOTS.acquire(blocking=False)
    assert reports.PDF_SLOTS.acquire(blocking=False)
    try:
        response = client.post("/reports/chart.pdf", json=BIRTH)
        assert response.status_code == 429
        assert response.headers["retry-after"] == "5"
    finally:
        reports.PDF_SLOTS.release()
        reports.PDF_SLOTS.release()


def test_renderer_slot_is_released_after_failure(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("test renderer failure")
    monkeypatch.setattr(reports, "report_html", fail)
    with pytest.raises(RuntimeError):
        reports.render_pdf({}, [], "chart", "en", "lahiri")
    assert reports.PDF_SLOTS.acquire(blocking=False)
    assert reports.PDF_SLOTS.acquire(blocking=False)
    reports.PDF_SLOTS.release()
    reports.PDF_SLOTS.release()
