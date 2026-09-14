"""Prove displayed explanations follow actual data, and public guides leak no inputs."""
from copy import deepcopy
from io import BytesIO
import json
import re

from fastapi.testclient import TestClient
from PIL import Image
import pytest

from gunamilan.api import app
from gunamilan.insights import analyze_match, analyze_chart
from gunamilan.knowledge import TERMS, ARTICLES, term_key

client = TestClient(app)
BIRTH = {"name": "Example", "date": "1992-03-14", "time": "07:25", "latitude": 17.385,
         "longitude": 78.4867, "timezone": "Asia/Kolkata"}


@pytest.fixture(scope="module")
def result():
    response = client.post("/match/full", json={"groom": BIRTH, "bride": {**BIRTH, "date": "1994-11-02"}, "system": "both"})
    assert response.status_code == 200
    return response.json()


def test_analysis_is_complete_sorted_and_never_changes_raw_scores(result):
    original = deepcopy(result)
    analysis = analyze_match(result)
    assert result == original
    assert analysis["language"] == "en"
    rows = analysis["full_points"] + analysis["review_factors"]
    assert len(rows) == 8
    assert sum(row["score"] for row in rows) == result["ashtakoota"]["total"]
    assert all(row["gap"] == 0 for row in analysis["full_points"])
    assert all(row["gap"] > 0 for row in analysis["review_factors"])
    assert [r["gap"] for r in analysis["review_factors"]] == sorted([r["gap"] for r in analysis["review_factors"]], reverse=True)
    assert "probabilities" in analysis["context"]


def test_unknown_time_and_supplied_time_have_distinct_uncertainty(result):
    assert "not been independently verified" in result["analysis"]["accuracy"]
    changed = deepcopy(result)
    changed["accuracy_warning"] = "Unknown"
    assert analyze_match(changed)["accuracy"].startswith("Approximate")


def test_high_total_does_not_remove_essential_flags_or_rewrite_exceptions(result):
    changed = deepcopy(result)
    changed["ashtakoota"]["total"] = 35
    changed["ashtakoota"]["blocking_doshas"] = ["Nadi"]
    changed["ashtakoota"]["exceptions"] = {"bhakoot": ["Sample exception; arithmetic unchanged."]}
    changed["porutham"]["essential_failures"] = ["Rajju"]
    analysis = analyze_match(changed)
    assert analysis["essential_flags"] == ["Ashtakoota: Nadi", "Porutham: Rajju"]
    assert analysis["exceptions"] == [{"name": "Bhakoot", "text": "Sample exception; arithmetic unchanged."}]


@pytest.mark.parametrize("system", ["ashtakoota", "porutham"])
def test_analysis_handles_single_system_without_inventing_other_result(result, system):
    data = {system: result[system]}
    analysis = analyze_match(data)
    assert ("Ashtakoota points" in analysis["summary"]) == (system == "ashtakoota")
    assert ("Porutham checks" in analysis["summary"]) == (system == "porutham")
    if system == "porutham":
        assert analysis["full_points"] == [] and analysis["review_factors"] == []


def test_every_actual_factor_has_a_definition_and_next_step(result):
    factors = result["ashtakoota"]["kootas"] + result["porutham"]["poruthams"]
    for factor in factors:
        assert term_key(factor["name"]) in TERMS
        definition = TERMS[term_key(factor["name"])]
        assert len(definition["meaning"]) > 80 and len(definition["next_step"]) > 20


def test_chart_highlights_are_positions_not_fabricated_traits(result):
    for chart in result["full_charts"].values():
        overview = analyze_chart(chart)
        by_name = {g["name"]: g for g in chart["grahas"]}
        assert overview["highlights"][0]["value"] == by_name["Moon"]["rashi"]
        assert overview["highlights"][1]["value"] == by_name["Sun"]["rashi"]
        assert overview["highlights"][2]["value"] == chart["ascendant"]["rashi"]
    unknown = client.post("/chart", json={**BIRTH, "time": None}).json()
    assert unknown["analysis"]["highlights"][2]["value"] == "Not calculated"
    assert "noon" in unknown["analysis"]["accuracy"]


@pytest.mark.parametrize("slug", [None, *ARTICLES])
def test_guides_are_server_rendered_and_have_truthful_schema(slug, monkeypatch):
    monkeypatch.setenv("SITE_URL", "https://astro.example.org")
    monkeypatch.setenv("INDEXABLE", "true")
    path = "/en/guide/" + (slug + "/" if slug else "")
    response = client.get(path + "?name=SecretPerson")
    assert response.status_code == 200
    assert "SecretPerson" not in response.text
    assert '<link rel="canonical" href="https://astro.example.org' + path + '"' in response.text
    assert "hreflang" not in response.text
    assert response.headers["content-language"] == "en"
    raw = re.search(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', response.text, re.S).group(1)
    graph = json.loads(raw)["@graph"]
    assert graph[1]["@type"] == "BreadcrumbList"
    if slug:
        assert graph[0]["@type"] == "Article"
        for heading, text in ARTICLES[slug]["sections"]:
            assert heading in graph[0]["articleBody"] and text in graph[0]["articleBody"]
    else:
        assert graph[0]["@type"] == "CollectionPage"
        assert response.text.count('class="glossary-term"') == len(TERMS)
    assert '"FAQPage"' not in raw and "aggregateRating" not in raw


def test_english_guides_are_not_duplicated_under_untranslated_routes():
    assert client.get("/hi/guide/").status_code == 404
    assert client.get("/en/guide/not-a-guide/").status_code == 404
    assert client.get("/en/guide/").headers["x-robots-tag"].startswith("noindex")


def test_help_and_chart_page_copy_exist_without_old_headline():
    html = client.get("/en/birth-chart/").text
    assert "Explore your sky" in html
    assert "Two charts." not in html
    assert "A traditional reading" not in html
    assert 'id="help-dialog"' in html and 'aria-labelledby="help-heading"' in html
    assert 'data-help="birth-time"' in html
    assert 'id="knowledge" type="application/json"' in html


def test_social_card_is_fixed_png_with_matching_metadata(monkeypatch):
    monkeypatch.setenv("SITE_URL", "https://astro.example.org")
    response = client.get("/social-card.png?name=NeverRenderThis")
    assert response.status_code == 200 and response.headers["content-type"] == "image/png"
    assert response.content == client.get("/social-card.png").content
    assert Image.open(BytesIO(response.content)).size == (1200, 630)
    assert "max-age=86400" in response.headers["cache-control"]
    html = client.get("/en/").text
    assert 'content="summary_large_image"' in html
    assert 'property="og:image" content="https://astro.example.org/social-card.png"' in html
    assert 'property="og:image:width" content="1200"' in html
