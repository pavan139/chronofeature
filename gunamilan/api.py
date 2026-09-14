"""
HTTP layer.

Both matching endpoints are public and have no payment enforcement. PDF
exports use the same validated inputs and calculations as interactive reports.

Run locally:
    uvicorn gunamilan.api:app --reload
"""

from __future__ import annotations

import datetime as dt
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi.responses import Response

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

# Import the functions, not the module: the package namespace binds `geocode`
# to the function of that name, which would shadow the module here.
from .geocode import search as search_places, is_ambiguous, stats as place_stats
from .ephemeris import BirthData, Chart, cast_chart, GRAHA_ORDER
from .matching import match
from .porutham import match_porutham
from .dasha import vimshottari, current_dasha, describe_current, marriage_windows
from .doshas import (
    mangal_dosha, compare_mangal, kaal_sarp_dosha, sade_sati,
)

app = FastAPI(
    title="Guna Milan",
    description=(
        "Vedic marriage compatibility from Swiss Ephemeris. Ashtakoota and "
        "Dasa Porutham, Vimshottari dashas, doshas with their classical "
        "exceptions, and offline geocoding."
    ),
    version="0.2.0",
)


# --------------------------------------------------------------------------
# Request models
# --------------------------------------------------------------------------

class BirthInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    date: dt.date
    time: dt.time | None = Field(
        None, description="Local birth time. Omit if unknown; the ascendant is then skipped."
    )
    place: str | None = Field(
        None, min_length=2, max_length=200, description="Place name, resolved offline. Use instead of coordinates."
    )
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    timezone: str | None = Field(None, description="IANA name; inferred from place when omitted.")

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, v):
        if v is not None:
            try:
                ZoneInfo(v)
            except (ZoneInfoNotFoundError, ValueError):
                raise ValueError("Use a valid IANA timezone")
        return v

    @field_validator("time")
    @classmethod
    def local_time_only(cls, v):
        if v is not None and v.tzinfo is not None:
            raise ValueError("Birth time must be local, without a UTC offset")
        return v

    @field_validator("date")
    @classmethod
    def not_in_the_future(cls, v: dt.date) -> dt.date:
        if v.year < 1800:
            raise ValueError("birth dates before 1800 are not supported by this service")
        if v > dt.date.today():
            raise ValueError("birth date cannot be in the future")
        return v

    def resolve(self) -> tuple[BirthData, str | None]:
        """Return birth data plus a warning if the place was ambiguous."""
        warning = None
        if self.place:
            try:
                candidates = search_places(self.place, limit=5)
            except FileNotFoundError as e:
                raise HTTPException(status_code=503, detail=str(e))
            if not candidates:
                raise HTTPException(
                    status_code=422,
                    detail=f"Could not find a place called {self.place!r}.",
                )
            chosen = candidates[0]
            rivals = is_ambiguous(self.place)
            if rivals:
                others = ", ".join(p.label for p in rivals[1:4])
                warning = (
                    f"{self.place!r} matched several places. Used {chosen.label}; "
                    f"other candidates were {others}."
                )
            data = BirthData.from_place(
                self.name, self.date, self.time, chosen,
                time_known=self.time is not None,
            )
        elif self.latitude is not None and self.longitude is not None:
            data = BirthData(
                name=self.name, date=self.date, time=self.time or dt.time(12, 0),
                latitude=self.latitude, longitude=self.longitude,
                timezone=self.timezone or "Asia/Kolkata",
                time_known=self.time is not None,
            )
        else:
            raise HTTPException(
                status_code=422,
                detail="Provide either a place name or both latitude and longitude.",
            )
        return data, warning


class MatchRequest(BaseModel):
    groom: BirthInput
    bride: BirthInput
    ayanamsa: Literal["lahiri", "raman", "krishnamurti", "fagan_bradley"] = "lahiri"
    system: Literal["ashtakoota", "porutham", "both"] = "both"


# --------------------------------------------------------------------------
# Serialisation helpers
# --------------------------------------------------------------------------

def _position_dict(pos) -> dict:
    return {
        "rashi": pos.rashi_name,
        "nakshatra": pos.nakshatra_name,
        "pada": pos.pada,
        "degrees": pos.format_degrees(),
        "navamsa": pos.navamsa_name,
        "longitude": round(pos.longitude, 4),
    }


def _chart_dict(chart: Chart) -> dict:
    return {
        "name": chart.name,
        "place": chart.birth.place_label or None,
        "ascendant": _position_dict(chart.ascendant) if chart.ascendant else None,
        "grahas": [
            {
                "name": name,
                **_position_dict(chart.grahas[name].position),
                "house": chart.grahas[name].house or None,
                "retrograde": chart.grahas[name].retrograde,
                "combust": chart.grahas[name].combust,
                "dignity": chart.grahas[name].dignity,
            }
            for name in GRAHA_ORDER
        ],
        "time_known": chart.time_known,
        "ayanamsa": chart.ayanamsa,
    }


DISCLAIMER = (
    "Guna Milan is one traditional input among several and is not a prediction. "
    "Results vary between schools of astrology, and no compatibility score should "
    "be treated as a decision on its own."
)


def _accuracy_note(*charts: Chart) -> str | None:
    if all(c.time_known for c in charts):
        return None
    return (
        "A birth time was missing, so the Moon position is approximate and the "
        "ascendant was skipped. The Moon changes nakshatra roughly every 21 hours, "
        "which can move four of the eight kootas."
    )


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------

@app.get("/health")
def health() -> dict:
    try:
        return {"status": "ok", "places": place_stats()}
    except FileNotFoundError:
        return {"status": "degraded", "detail": "place database not built"}


