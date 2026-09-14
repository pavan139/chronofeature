"""
Dasa Porutham: the South Indian matching system.

Ashtakoota is North Indian. Tamil, Malayalam and much of Telugu practice uses
the ten poruthams instead, and a Chennai or Kochi family handed a 36-point guna
score will tell you it is the wrong system. This module implements the ten
poruthams so the same birth data answers both traditions.

The overlap is partial: Yoni, Gana, Rasi and Rasyadhipathi correspond closely to
kootas, while Rajju, Vedha, Mahendra and Stree Deergha have no Ashtakoota
equivalent at all. Rajju is the South Indian counterpart to Nadi dosha and
carries the same weight: a shared rajju is the one result that stops a match.

Where authorities differ the variant used is named in the docstring of the
function, so a practitioner can see which tradition is encoded.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict

from . import tables
from .ephemeris import Chart, Position

# --------------------------------------------------------------------------
# Rajju: the nakshatras mapped onto the body, ascending then descending.
# Siro (head) holds three; the other four hold six each.
# --------------------------------------------------------------------------

RAJJU_BY_NAKSHATRA = [
    "Paada",  # Ashwini
    "Jaanu",  # Bharani
    "Naabhi", # Krittika
    "Kanta",  # Rohini
    "Siro",   # Mrigashira
    "Kanta",  # Ardra
    "Naabhi", # Punarvasu
    "Jaanu",  # Pushya
    "Paada",  # Ashlesha
    "Paada",  # Magha
    "Jaanu",  # Purva Phalguni
    "Naabhi", # Uttara Phalguni
    "Kanta",  # Hasta
    "Siro",   # Chitra
    "Kanta",  # Swati
    "Naabhi", # Vishakha
    "Jaanu",  # Anuradha
    "Paada",  # Jyeshtha
    "Paada",  # Mula
    "Jaanu",  # Purva Ashadha
    "Naabhi", # Uttara Ashadha
    "Kanta",  # Shravana
    "Siro",   # Dhanishta
    "Kanta",  # Shatabhisha
    "Naabhi", # Purva Bhadrapada
    "Jaanu",  # Uttara Bhadrapada
    "Paada",  # Revati
]

RAJJU_MEANING = {
    "Paada": "the feet, read as wandering and separation",
    "Jaanu": "the knees, read as poverty and obstruction",
    "Naabhi": "the navel, read as difficulty with children",
    "Kanta": "the neck, read as risk to the spouse",
    "Siro": "the head, read as the gravest of the five",
}

# --------------------------------------------------------------------------
# Vedha: mutually obstructing nakshatra pairs, 0-based.
# Chitra appears in no pair in the authorities followed here.
# --------------------------------------------------------------------------

_VEDHA_PAIRS = [
    (0, 17), (1, 16), (2, 15), (3, 14), (4, 22), (5, 21), (6, 20),
    (7, 19), (8, 18), (9, 26), (10, 25), (11, 24), (12, 23),
]

VEDHA_PARTNER: dict[int, int] = {}
for _a, _b in _VEDHA_PAIRS:
    VEDHA_PARTNER[_a] = _b
    VEDHA_PARTNER[_b] = _a

# Mahendra: favourable counts from the bride's star to the groom's.
MAHENDRA_COUNTS = {4, 7, 10, 13, 16, 19, 22, 25}

# Dina porutham: favourable remainders after dividing the count by nine.
DINA_GOOD_REMAINDERS = {2, 4, 6, 8, 0}


@dataclass
class PoruthamResult:
    name: str
    tamil_name: str
    passed: bool
    weight: str            # "essential" or "supporting"
    groom_attribute: str
    bride_attribute: str
    explanation: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PoruthamMatch:
    groom: str
    bride: str
    passed: int
    total: int
    essential_failures: list[str]
    poruthams: list[PoruthamResult]
    verdict: str

    def to_dict(self) -> dict:
        return {
            "groom": self.groom,
            "bride": self.bride,
            "passed": self.passed,
            "total": self.total,
            "essential_failures": self.essential_failures,
            "verdict": self.verdict,
            "poruthams": [p.to_dict() for p in self.poruthams],
        }


def _count_stars(frm: int, to: int) -> int:
    """Inclusive count from one nakshatra to another, 1 to 27."""
    return ((to - frm) % 27) + 1


# --------------------------------------------------------------------------
# The ten poruthams
# --------------------------------------------------------------------------

def dina_porutham(groom: Position, bride: Position) -> PoruthamResult:
    """Counted from the bride's star to the groom's; remainder decides."""
    count = _count_stars(bride.nakshatra, groom.nakshatra)
    remainder = count % 9
    passed = remainder in DINA_GOOD_REMAINDERS
    return PoruthamResult(
        "Dina", "\u0ba4\u0bbf\u0ba9 \u0baa\u0bca\u0bb0\u0bc1\u0ba4\u0bcd\u0ba4\u0bae\u0bcd",
        passed, "supporting",
        groom.nakshatra_name, bride.nakshatra_name,
        f"The groom's star is {count} from the bride's, leaving remainder {remainder}. "
        + ("This falls among the favourable remainders, read as general wellbeing."
           if passed else
           "This is not among the favourable remainders, traditionally linked to health and harmony."),
    )


def gana_porutham(groom: Position, bride: Position) -> PoruthamResult:
    g = tables.GANA_BY_NAKSHATRA[groom.nakshatra]
    b = tables.GANA_BY_NAKSHATRA[bride.nakshatra]
    passed = tables.GANA_MATRIX[g][b] >= 5.0
    return PoruthamResult(
        "Gana", "\u0b95\u0ba3 \u0baa\u0bca\u0bb0\u0bc1\u0ba4\u0bcd\u0ba4\u0bae\u0bcd",
        passed, "supporting", g, b,
        f"The groom is {g} and the bride {b}. "
        + ("These temperaments sit comfortably together."
           if passed else
           "These temperaments are read as pulling in different directions."),
    )


def mahendra_porutham(groom: Position, bride: Position) -> PoruthamResult:
    """Read as the couple's prosperity and continuity of line."""
    count = _count_stars(bride.nakshatra, groom.nakshatra)
    passed = count in MAHENDRA_COUNTS
    return PoruthamResult(
        "Mahendra", "\u0bae\u0b95\u0bc7\u0ba8\u0bcd\u0ba4\u0bbf\u0bb0 \u0baa\u0bca\u0bb0\u0bc1\u0ba4\u0bcd\u0ba4\u0bae\u0bcd",
        passed, "supporting",
        f"star {count} from bride", bride.nakshatra_name,
        f"The groom's star is {count} from the bride's. "
        + ("This is one of the Mahendra counts, read as wellbeing and continuity."
           if passed else
           "This is not a Mahendra count, so the porutham is absent."),
    )


