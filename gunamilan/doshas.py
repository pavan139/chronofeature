"""
Doshas and their exceptions.

Most free tools report a dosha and stop. The exceptions are where the actual
skill sits, and leaving them out is why so many people are told a match is
ruined when a practising astrologer would have waived it. Every cancellation
here is applied explicitly and named in the output, so the reader can see which
rule fired rather than being handed a verdict.

Covered:
  - Mangal (Manglik), checked from the ascendant, the Moon and Venus
  - Kaal Sarp, with its partial form
  - Sade Sati, the seven-and-a-half year Saturn transit
  - The classical exceptions to Nadi and Bhakoot dosha
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, asdict, field

from . import tables
from .ephemeris import Chart, Position, house_from, transit_positions

# Mars is comfortable in these signs, one basis for cancellation.
MARS_OWN_SIGNS = {0, 7}       # Aries, Scorpio
MARS_EXALTATION = 9           # Capricorn
MARS_DEBILITATION = 3         # Cancer

# Signs in which Mangal dosha is traditionally held not to apply, counted by
# the house Mars occupies. Widely cited, though schools differ.
MANGAL_EXEMPT_SIGNS = {
    1: {0, 7},        # Mars in Aries or Scorpio in the 1st
    2: {2, 5},        # Mercury signs in the 2nd
    4: {1, 6},        # Venus signs in the 4th
    7: {3, 9},        # Cancer or Capricorn in the 7th
    8: {8, 11},       # Jupiter signs in the 8th
    12: {1, 6},       # Venus signs in the 12th
}


@dataclass
class DoshaReport:
    name: str
    present: bool
    severity: str                       # none, mild, moderate, severe
    detail: str
    cancellations: list[str] = field(default_factory=list)
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


# --------------------------------------------------------------------------
# Mangal (Manglik) dosha
# --------------------------------------------------------------------------

def mangal_dosha(chart: Chart) -> DoshaReport:
    """Mars in houses 1, 2, 4, 7, 8 or 12, checked from three reference points.

    Checking from the Moon and Venus as well as the ascendant is standard in
    North Indian practice. Counting only from the ascendant, which is what most
    free tools do, misses roughly half of real cases.
    """
    mars = chart.mars
    references: list[tuple[str, Position]] = [("Moon", chart.moon)]
    if chart.ascendant:
        references.insert(0, ("ascendant", chart.ascendant))
    references.append(("Venus", chart.grahas["Venus"].position))

    afflicted = []
    for label, ref in references:
        house = house_from(ref, mars)
        if house in tables.MANGAL_HOUSES:
            afflicted.append((label, house))

    present = bool(afflicted)
    cancellations: list[str] = []

    if present:
        if mars.rashi in MARS_OWN_SIGNS:
            cancellations.append(
                f"Mars occupies its own sign ({tables.RASHIS_EN[mars.rashi]}), "
                "which most traditions treat as cancelling the dosha."
            )
        if mars.rashi == MARS_EXALTATION:
            cancellations.append(
                "Mars is exalted in Capricorn, a standard ground for cancellation."
            )
        if mars.rashi == MARS_DEBILITATION:
            cancellations.append(
                "Mars is debilitated in Cancer. Some schools read this as cancelling "
                "the dosha and others as intensifying it."
            )
        for _, house in afflicted:
            exempt = MANGAL_EXEMPT_SIGNS.get(house, set())
            if mars.rashi in exempt:
                cancellations.append(
                    f"Mars in {tables.RASHIS_EN[mars.rashi]} in house {house} falls "
                    "under the classical sign exemption for that house."
                )
                break
        jupiter = chart.grahas["Jupiter"]
        if abs(((jupiter.position.rashi - mars.rashi) % 12)) in (4, 8) or \
           jupiter.position.rashi == mars.rashi:
            cancellations.append(
                "Jupiter aspects or joins Mars, which is widely held to soften the dosha."
            )

    if not present:
        severity = "none"
    elif cancellations:
        severity = "mild"
    elif any(h in tables.MANGAL_SEVERE_HOUSES for _, h in afflicted):
        severity = "severe"
    elif len(afflicted) >= 2:
        severity = "moderate"
    else:
        severity = "mild"

    if not present:
        detail = (
            "Mars occupies none of the six houses that create Mangal dosha, counted "
            "from the ascendant, the Moon or Venus."
        )
    else:
        where = ", ".join(f"house {h} from the {src}" for src, h in afflicted)
        detail = f"Mars occupies {where}."
        if cancellations:
            detail += " Classical cancellations apply, listed separately."

    if not chart.time_known:
        detail += (
            " No birth time was supplied, so the ascendant check was skipped and "
            "this reading rests on the Moon and Venus alone."
        )

    return DoshaReport(
        name="Mangal", present=present, severity=severity, detail=detail,
        cancellations=cancellations,
        data={
            "afflicted_from": {src: h for src, h in afflicted},
            "mars_sign": tables.RASHIS_EN[mars.rashi],
            "checked_ascendant": chart.ascendant is not None,
        },
    )


def compare_mangal(groom: DoshaReport, bride: DoshaReport) -> str:
    """The rule families care about: does one side's dosha cancel the other's."""
    if not groom.present and not bride.present:
        return "Neither chart carries Mangal dosha."
    if groom.present and bride.present:
        return (
            "Both charts carry Mangal dosha. This is the most widely accepted "
            "cancellation in the tradition: when both partners are Manglik, the "
            "affliction is held to neutralise itself."
        )
    who = "groom" if groom.present else "bride"
    other = "bride" if groom.present else "groom"
    afflicted = groom if groom.present else bride
    text = (
        f"The {who}'s chart carries Mangal dosha ({afflicted.severity}) and the "
        f"{other}'s does not."
    )
    if afflicted.cancellations:
        text += " Cancellations apply, so most astrologers would not treat this as blocking."
    else:
        text += (
            " Traditions differ on remedies here. Most astrologers weigh the severity "
            "rather than treating it as a blanket objection."
        )
    return text


# --------------------------------------------------------------------------
# Kaal Sarp dosha
# --------------------------------------------------------------------------

KAAL_SARP_TYPES = [
    "Anant", "Kulik", "Vasuki", "Shankhpal", "Padma", "Mahapadma",
    "Takshak", "Karkotak", "Shankhachud", "Ghatak", "Vishdhar", "Sheshnag",
]


def kaal_sarp_dosha(chart: Chart) -> DoshaReport:
    """All seven visible grahas hemmed between Rahu and Ketu.

    Partial Kaal Sarp, where one or two planets sit outside the axis, is
    reported separately because it is read far more lightly.
    """
    rahu = chart.grahas["Rahu"].position.longitude
    ketu = chart.grahas["Ketu"].position.longitude

    def within_rahu_to_ketu(lon: float) -> bool:
        """True if the longitude lies on the arc travelling from Rahu to Ketu."""
        return ((lon - rahu) % 360.0) < ((ketu - rahu) % 360.0)

    planets = [n for n in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")]
    on_one_side = [n for n in planets if within_rahu_to_ketu(chart.grahas[n].position.longitude)]
    on_other = [n for n in planets if n not in on_one_side]

    full = len(on_one_side) == 7 or len(on_other) == 7
    outside = min(len(on_one_side), len(on_other))
    partial = 0 < outside <= 2

    if full:
        house = chart.grahas["Rahu"].house
        kind = KAAL_SARP_TYPES[(house - 1) % 12] if house else None
        detail = (
            "All seven visible grahas fall on one side of the Rahu-Ketu axis, "
            "forming full Kaal Sarp dosha."
        )
        if kind:
            detail += f" With Rahu in house {house}, this is the {kind} variety."
        return DoshaReport("Kaal Sarp", True, "moderate", detail,
                           data={"type": kind, "rahu_house": house})

    if partial:
        escaped = on_other if len(on_other) < len(on_one_side) else on_one_side
        return DoshaReport(
            "Kaal Sarp", True, "mild",
            f"Partial Kaal Sarp: {' and '.join(escaped)} fall outside the "
            "Rahu-Ketu axis, which most traditions read as substantially reducing "
            "the effect.",
            data={"outside_axis": escaped},
        )

    return DoshaReport(
        "Kaal Sarp", False, "none",
        "The grahas are distributed on both sides of the Rahu-Ketu axis, so Kaal "
        "Sarp dosha does not form.",
    )


# --------------------------------------------------------------------------
# Sade Sati
# --------------------------------------------------------------------------

SADE_SATI_PHASES = {
    12: ("rising", "Saturn in the twelfth from the Moon: expenditure, sleep and "
                   "unsettled beginnings."),
    1:  ("peak", "Saturn over the natal Moon: the heaviest phase, read as pressure "
                 "on health and state of mind."),
    2:  ("setting", "Saturn in the second from the Moon: family and finances, and "
                    "the phase where the cycle eases."),
}


def sade_sati(chart: Chart, when: dt.date | None = None) -> DoshaReport:
    """Whether Saturn is currently transiting the 12th, 1st or 2nd from the Moon."""
    when = when or dt.date.today()
    moment = dt.datetime.combine(when, dt.time(12, 0), dt.timezone.utc)
    saturn = transit_positions(moment, chart.ayanamsa)["Saturn"]

    house = house_from(chart.moon, saturn)
    phase = SADE_SATI_PHASES.get(house)

    if phase:
        label, description = phase
        return DoshaReport(
            "Sade Sati", True, "moderate" if label == "peak" else "mild",
            f"Sade Sati is running, in its {label} phase. {description}",
            data={
                "phase": label,
                "saturn_sign": saturn.rashi_name,
                "moon_sign": chart.moon.rashi_name,
                "house_from_moon": house,
                "as_of": when.isoformat(),
            },
        )

    # Dhaiya, the two-and-a-half year Saturn transits, are the lighter relatives.
    if house in (4, 8):
        return DoshaReport(
            "Sade Sati", False, "mild",
            f"Sade Sati is not running. Saturn transits the {house}th from the "
            "natal Moon, which is the shorter Dhaiya period.",
            data={"phase": "dhaiya", "house_from_moon": house,
                  "as_of": when.isoformat()},
        )

    return DoshaReport(
        "Sade Sati", False, "none",
        f"Sade Sati is not running. Saturn is in {saturn.rashi_name}, which is "
        f"house {house} from the natal Moon.",
        data={"house_from_moon": house, "as_of": when.isoformat()},
    )


# --------------------------------------------------------------------------
# Exceptions to the heavy kootas
# --------------------------------------------------------------------------

def nadi_exceptions(groom: Chart, bride: Chart) -> list[str]:
    """Classical grounds for waiving Nadi dosha.

    Nadi costs eight of thirty-six points, so whether an exception applies often
    decides the whole match. These are the commonly accepted ones.
    """
    g, b = groom.moon, bride.moon
    out = []

    if g.nakshatra == b.nakshatra and g.pada != b.pada:
        out.append(
            "Both Moons fall in the same nakshatra but different padas, which is a "
            "recognised exemption."
        )
    if g.rashi != b.rashi and g.nakshatra == b.nakshatra:
        out.append("Same nakshatra but different Moon signs, a recognised exemption.")
    if g.rashi == b.rashi and g.nakshatra != b.nakshatra:
        out.append("Same Moon sign but different nakshatras, a recognised exemption.")
    if tables.RASHI_LORD[g.rashi] == tables.RASHI_LORD[b.rashi]:
        out.append(
            f"Both Moon signs share the same lord ({tables.RASHI_LORD[g.rashi]}), "
            "which several authorities accept as cancelling Nadi dosha."
        )
    return out


def bhakoot_exceptions(groom: Chart, bride: Chart) -> list[str]:
    """Classical grounds for waiving Bhakoot dosha."""
    g, b = groom.moon, bride.moon
    out = []

    g_lord, b_lord = tables.RASHI_LORD[g.rashi], tables.RASHI_LORD[b.rashi]
    if g_lord == b_lord:
        out.append(
            f"Both Moon signs are ruled by {g_lord}, the most commonly cited "
            "Bhakoot exemption."
        )
    elif b_lord in tables.PLANET_FRIENDS.get(g_lord, set()) and \
            g_lord in tables.PLANET_FRIENDS.get(b_lord, set()):
        out.append(
            f"The sign lords ({g_lord} and {b_lord}) are mutual friends, which is "
            "accepted as cancelling Bhakoot dosha."
        )

    if ((g.nakshatra - b.nakshatra) % 27) in (0,):
        out.append("Both Moons share a nakshatra, a further recognised exemption.")
    return out


def full_dosha_report(chart: Chart, when: dt.date | None = None) -> dict:
    """Every dosha this engine knows about, for one chart."""
    return {
        "mangal": mangal_dosha(chart).to_dict(),
        "kaal_sarp": kaal_sarp_dosha(chart).to_dict(),
        "sade_sati": sade_sati(chart, when).to_dict(),
    }
