"""
Vimshottari dasha.

The 120-year planetary period cycle, which is what turns a static chart into a
timeline. Every paid report leans on this: people want to know when, not just
what.

The starting period is fixed by how far the Moon has travelled through its
nakshatra at birth. That makes dashas acutely sensitive to birth time; ten
minutes of error can move a period boundary by weeks. The code exposes that
sensitivity rather than hiding it.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from .ephemeris import Chart, NAKSHATRA_ARC

# The cycle, in order, totalling 120 years.
DASHA_SEQUENCE = [
    ("Ketu", 7), ("Venus", 20), ("Sun", 6), ("Moon", 10), ("Mars", 7),
    ("Rahu", 18), ("Jupiter", 16), ("Saturn", 19), ("Mercury", 17),
]

TOTAL_YEARS = sum(years for _, years in DASHA_SEQUENCE)  # 120

# A sidereal year in days, the unit classical dasha arithmetic assumes.
SIDEREAL_YEAR_DAYS = 365.25636

LORD_INDEX = {name: i for i, (name, _) in enumerate(DASHA_SEQUENCE)}
DASHA_YEARS = dict(DASHA_SEQUENCE)

# The 27 nakshatras cycle through the nine lords three times.
NAKSHATRA_LORDS = [DASHA_SEQUENCE[i % 9][0] for i in range(27)]

# What each period is traditionally associated with, used to caption a timeline.
DASHA_THEMES = {
    "Ketu": "detachment, endings and spiritual turns",
    "Venus": "relationships, comfort, art and material ease",
    "Sun": "authority, recognition, father and self-assertion",
    "Moon": "emotional life, mother, home and public contact",
    "Mars": "energy, conflict, property and siblings",
    "Rahu": "ambition, foreign contact and sudden change",
    "Jupiter": "learning, children, counsel and expansion",
    "Saturn": "labour, delay, discipline and consolidation",
    "Mercury": "communication, commerce, study and negotiation",
}


@dataclass(frozen=True)
class DashaPeriod:
    lord: str
    start: dt.date
    end: dt.date
    level: int                       # 1 maha, 2 antar, 3 pratyantar
    parent: str | None = None
    children: tuple["DashaPeriod", ...] = ()

    @property
    def duration_days(self) -> int:
        return (self.end - self.start).days

    @property
    def label(self) -> str:
        if self.parent:
            return f"{self.parent}\u2013{self.lord}"
        return self.lord

    def contains(self, when: dt.date) -> bool:
        return self.start <= when < self.end

    def to_dict(self, depth: int = 1) -> dict:
        out = {
            "lord": self.lord,
            "label": self.label,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "level": self.level,
            "theme": DASHA_THEMES[self.lord],
        }
        if depth > 1 and self.children:
            out["periods"] = [c.to_dict(depth - 1) for c in self.children]
        return out


def _add_years(start: dt.date, years: float) -> dt.date:
    """Advance by a fractional number of sidereal years."""
    return start + dt.timedelta(days=years * SIDEREAL_YEAR_DAYS)


def balance_at_birth(chart: Chart) -> tuple[str, float]:
    """The ruling lord at birth and the fraction of its period still unspent."""
    moon = chart.moon
    lord = NAKSHATRA_LORDS[moon.nakshatra]
    traversed = (moon.longitude % NAKSHATRA_ARC) / NAKSHATRA_ARC
    return lord, (1.0 - traversed)


def _subdivide(lord: str, start: dt.date, end: dt.date,
               level: int, depth: int) -> tuple[DashaPeriod, ...]:
    """Split a period into sub-periods in the same 120-year proportions."""
    if depth <= 0:
        return ()

    span_days = (end - start).days
    if span_days <= 0:
        return ()

    order = LORD_INDEX[lord]
    children, cursor = [], start
    for offset in range(9):
        sub_lord, sub_years = DASHA_SEQUENCE[(order + offset) % 9]
        sub_days = span_days * sub_years / TOTAL_YEARS
        sub_end = cursor + dt.timedelta(days=sub_days)
        if offset == 8:
            sub_end = end  # absorb rounding into the final sub-period
        children.append(DashaPeriod(
            lord=sub_lord, start=cursor, end=sub_end, level=level, parent=lord,
            children=_subdivide(sub_lord, cursor, sub_end, level + 1, depth - 1),
        ))
        cursor = sub_end
    return tuple(children)


def vimshottari(chart: Chart, depth: int = 2,
                span_years: int = 120) -> list[DashaPeriod]:
    """Full mahadasha sequence from birth.

    depth=1 gives mahadashas only, 2 adds antardashas, 3 adds pratyantardashas.
    Depth 3 produces 729 periods per mahadasha, so only request it for a single
    period the caller actually intends to display.
    """
    lord, remaining = balance_at_birth(chart)
    birth_date = chart.birth.date

    periods: list[DashaPeriod] = []
    start = birth_date
    order = LORD_INDEX[lord]
    elapsed = 0.0

    for offset in range(9 * (span_years // TOTAL_YEARS + 1)):
        current, full_years = DASHA_SEQUENCE[(order + offset) % 9]
        years = full_years * remaining if offset == 0 else full_years
        if elapsed + years > span_years:
            years = span_years - elapsed
        if years <= 0:
            break
        end = _add_years(start, years)
        periods.append(DashaPeriod(
            lord=current, start=start, end=end, level=1,
            children=_subdivide(current, start, end, 2, depth - 1),
        ))
        start = end
        elapsed += years
        if elapsed >= span_years:
            break

    return periods


def current_dasha(chart: Chart, when: dt.date | None = None) -> list[DashaPeriod]:
    """The nested chain of periods running on a given date, outermost first."""
    when = when or dt.date.today()
    chain: list[DashaPeriod] = []
    candidates = vimshottari(chart, depth=3)

    while candidates:
        match = next((p for p in candidates if p.contains(when)), None)
        if match is None:
            break
        chain.append(match)
        candidates = list(match.children)
    return chain


def describe_current(chart: Chart, when: dt.date | None = None) -> str:
    """One sentence naming the running periods and what they govern."""
    chain = current_dasha(chart, when)
    if not chain:
        return "The requested date falls outside the computed 120-year cycle."

    maha = chain[0]
    text = (
        f"{maha.lord} mahadasha, running to {maha.end.strftime('%B %Y')}, "
        f"which governs {DASHA_THEMES[maha.lord]}."
    )
    if len(chain) > 1:
        antar = chain[1]
        text += (
            f" Within it, {antar.lord} antardasha runs to "
            f"{antar.end.strftime('%B %Y')}."
        )
    return text


def marriage_windows(chart: Chart, from_date: dt.date | None = None,
                     years_ahead: int = 12) -> list[DashaPeriod]:
    """Antardashas classically associated with marriage in the years ahead.

    Venus and Jupiter periods, and periods ruled by the lords of the 7th house,
    are the conventional markers. This surfaces candidates for an astrologer to
    weigh; it does not predict a date, and the report wording should say so.
    """
    from .tables import RASHI_LORD

    start = from_date or dt.date.today()
    horizon = start + dt.timedelta(days=int(years_ahead * SIDEREAL_YEAR_DAYS))

    markers = {"Venus", "Jupiter"}
    if chart.ascendant:
        seventh_sign = (chart.ascendant.rashi + 6) % 12
        markers.add(RASHI_LORD[seventh_sign])

    out = []
    for maha in vimshottari(chart, depth=2):
        for antar in maha.children:
            if antar.end < start or antar.start > horizon:
                continue
            if antar.lord in markers or maha.lord in markers:
                out.append(antar)
    return out