@app.get("/places")
def places(q: str = Query(..., min_length=2), limit: int = Query(8, ge=1, le=25)) -> dict:
    """Typeahead for the birth-place field."""
    try:
        results = search_places(q, limit=limit)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return {
        "query": q,
        "results": [
            {
                "label": p.label, "name": p.name, "region": p.region,
                "country": p.country, "latitude": p.latitude,
                "longitude": p.longitude, "timezone": p.timezone,
                "population": p.population,
            }
            for p in results
        ],
    }


@app.post("/chart")
def chart_endpoint(birth: BirthInput, ayanamsa: str = "lahiri") -> dict:
    """Full natal chart: nine grahas, houses, Navamsa, dashas and doshas."""
    data, warning = birth.resolve()
    try:
        chart = cast_chart(data, ayanamsa)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    out = _chart_dict(chart)
    out["dasha"] = {
        "current": [p.to_dict() for p in current_dasha(chart)],
        "summary": describe_current(chart),
        "mahadashas": [p.to_dict() for p in vimshottari(chart, depth=1)],
    }
    out["doshas"] = {
        "mangal": mangal_dosha(chart).to_dict(),
        "kaal_sarp": kaal_sarp_dosha(chart).to_dict(),
        "sade_sati": sade_sati(chart).to_dict(),
    }
    out["disclaimer"] = DISCLAIMER
    if warning:
        out["place_warning"] = warning
    if note := _accuracy_note(chart):
        out["accuracy_warning"] = note
    return out


@app.post("/match/free")
def match_free(req: MatchRequest) -> dict:
    """The free result: the score, the eight breakdowns, and the headline verdict.

    Deliberately generous. A bare number does not get forwarded to a family
    group, and forwarding is how this reaches people who never searched for it.
    """
    groom_data, groom_warn = req.groom.resolve()
    bride_data, bride_warn = req.bride.resolve()
    try:
        groom = cast_chart(groom_data, req.ayanamsa)
        bride = cast_chart(bride_data, req.ayanamsa)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    out: dict = {"ayanamsa": req.ayanamsa, "disclaimer": DISCLAIMER}

    if req.system in ("ashtakoota", "both"):
        out["ashtakoota"] = match(groom, bride).to_dict()
    if req.system in ("porutham", "both"):
        out["porutham"] = match_porutham(groom, bride).to_dict()

    out["charts"] = {
        "groom": {
            "nakshatra": groom.moon.nakshatra_name, "pada": groom.moon.pada,
            "rashi": groom.moon.rashi_name,
        },
        "bride": {
            "nakshatra": bride.moon.nakshatra_name, "pada": bride.moon.pada,
            "rashi": bride.moon.rashi_name,
        },
    }

    warnings = [w for w in (groom_warn, bride_warn) if w]
    if warnings:
        out["place_warnings"] = warnings
    if note := _accuracy_note(groom, bride):
        out["accuracy_warning"] = note
    return out


@app.post("/match/full")
def match_full(req: MatchRequest) -> dict:
    """Full public calculation. No authentication or payment gate is implied."""
    result = match_free(req)

    groom_data, _ = req.groom.resolve()
    bride_data, _ = req.bride.resolve()
    groom = cast_chart(groom_data, req.ayanamsa)
    bride = cast_chart(bride_data, req.ayanamsa)

    g_mangal, b_mangal = mangal_dosha(groom), mangal_dosha(bride)
    result["doshas"] = {
        "mangal": {
            "groom": g_mangal.to_dict(),
            "bride": b_mangal.to_dict(),
            "summary": compare_mangal(g_mangal, b_mangal),
        },
        "kaal_sarp": {
            "groom": kaal_sarp_dosha(groom).to_dict(),
            "bride": kaal_sarp_dosha(bride).to_dict(),
        },
        "sade_sati": {
            "groom": sade_sati(groom).to_dict(),
            "bride": sade_sati(bride).to_dict(),
        },
    }
    result["dasha"] = {
        "groom": describe_current(groom),
        "bride": describe_current(bride),
        "shared_windows": [
            p.to_dict() for p in marriage_windows(groom)[:6]
        ],
        "windows_note": (
            "Periods classically associated with marriage. These are candidates "
            "for an astrologer to weigh, not predicted dates."
        ),
    }
    result["full_charts"] = {"groom": _chart_dict(groom), "bride": _chart_dict(bride)}
    return result


@app.post("/reports/match.pdf", response_class=Response)
def match_pdf(req: MatchRequest, locale: str = "en"):
    from .reports import render_pdf, validate_locale
    validate_locale(locale)
    result = match_full(req)
    return render_pdf(result, [_report_birth(req.groom), _report_birth(req.bride)],
                      "match", locale, req.ayanamsa)


@app.post("/reports/chart.pdf", response_class=Response)
def chart_pdf(birth: BirthInput, locale: str = "en", ayanamsa: str = "lahiri"):
    from .reports import render_pdf, validate_locale
    validate_locale(locale)
    result = chart_endpoint(birth, ayanamsa)
    return render_pdf(result, [_report_birth(birth)], "chart", locale, ayanamsa)


def _report_birth(birth: BirthInput):
    resolved, _ = birth.resolve()
    return {**birth.model_dump(mode="json"), "timezone": resolved.timezone,
            "latitude": resolved.latitude, "longitude": resolved.longitude,
            "place": resolved.place_label or birth.place}


# Public documents are rendered on the server. Personal results are POST-only.
from .web import install_web
install_web(app)