def stree_deergha_porutham(groom: Position, bride: Position) -> PoruthamResult:
    """Distance from the bride's star to the groom's, read as her longevity and ease."""
    count = _count_stars(bride.nakshatra, groom.nakshatra)
    passed = count > 13
    return PoruthamResult(
        "Stree Deergha", "\u0bb8\u0bcd\u0ba4\u0bbf\u0bb0\u0bc0 \u0ba4\u0bc0\u0bb0\u0bcd\u0b95\u0bcd\u0b95 \u0baa\u0bca\u0bb0\u0bc1\u0ba4\u0bcd\u0ba4\u0bae\u0bcd",
        passed, "supporting",
        f"star {count} from bride", bride.nakshatra_name,
        f"The count is {count}. "
        + ("Above thirteen, which satisfies the porutham."
           if passed else
           "Thirteen or below. Several authorities accept nine as the threshold, "
           "under which this would pass."),
    )


def yoni_porutham(groom: Position, bride: Position) -> PoruthamResult:
    g_animal, g_sex = tables.YONI_BY_NAKSHATRA[groom.nakshatra]
    b_animal, b_sex = tables.YONI_BY_NAKSHATRA[bride.nakshatra]
    score = tables.YONI_MATRIX[g_animal][b_animal]
    passed = score >= 3
    return PoruthamResult(
        "Yoni", "\u0baf\u0bc7\u0bbe\u0ba9\u0bbf \u0baa\u0bca\u0bb0\u0bc1\u0ba4\u0bcd\u0ba4\u0bae\u0bcd",
        passed, "supporting",
        f"{g_animal} ({g_sex})", f"{b_animal} ({b_sex})",
        f"The animal signs are {g_animal} and {b_animal}. "
        + ("They are the same or friendly, satisfying the porutham."
           if passed else
           "They are not compatible under the yoni table."),
    )


def rasi_porutham(groom: Position, bride: Position) -> PoruthamResult:
    """The groom's Moon sign should sit seven or further from the bride's."""
    count = ((groom.rashi - bride.rashi) % 12) + 1
    passed = count >= 7 or count == 1
    return PoruthamResult(
        "Rasi", "\u0bb0\u0bbe\u0b9a\u0bbf \u0baa\u0bca\u0bb0\u0bc1\u0ba4\u0bcd\u0ba4\u0bae\u0bcd",
        passed, "essential",
        groom.rashi_name, bride.rashi_name,
        f"The groom's sign is {count} from the bride's. "
        + ("Same sign or seven or beyond, which satisfies the porutham."
           if passed else
           "Under seven, which the tradition reads as unfavourable for the family line."),
    )


def rasyadhipathi_porutham(groom: Position, bride: Position) -> PoruthamResult:
    """Friendship between the lords of the two Moon signs."""
    g_lord = tables.RASHI_LORD[groom.rashi]
    b_lord = tables.RASHI_LORD[bride.rashi]

    if g_lord == b_lord:
        passed, note = True, "Both signs share the same lord."
    else:
        friendly = (b_lord in tables.PLANET_FRIENDS[g_lord]
                    or g_lord in tables.PLANET_FRIENDS[b_lord])
        hostile = (b_lord in tables.PLANET_ENEMIES[g_lord]
                   and g_lord in tables.PLANET_ENEMIES[b_lord])
        passed = friendly and not hostile
        note = ("The lords regard each other as friends." if passed
                else "The lords are not friendly to each other.")

    return PoruthamResult(
        "Rasyadhipathi", "\u0bb0\u0bbe\u0b9a\u0bbf\u0baf\u0ba4\u0bbf\u0baa\u0ba4\u0bbf \u0baa\u0bca\u0bb0\u0bc1\u0ba4\u0bcd\u0ba4\u0bae\u0bcd",
        passed, "essential", g_lord, b_lord,
        f"{note} This porutham is read as the durability of the bond.",
    )


