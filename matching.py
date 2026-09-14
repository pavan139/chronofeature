"""
Ashtakoota (Guna Milan) scoring: eight kootas totalling 36 points.

Each koota returns a KootaResult carrying its score, its maximum, and a plain
sentence explaining why it landed there. The explanation is generated from the
rule itself, not written by a language model, so it is always consistent with
the number beside it.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field

from . import tables
from .ephemeris import Chart, Position


@dataclass
class KootaResult:
    name: str
    score: float
    maximum: float
    groom_attribute: str
    bride_attribute: str
    explanation: str

    @property
    def is_full(self) -> bool:
        return self.score == self.maximum

    @property
    def is_zero(self) -> bool:
        return self.score == 0


@dataclass
class MatchResult:
    groom: str
    bride: str
    total: float
    maximum: float
    kootas: list[KootaResult]
    verdict: str
    nadi_exceptions: list[str] = field(default_factory=list)
    bhakoot_exceptions: list[str] = field(default_factory=list)

    @property
    def percentage(self) -> float:
        return round(100.0 * self.total / self.maximum, 1)

    @property
    def blocking_doshas(self) -> list[str]:
        """Zero-scoring heavy kootas with no exception to waive them."""
        out = []
        for k in self.kootas:
            if k.name == "Nadi" and k.is_zero and not self.nadi_exceptions:
                out.append("Nadi")
            if k.name == "Bhakoot" and k.is_zero and not self.bhakoot_exceptions:
                out.append("Bhakoot")
        return out

    def to_dict(self) -> dict:
        return {
            "groom": self.groom,
            "bride": self.bride,
            "total": self.total,
            "maximum": self.maximum,
            "percentage": self.percentage,
            "verdict": self.verdict,
            "blocking_doshas": self.blocking_doshas,
            "exceptions": {
                "nadi": self.nadi_exceptions,
                "bhakoot": self.bhakoot_exceptions,
            },
            "kootas": [asdict(k) for k in self.kootas],
        }


# --------------------------------------------------------------------------
# Individual kootas
# --------------------------------------------------------------------------

def varna_koota(groom: Position, bride: Position) -> KootaResult:
    g = tables.VARNA_BY_RASHI[groom.rashi]
    b = tables.VARNA_BY_RASHI[bride.rashi]
    score = 1.0 if tables.VARNA_RANK[g] >= tables.VARNA_RANK[b] else 0.0

    if score:
        explanation = (
            f"The groom's varna ({g}) is not below the bride's ({b}), "
            "which the rule treats as a settled working temperament."
        )
    else:
        explanation = (
            f"The groom's varna ({g}) sits below the bride's ({b}). "
            "Classically read as friction over who leads; it is the lightest "
            "koota at one point and rarely decides a match on its own."
        )
    return KootaResult("Varna", score, 1.0, g, b, explanation)


def vashya_koota(groom: Position, bride: Position) -> KootaResult:
    def category(p: Position) -> str:
        if p.rashi in tables.VASHYA_SECOND_HALF_OVERRIDE and p.degrees_in_rashi >= 15.0:
            return tables.VASHYA_SECOND_HALF_OVERRIDE[p.rashi]
        return tables.VASHYA_BY_RASHI[p.rashi]

    g, b = category(groom), category(bride)
    score = tables.VASHYA_MATRIX[g][b]

    if score == 2.0:
        explanation = f"Both fall in compatible vashya groups ({g} and {b}), indicating easy mutual influence."
    elif score == 0.0:
        explanation = f"The {g} and {b} groups are read as resistant to each other, so neither yields easily."
    else:
        explanation = f"{g} and {b} are partially compatible; influence runs more in one direction than the other."
    return KootaResult("Vashya", score, 2.0, g, b, explanation)


def tara_koota(groom: Position, bride: Position) -> KootaResult:
    def remainder(frm: int, to: int) -> int:
        count = ((to - frm) % 27) + 1
        r = count % 9
        return 9 if r == 0 else r

    g_to_b = remainder(groom.nakshatra, bride.nakshatra)
    b_to_g = remainder(bride.nakshatra, groom.nakshatra)

    g_ok = g_to_b not in tables.INAUSPICIOUS_TARA
    b_ok = b_to_g not in tables.INAUSPICIOUS_TARA
    score = 3.0 if (g_ok and b_ok) else (1.5 if (g_ok or b_ok) else 0.0)

    if score == 3.0:
        explanation = "Counted both ways, neither partner falls in an inauspicious tara from the other. Read as mutual wellbeing."
    elif score == 1.5:
        explanation = "The count is favourable in one direction only, so one partner is held to benefit more than the other."
    else:
        explanation = "Both counts land on inauspicious taras, traditionally associated with health and stability concerns."

    return KootaResult(
        "Tara", score, 3.0,
        f"tara {g_to_b} from bride", f"tara {b_to_g} from groom", explanation,
    )


def yoni_koota(groom: Position, bride: Position) -> KootaResult:
    g_animal, g_sex = tables.YONI_BY_NAKSHATRA[groom.nakshatra]
    b_animal, b_sex = tables.YONI_BY_NAKSHATRA[bride.nakshatra]
    score = float(tables.YONI_MATRIX[g_animal][b_animal])

    if score == 4.0:
        explanation = f"Both share the {g_animal} yoni, the strongest reading for physical and temperamental compatibility."
    elif score == 0.0:
        explanation = f"{g_animal} and {b_animal} are classified as mortal opposites, the weakest possible yoni pairing."
    else:
        explanation = f"{g_animal} and {b_animal} are neither the same nor natural enemies, giving a moderate reading."

    return KootaResult(
        "Yoni", score, 4.0,
        f"{g_animal} ({g_sex})", f"{b_animal} ({b_sex})", explanation,
    )


def graha_maitri_koota(groom: Position, bride: Position) -> KootaResult:
    g_lord = tables.RASHI_LORD[groom.rashi]
    b_lord = tables.RASHI_LORD[bride.rashi]

    if g_lord == b_lord:
        return KootaResult(
            "Graha Maitri", 5.0, 5.0, g_lord, b_lord,
            f"Both Moon signs are ruled by {g_lord}, giving identical mental temperament and full marks.",
        )

    def relation(a: str, b: str) -> str:
        if b in tables.PLANET_FRIENDS[a]:
            return "friend"
        if b in tables.PLANET_ENEMIES[a]:
            return "enemy"
        return "neutral"

    r1, r2 = relation(g_lord, b_lord), relation(b_lord, g_lord)
    key = tuple(sorted([r1, r2]))
    score = tables.GRAHA_MAITRI_SCORE[key]

    explanation = (
        f"{g_lord} regards {b_lord} as a {r1}, and {b_lord} regards {g_lord} as a {r2}. "
        "This koota carries five points because it is read as mental and emotional wavelength."
    )
    return KootaResult("Graha Maitri", score, 5.0, g_lord, b_lord, explanation)


def gana_koota(groom: Position, bride: Position) -> KootaResult:
    g = tables.GANA_BY_NAKSHATRA[groom.nakshatra]
    b = tables.GANA_BY_NAKSHATRA[bride.nakshatra]
    score = tables.GANA_MATRIX[g][b]

    if score == 6.0:
        explanation = f"{g} and {b} temperaments are held to sit comfortably together."
    elif score == 0.0:
        explanation = f"A {g} groom with a {b} bride is the classically difficult gana combination, pointing to clashing instincts."
    else:
        explanation = f"{g} and {b} are partially compatible; differences in temperament are workable rather than absent."

    return KootaResult("Gana", score, 6.0, g, b, explanation)


def bhakoot_koota(groom: Position, bride: Position) -> KootaResult:
    g_to_b = ((bride.rashi - groom.rashi) % 12) + 1
    b_to_g = ((groom.rashi - bride.rashi) % 12) + 1

    afflicted = (g_to_b, b_to_g) in tables.BHAKOOT_AFFLICTED_PAIRS
    score = 0.0 if afflicted else 7.0

    if afflicted:
        explanation = (
            f"The Moon signs sit at a {min(g_to_b, b_to_g)}/{max(g_to_b, b_to_g)} distance, "
            "one of the three combinations classically flagged for strain on health and finances. "
            "Many traditions waive this when the sign lords are the same or friendly."
        )
    else:
        explanation = (
            f"The Moon signs sit at a {min(g_to_b, b_to_g)}/{max(g_to_b, b_to_g)} distance, "
            "clear of the three afflicted combinations."
        )

    return KootaResult(
        "Bhakoot", score, 7.0,
        f"{groom.rashi_name} ({tables.RASHIS_EN[groom.rashi]})",
        f"{bride.rashi_name} ({tables.RASHIS_EN[bride.rashi]})",
        explanation,
    )


def nadi_koota(groom: Position, bride: Position) -> KootaResult:
    g = tables.NADI_BY_NAKSHATRA[groom.nakshatra]
    b = tables.NADI_BY_NAKSHATRA[bride.nakshatra]
    score = 0.0 if g == b else 8.0

    if score:
        explanation = f"Different nadis ({g} and {b}), which carries the full eight points, the heaviest single koota."
    else:
        explanation = (
            f"Both fall in {g} nadi. Nadi dosha is the most weighted objection in the system, "
            "costing eight of thirty-six points. It is traditionally waived when the Moon signs "
            "differ and the sign lords are the same, among other exceptions."
        )
    return KootaResult("Nadi", score, 8.0, g, b, explanation)


# --------------------------------------------------------------------------
# Aggregate
# --------------------------------------------------------------------------

KOOTAS = [
    varna_koota, vashya_koota, tara_koota, yoni_koota,
    graha_maitri_koota, gana_koota, bhakoot_koota, nadi_koota,
]


def _verdict(total: float, kootas: list[KootaResult],
             nadi_waivers: list[str], bhakoot_waivers: list[str]) -> str:
    nadi = next(k for k in kootas if k.name == "Nadi")
    bhakoot = next(k for k in kootas if k.name == "Bhakoot")

    if total < 18:
        base = "Below the conventional threshold of 18."
    elif total < 25:
        base = "Acceptable. 18 and above is the usual threshold for proceeding."
    elif total < 32:
        base = "A strong score by conventional reading."
    else:
        base = "A very high score."

    standing, waived = [], []
    if nadi.is_zero:
        (waived if nadi_waivers else standing).append("Nadi dosha")
    if bhakoot.is_zero:
        (waived if bhakoot_waivers else standing).append("Bhakoot dosha")

    parts = [base]
    if standing:
        verb = "stands" if len(standing) == 1 else "stand"
        parts.append(
            f"{' and '.join(standing)} {verb} with no classical exception applying, "
            "which most astrologers weigh separately from the total."
        )
    if waived:
        verb = "appears" if len(waived) == 1 else "appear"
        parts.append(
            f"{' and '.join(waived)} {verb} in the arithmetic but a recognised "
            "exception applies, so it would not normally be treated as blocking."
        )
    return " ".join(parts)


def match(groom_chart: Chart, bride_chart: Chart,
          apply_exceptions: bool = True) -> MatchResult:
    """Score a pair of charts across all eight kootas.

    With apply_exceptions on, the classical waivers for Nadi and Bhakoot dosha
    are checked and reported. The arithmetic is never altered, because the
    36-point total is a fixed convention and quietly inflating it would make the
    number incomparable with every other tool. The exceptions change the verdict
    and appear in their own field instead.
    """
    results = [fn(groom_chart.moon, bride_chart.moon) for fn in KOOTAS]
    total = sum(r.score for r in results)

    nadi_waivers: list[str] = []
    bhakoot_waivers: list[str] = []
    if apply_exceptions:
        from .doshas import nadi_exceptions, bhakoot_exceptions
        if any(k.name == "Nadi" and k.is_zero for k in results):
            nadi_waivers = nadi_exceptions(groom_chart, bride_chart)
        if any(k.name == "Bhakoot" and k.is_zero for k in results):
            bhakoot_waivers = bhakoot_exceptions(groom_chart, bride_chart)

    return MatchResult(
        groom=groom_chart.name,
        bride=bride_chart.name,
        total=total,
        maximum=36.0,
        kootas=results,
        verdict=_verdict(total, results, nadi_waivers, bhakoot_waivers),
        nadi_exceptions=nadi_waivers,
        bhakoot_exceptions=bhakoot_waivers,
    )
