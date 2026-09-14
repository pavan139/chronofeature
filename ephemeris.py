"""
Chart computation.

Wraps Swiss Ephemeris and returns sidereal positions for all nine grahas, the
ascendant, whole-sign houses, and the Navamsa (D9) divisional chart. Lahiri
ayanamsa is the default because it is what Indian practice and the Indian
government calendar use.

Birth time matters enormously here. The Moon moves roughly one nakshatra every
21 hours and the ascendant changes sign every two hours, so an hour of error can
change the nakshatra, four of the eight kootas, and the entire house structure.
Callers should surface time uncertainty rather than hiding it.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from zoneinfo import ZoneInfo

import swisseph as swe

from . import tables

NAKSHATRA_ARC = 360.0 / 27.0   # 13 degrees 20 minutes
RASHI_ARC = 30.0
PADA_ARC = NAKSHATRA_ARC / 4.0
NAVAMSA_ARC = RASHI_ARC / 9.0  # 3 degrees 20 minutes

AYANAMSA = {
    "lahiri": swe.SIDM_LAHIRI,
    "raman": swe.SIDM_RAMAN,
    "krishnamurti": swe.SIDM_KRISHNAMURTI,
    "fagan_bradley": swe.SIDM_FAGAN_BRADLEY,
}

# Swiss Ephemeris body codes for the seven visible grahas. Rahu and Ketu are
# derived from the lunar node rather than requested directly.
GRAHA_CODES = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mars": swe.MARS,
    "Mercury": swe.MERCURY,
    "Jupiter": swe.JUPITER,
    "Venus": swe.VENUS,
    "Saturn": swe.SATURN,
}

GRAHA_ORDER = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus",
               "Saturn", "Rahu", "Ketu"]

# Degrees from the Sun within which a graha is held to be combust.
COMBUSTION_ORB = {
    "Moon": 12.0, "Mars": 17.0, "Mercury": 14.0,
    "Jupiter": 11.0, "Venus": 10.0, "Saturn": 15.0,
}

# Exaltation signs, 0-based. Debilitation is the opposite sign.
EXALTATION = {"Sun": 0, "Moon": 1, "Mars": 9, "Mercury": 5,
              "Jupiter": 3, "Venus": 11, "Saturn": 6}
DEBILITATION = {p: (s + 6) % 12 for p, s in EXALTATION.items()}

OWN_SIGNS = {
    "Sun": {4}, "Moon": {3}, "Mars": {0, 7}, "Mercury": {2, 5},
    "Jupiter": {8, 11}, "Venus": {1, 6}, "Saturn": {9, 10},
}


@dataclass(frozen=True)
class BirthData:
    """Everything needed to cast a chart."""

    name: str
    date: dt.date
    time: dt.time
    latitude: float
    longitude: float
    timezone: str = "Asia/Kolkata"
    time_known: bool = True
    place_label: str = ""

    def to_utc(self) -> dt.datetime:
        local = dt.datetime.combine(self.date, self.time, ZoneInfo(self.timezone))
        return local.astimezone(dt.timezone.utc)

    @classmethod
    def from_place(cls, name, date, time, place, time_known=True) -> "BirthData":
        """Build from a geocode.Place, which carries coordinates and timezone."""
        return cls(
            name=name, date=date, time=time or dt.time(12, 0),
            latitude=place.latitude, longitude=place.longitude,
            timezone=place.timezone, time_known=time_known,
            place_label=place.label,
        )


@dataclass(frozen=True)
class Position:
    """A sidereal position broken into the divisions Vedic astrology uses."""

    longitude: float       # sidereal, 0-360
    rashi: int             # 0-based, Aries = 0
    rashi_name: str
    nakshatra: int         # 0-based, Ashwini = 0
    nakshatra_name: str
    pada: int              # 1-4
    degrees_in_rashi: float
    navamsa: int           # 0-based sign of the D9 chart

    @property
    def rashi_number(self) -> int:
        """1-based sign number, which is how classical rules are written."""
        return self.rashi + 1

    @property
    def navamsa_name(self) -> str:
        return tables.RASHIS[self.navamsa]

    def format_degrees(self) -> str:
        d = int(self.degrees_in_rashi)
        m = int((self.degrees_in_rashi - d) * 60)
        s = int(round(((self.degrees_in_rashi - d) * 60 - m) * 60))
        if s == 60:
            s, m = 0, m + 1
        return f"{d}\u00b0{m:02d}'{s:02d}\""


@dataclass(frozen=True)
class Graha:
    """A planet with the dignities a reading actually refers to."""

    name: str
    position: Position
    house: int              # whole-sign house from the ascendant, 0 if unknown
    retrograde: bool
    combust: bool
    dignity: str            # exalted, debilitated, own sign, node or neutral

    @property
    def rashi_name(self) -> str:
        return self.position.rashi_name

    @property
    def nakshatra_name(self) -> str:
        return self.position.nakshatra_name


@dataclass(frozen=True)
class Chart:
    name: str
    birth: BirthData
    grahas: dict[str, Graha]
    ascendant: Position | None
    time_known: bool
    ayanamsa: str
    julian_day: float = 0.0

    @property
    def moon(self) -> Position:
        return self.grahas["Moon"].position

    @property
    def sun(self) -> Position:
        return self.grahas["Sun"].position

    @property
    def mars(self) -> Position:
        return self.grahas["Mars"].position

    def house_of(self, graha: str) -> int:
        return self.grahas[graha].house

    def grahas_in_house(self, house: int) -> list[str]:
        return [g.name for g in self.grahas.values() if g.house == house]


def _julian_day(when_utc: dt.datetime) -> float:
    hour = when_utc.hour + when_utc.minute / 60.0 + when_utc.second / 3600.0
    return swe.julday(when_utc.year, when_utc.month, when_utc.day, hour, swe.GREG_CAL)


def _navamsa_sign(longitude: float) -> int:
    """D9 sign for a sidereal longitude.

    The zodiac holds 108 navamsas of 3 degrees 20 minutes. Numbering them from
    0 degrees Aries and taking the remainder modulo 12 reproduces the classical
    rule exactly: movable signs begin their navamsa series from themselves,
    fixed signs from the ninth sign, dual signs from the fifth.
    """
    return int(longitude // NAVAMSA_ARC) % 12


def _to_position(sidereal_longitude: float) -> Position:
    lon = sidereal_longitude % 360.0
    rashi = int(lon // RASHI_ARC)
    nak = int(lon // NAKSHATRA_ARC)
    pada = int((lon % NAKSHATRA_ARC) // PADA_ARC) + 1
    return Position(
        longitude=lon,
        rashi=rashi,
        rashi_name=tables.RASHIS[rashi],
        nakshatra=nak,
        nakshatra_name=tables.NAKSHATRAS[nak],
        pada=pada,
        degrees_in_rashi=lon % RASHI_ARC,
        navamsa=_navamsa_sign(lon),
    )


def _angular_separation(a: float, b: float) -> float:
    diff = abs(a - b) % 360.0
    return min(diff, 360.0 - diff)


def _dignity(name: str, rashi: int) -> str:
    if name in ("Rahu", "Ketu"):
        return "node"
    if rashi == EXALTATION.get(name):
        return "exalted"
    if rashi == DEBILITATION.get(name):
        return "debilitated"
    if rashi in OWN_SIGNS.get(name, set()):
        return "own sign"
    return "neutral"


def cast_chart(birth: BirthData, ayanamsa: str = "lahiri",
               true_node: bool = True) -> Chart:
    """Compute sidereal positions for all nine grahas plus the ascendant.

    When the birth time is unknown, pass time_known=False and a noon time. The
    Moon position is then approximate and the ascendant is meaningless, so it is
    returned as None and all house numbers are zero rather than being presented
    as confident wrong answers.
    """
    if ayanamsa not in AYANAMSA:
        raise ValueError(f"unknown ayanamsa {ayanamsa!r}; choose from {sorted(AYANAMSA)}")

    swe.set_sid_mode(AYANAMSA[ayanamsa], 0, 0)
    jd = _julian_day(birth.to_utc())
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED

    raw: dict[str, tuple[float, float]] = {}
    for name, code in GRAHA_CODES.items():
        values = swe.calc_ut(jd, code, flags)[0]
        raw[name] = (values[0], values[3])  # longitude, daily motion

    node_code = swe.TRUE_NODE if true_node else swe.MEAN_NODE
    node = swe.calc_ut(jd, node_code, flags)[0]
    raw["Rahu"] = (node[0], node[3])
    raw["Ketu"] = ((node[0] + 180.0) % 360.0, node[3])

    ascendant = None
    if birth.time_known:
        # 'W' is whole-sign houses, which is what Indian practice assumes when
        # counting houses from the lagna.
        _, ascmc = swe.houses_ex(jd, birth.latitude, birth.longitude, b"W", flags)
        ascendant = _to_position(ascmc[0])

    sun_longitude = raw["Sun"][0]
    grahas: dict[str, Graha] = {}
    for name in GRAHA_ORDER:
        longitude, speed = raw[name]
        pos = _to_position(longitude)
        # The nodes are always retrograde; for the rest, negative daily motion.
        retrograde = name in ("Rahu", "Ketu") or speed < 0
        orb = COMBUSTION_ORB.get(name)
        combust = bool(orb and _angular_separation(longitude, sun_longitude) < orb)
        house = (((pos.rashi - ascendant.rashi) % 12) + 1) if ascendant else 0
        grahas[name] = Graha(
            name=name, position=pos, house=house, retrograde=retrograde,
            combust=combust, dignity=_dignity(name, pos.rashi),
        )

    return Chart(
        name=birth.name, birth=birth, grahas=grahas, ascendant=ascendant,
        time_known=birth.time_known, ayanamsa=ayanamsa, julian_day=jd,
    )


def house_from(reference: Position, planet: Position) -> int:
    """Whole-sign house number (1-12) of `planet` counted from `reference`."""
    return ((planet.rashi - reference.rashi) % 12) + 1


def transit_positions(when: dt.datetime, ayanamsa: str = "lahiri") -> dict[str, Position]:
    """Sidereal positions at a moment, used for transit work such as Sade Sati."""
    swe.set_sid_mode(AYANAMSA[ayanamsa], 0, 0)
    if when.tzinfo is None:
        when = when.replace(tzinfo=dt.timezone.utc)
    jd = _julian_day(when.astimezone(dt.timezone.utc))
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL

    out = {}
    for name, code in GRAHA_CODES.items():
        out[name] = _to_position(swe.calc_ut(jd, code, flags)[0][0])
    node = swe.calc_ut(jd, swe.TRUE_NODE, flags)[0][0]
    out["Rahu"] = _to_position(node)
    out["Ketu"] = _to_position((node + 180.0) % 360.0)
    return out