def vashya_porutham(groom: Position, bride: Position) -> PoruthamResult:
    def category(p: Position) -> str:
        if p.rashi in tables.VASHYA_SECOND_HALF_OVERRIDE and p.degrees_in_rashi >= 15.0:
            return tables.VASHYA_SECOND_HALF_OVERRIDE[p.rashi]
        return tables.VASHYA_BY_RASHI[p.rashi]

    g, b = category(groom), category(bride)
    passed = tables.VASHYA_MATRIX[g][b] >= 1.0
    return PoruthamResult(
        "Vashya", "\u0bb5\u0b9a\u0bbf\u0baf \u0baa\u0bca\u0bb0\u0bc1\u0ba4\u0bcd\u0ba4\u0bae\u0bcd",
        passed, "supporting", g, b,
        f"The groups are {g} and {b}. "
        + ("Mutual influence runs easily between them."
           if passed else
           "Neither group yields to the other under the vashya table."),
    )


def rajju_porutham(groom: Position, bride: Position) -> PoruthamResult:
    """The heaviest porutham. A shared rajju is the South Indian counterpart to Nadi dosha."""
    g = RAJJU_BY_NAKSHATRA[groom.nakshatra]
    b = RAJJU_BY_NAKSHATRA[bride.nakshatra]
    passed = g != b
    if passed:
        note = f"The rajjus differ ({g} and {b}), which satisfies the porutham."
    else:
        note = (
            f"Both stars fall in {g} rajju, {RAJJU_MEANING[g]}. A shared rajju is the "
            "single strongest objection in the South Indian system and is rarely waived."
        )
    return PoruthamResult(
        "Rajju", "\u0bb0\u0b9c\u0bcd\u0b9c\u0bc1 \u0baa\u0bca\u0bb0\u0bc1\u0ba4\u0bcd\u0ba4\u0bae\u0bcd",
        passed, "essential", g, b, note,
    )


def vedha_porutham(groom: Position, bride: Position) -> PoruthamResult:
    """Mutually obstructing star pairs."""
    partner = VEDHA_PARTNER.get(bride.nakshatra)
    passed = partner != groom.nakshatra
    if passed:
        note = "The two stars do not form a vedha pair."
    else:
        note = (
            f"{groom.nakshatra_name} and {bride.nakshatra_name} are a vedha pair, "
            "read as mutually obstructing."
        )
    return PoruthamResult(
        "Vedha", "\u0bb5\u0bc7\u0ba4\u0bc8 \u0baa\u0bca\u0bb0\u0bc1\u0ba4\u0bcd\u0ba4\u0bae\u0bcd",
        passed, "essential",
        groom.nakshatra_name, bride.nakshatra_name, note,
    )


PORUTHAMS = [
    dina_porutham, gana_porutham, mahendra_porutham, stree_deergha_porutham,
    yoni_porutham, rasi_porutham, rasyadhipathi_porutham, vashya_porutham,
    rajju_porutham, vedha_porutham,
]


def _verdict(results: list[PoruthamResult]) -> str:
    passed = sum(1 for r in results if r.passed)
    essential_failed = [r.name for r in results if r.weight == "essential" and not r.passed]

    if "Rajju" in essential_failed:
        return (
            f"{passed} of 10 poruthams match, but Rajju does not. In South Indian "
            "practice Rajju is treated as decisive on its own, and most astrologers "
            "would not proceed on the count alone."
        )
    if essential_failed:
        return (
            f"{passed} of 10 poruthams match. The essential ones that fail are "
            f"{', '.join(essential_failed)}, which carry more weight than the total."
        )
    if passed >= 7:
        return f"{passed} of 10 poruthams match, with all the essential ones intact. A strong result."
    if passed >= 5:
        return f"{passed} of 10 poruthams match, with the essential ones intact. Conventionally acceptable."
    return f"Only {passed} of 10 poruthams match, which is below what most families would accept."


def match_porutham(groom_chart: Chart, bride_chart: Chart) -> PoruthamMatch:
    """Score a pair across the ten poruthams."""
    results = [fn(groom_chart.moon, bride_chart.moon) for fn in PORUTHAMS]
    return PoruthamMatch(
        groom=groom_chart.name,
        bride=bride_chart.name,
        passed=sum(1 for r in results if r.passed),
        total=len(results),
        essential_failures=[r.name for r in results if r.weight == "essential" and not r.passed],
        poruthams=results,
        verdict=_verdict(results),
    )
