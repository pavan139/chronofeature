"""
Tests for the matching engine.

Three layers:
  1. Table integrity - the classical tables have known shapes and counts.
  2. Score bounds - no koota can ever exceed its maximum or go negative.
  3. Ephemeris accuracy - sidereal positions check out against known values.

If the tables are wrong the scores are wrong, and nobody downstream will catch
it, so the table tests matter more than they look.
"""

import datetime as dt
import random

import pytest

from . import tables
from .ephemeris import BirthData, cast_chart, NAKSHATRA_ARC, _to_position
from .matching import KOOTAS, match
from .doshas import mangal_dosha


# --------------------------------------------------------------------------
# 1. Table integrity
# --------------------------------------------------------------------------

def test_twenty_seven_nakshatras():
    assert len(tables.NAKSHATRAS) == 27
    assert len(tables.NAKSHATRA_DEVANAGARI) == 27
    assert len(set(tables.NAKSHATRAS)) == 27


@pytest.mark.parametrize("table", [
    tables.YONI_BY_NAKSHATRA,
    tables.GANA_BY_NAKSHATRA,
    tables.NADI_BY_NAKSHATRA,
])
def test_nakshatra_tables_are_complete(table):
    assert len(table) == 27


@pytest.mark.parametrize("table", [
    tables.RASHIS, tables.RASHIS_EN, tables.RASHI_LORD,
    tables.VARNA_BY_RASHI, tables.VASHYA_BY_RASHI,
])
def test_rashi_tables_are_complete(table):
    assert len(table) == 12


def test_nadi_splits_evenly():
    """Each of the three nadis governs exactly nine nakshatras."""
    counts = {n: tables.NADI_BY_NAKSHATRA.count(n) for n in {"Adi", "Madhya", "Antya"}}
    assert counts == {"Adi": 9, "Madhya": 9, "Antya": 9}


def test_gana_splits_evenly():
    counts = {g: tables.GANA_BY_NAKSHATRA.count(g) for g in {"Deva", "Manushya", "Rakshasa"}}
    assert counts == {"Deva": 9, "Manushya": 9, "Rakshasa": 9}


def test_varna_follows_elements():
    """Varna is assigned by element, so each varna covers exactly three signs."""
    counts = {v: tables.VARNA_BY_RASHI.count(v) for v in tables.VARNA_RANK}
    assert all(c == 3 for c in counts.values())


def test_yoni_matrix_is_square_and_symmetric():
    animals = set(tables.YONI_MATRIX)
    assert len(animals) == 14
    for a in animals:
        assert set(tables.YONI_MATRIX[a]) == animals
        assert tables.YONI_MATRIX[a][a] == 4, f"{a} against itself must score 4"
        for b in animals:
            assert tables.YONI_MATRIX[a][b] == tables.YONI_MATRIX[b][a], \
                f"yoni matrix asymmetric at {a}/{b}"


def test_yoni_scores_in_range():
    for a, row in tables.YONI_MATRIX.items():
        for b, v in row.items():
            assert 0 <= v <= 4, f"{a}/{b} out of range"


def test_every_nakshatra_has_a_valid_yoni():
    valid = set(tables.YONI_MATRIX)
    for animal, sex in tables.YONI_BY_NAKSHATRA:
        assert animal in valid
        assert sex in {"M", "F"}


def test_planet_cannot_be_friend_and_enemy():
    for planet in tables.PLANET_FRIENDS:
        overlap = tables.PLANET_FRIENDS[planet] & tables.PLANET_ENEMIES[planet]
        assert not overlap, f"{planet} lists {overlap} as both friend and enemy"


def test_all_sign_lords_appear_in_friendship_tables():
    for lord in set(tables.RASHI_LORD):
        assert lord in tables.PLANET_FRIENDS
        assert lord in tables.PLANET_ENEMIES


# --------------------------------------------------------------------------
# 2. Score bounds
# --------------------------------------------------------------------------

def _position_for_nakshatra(index: int):
    """Midpoint of the given nakshatra, so pada and half-sign edges are avoided."""
    return _to_position(index * NAKSHATRA_ARC + NAKSHATRA_ARC / 2)


def test_maximums_sum_to_thirty_six():
    a, b = _position_for_nakshatra(0), _position_for_nakshatra(1)
    assert sum(fn(a, b).maximum for fn in KOOTAS) == 36.0


def test_no_koota_exceeds_its_maximum():
    """Exhaustive over all 27 x 27 nakshatra pairs."""
    for i in range(27):
        for j in range(27):
            a, b = _position_for_nakshatra(i), _position_for_nakshatra(j)
            for fn in KOOTAS:
                r = fn(a, b)
                assert 0 <= r.score <= r.maximum, \
                    f"{r.name} scored {r.score}/{r.maximum} for {i}/{j}"


def test_total_never_exceeds_thirty_six():
    for i in range(27):
        for j in range(27):
            a, b = _position_for_nakshatra(i), _position_for_nakshatra(j)
            total = sum(fn(a, b).score for fn in KOOTAS)
            assert 0 <= total <= 36.0


def test_identical_nakshatra_gives_zero_nadi():
    """Same nakshatra means same nadi, which is always a zero."""
    for i in range(27):
        p = _position_for_nakshatra(i)
        nadi = next(fn for fn in KOOTAS if fn.__name__ == "nadi_koota")
        assert nadi(p, p).score == 0.0


def test_every_koota_explains_itself():
    for i in range(0, 27, 4):
        for j in range(0, 27, 5):
            a, b = _position_for_nakshatra(i), _position_for_nakshatra(j)
            for fn in KOOTAS:
                r = fn(a, b)
                assert len(r.explanation) > 20
                assert r.explanation.strip().endswith((".", "…"))


# --------------------------------------------------------------------------
# 3. Ephemeris accuracy
# --------------------------------------------------------------------------

def test_nakshatra_boundaries_are_exact():
    """Each nakshatra spans exactly 13 degrees 20 minutes."""
    for i in range(27):
        start = _to_position(i * NAKSHATRA_ARC + 0.001)
        end = _to_position((i + 1) * NAKSHATRA_ARC - 0.001)
        assert start.nakshatra == i
        assert end.nakshatra == i


def test_padas_divide_each_nakshatra_into_four():
    for pada in range(4):
        offset = pada * (NAKSHATRA_ARC / 4) + 0.1
        assert _to_position(offset).pada == pada + 1


def test_indian_independence_chart():
    """Midnight 15 August 1947, Delhi.

    This chart is published in enough places to serve as a fixed reference:
    Vrishabha lagna, Moon in Karka at roughly 4 degrees, giving Pushya pada 1.
    If an ephemeris or ayanamsa change ever shifts these, the engine is broken.
    """
    birth = BirthData(
        "reference", dt.date(1947, 8, 15), dt.time(0, 0),
        28.6139, 77.2090, "Asia/Kolkata",
    )
    chart = cast_chart(birth)
    assert chart.ascendant.rashi_name == "Vrishabha"
    assert chart.moon.rashi_name == "Karka"
    assert chart.moon.nakshatra_name == "Pushya"
    assert chart.moon.pada == 1
    assert 93.9 < chart.moon.longitude < 94.1


def test_ayanamsa_choice_changes_the_answer():
    """Different ayanamsas give different sidereal longitudes, by roughly a degree."""
    birth = BirthData(
        "x", dt.date(2000, 1, 1), dt.time(12, 0),
        19.0760, 72.8777, "Asia/Kolkata",
    )
    lahiri = cast_chart(birth, "lahiri").moon.longitude
    raman = cast_chart(birth, "raman").moon.longitude
    assert abs(lahiri - raman) > 0.1


def test_missing_birth_time_suppresses_ascendant():
    birth = BirthData(
        "x", dt.date(1990, 6, 1), dt.time(12, 0),
        19.0760, 72.8777, "Asia/Kolkata", time_known=False,
    )
    chart = cast_chart(birth)
    assert chart.ascendant is None
    result = mangal_dosha(chart)
    assert result.data["checked_ascendant"] is False
    assert "ascendant" not in result.data["afflicted_from"]
    assert "birth time" in result.detail.lower()


def test_timezone_is_actually_applied():
    """Same wall-clock time in Kolkata and London are different instants."""
    kwargs = dict(date=dt.date(2001, 5, 20), time=dt.time(6, 0), latitude=0.0, longitude=0.0)
    ist = cast_chart(BirthData("a", timezone="Asia/Kolkata", **kwargs))
    utc = cast_chart(BirthData("b", timezone="Europe/London", **kwargs))
    assert abs(ist.moon.longitude - utc.moon.longitude) > 0.5


def test_mars_house_count_is_one_based():
    """A planet in the reference sign itself is house 1, not house 0."""
    from .ephemeris import house_from
    p = _position_for_nakshatra(0)
    assert house_from(p, p) == 1


# --------------------------------------------------------------------------
# End to end
# --------------------------------------------------------------------------

def test_random_charts_always_produce_valid_matches():
    rng = random.Random(20260914)
    for _ in range(200):
        def rand_birth(name):
            return BirthData(
                name,
                dt.date(rng.randint(1970, 2005), rng.randint(1, 12), rng.randint(1, 28)),
                dt.time(rng.randint(0, 23), rng.randint(0, 59)),
                rng.uniform(8.0, 34.0), rng.uniform(68.0, 92.0),
                "Asia/Kolkata",
            )
        result = match(cast_chart(rand_birth("g")), cast_chart(rand_birth("b")))
        assert 0 <= result.total <= 36
        assert 0 <= result.percentage <= 100
        assert len(result.kootas) == 8
        assert result.verdict
        assert result.to_dict()["kootas"][0]["name"] == "Varna"


# ==========================================================================
# Extended engine: grahas, navamsa, dashas, doshas, porutham, geocoding
# ==========================================================================

from .ephemeris import GRAHA_ORDER, EXALTATION, DEBILITATION, _navamsa_sign, NAVAMSA_ARC
from .dasha import (
    vimshottari, current_dasha, balance_at_birth, DASHA_SEQUENCE,
    TOTAL_YEARS, NAKSHATRA_LORDS,
)
from .doshas import mangal_dosha, kaal_sarp_dosha, sade_sati, nadi_exceptions
from .porutham import (
    PORUTHAMS, match_porutham, RAJJU_BY_NAKSHATRA, VEDHA_PARTNER,
)

REFERENCE = BirthData("ref", dt.date(1992, 3, 14), dt.time(7, 25),
                      17.3850, 78.4867, "Asia/Kolkata")


# --- Grahas ---------------------------------------------------------------

def test_all_nine_grahas_present():
    chart = cast_chart(REFERENCE)
    assert set(chart.grahas) == set(GRAHA_ORDER)
    assert len(GRAHA_ORDER) == 9


def test_ketu_is_exactly_opposite_rahu():
    chart = cast_chart(REFERENCE)
    rahu = chart.grahas["Rahu"].position.longitude
    ketu = chart.grahas["Ketu"].position.longitude
    assert abs(((ketu - rahu) % 360.0) - 180.0) < 1e-6


def test_nodes_are_always_retrograde():
    chart = cast_chart(REFERENCE)
    assert chart.grahas["Rahu"].retrograde
    assert chart.grahas["Ketu"].retrograde


def test_sun_and_moon_are_never_retrograde():
    for year in (1970, 1985, 2000, 2015):
        chart = cast_chart(BirthData("x", dt.date(year, 6, 15), dt.time(9, 0),
                                     19.07, 72.87, "Asia/Kolkata"))
        assert not chart.grahas["Sun"].retrograde
        assert not chart.grahas["Moon"].retrograde


def test_sun_is_never_combust_with_itself():
    assert "Sun" not in __import__(
        "gunamilan.ephemeris", fromlist=["COMBUSTION_ORB"]
    ).COMBUSTION_ORB


def test_debilitation_is_opposite_exaltation():
    for planet, exalt in EXALTATION.items():
        assert DEBILITATION[planet] == (exalt + 6) % 12


def test_known_dignities_in_reference_chart():
    """Mars exalted in Capricorn, Mercury debilitated in Pisces, Saturn in own sign."""
    chart = cast_chart(REFERENCE)
    assert chart.grahas["Mars"].dignity == "exalted"
    assert chart.grahas["Mercury"].dignity == "debilitated"
    assert chart.grahas["Saturn"].dignity == "own sign"


def test_houses_are_one_to_twelve():
    chart = cast_chart(REFERENCE)
    for g in chart.grahas.values():
        assert 1 <= g.house <= 12


def test_houses_are_zero_without_birth_time():
    chart = cast_chart(BirthData("x", dt.date(1990, 1, 1), dt.time(12, 0),
                                 19.07, 72.87, "Asia/Kolkata", time_known=False))
    assert chart.ascendant is None
    assert all(g.house == 0 for g in chart.grahas.values())


# --- Navamsa --------------------------------------------------------------

def test_navamsa_has_108_divisions():
    seen = {_navamsa_sign(i * NAVAMSA_ARC + 0.1) for i in range(108)}
    assert seen == set(range(12))


def test_navamsa_movable_signs_start_from_themselves():
    """Aries, Cancer, Libra and Capricorn begin their navamsa series at themselves."""
    for sign in (0, 3, 6, 9):
        assert _navamsa_sign(sign * 30 + 0.1) == sign


def test_navamsa_fixed_signs_start_from_the_ninth():
    """Taurus, Leo, Scorpio and Aquarius begin nine signs along."""
    for sign in (1, 4, 7, 10):
        assert _navamsa_sign(sign * 30 + 0.1) == (sign + 8) % 12


def test_navamsa_dual_signs_start_from_the_fifth():
    """Gemini, Virgo, Sagittarius and Pisces begin five signs along."""
    for sign in (2, 5, 8, 11):
        assert _navamsa_sign(sign * 30 + 0.1) == (sign + 4) % 12


# --- Vimshottari dasha ----------------------------------------------------

def test_dasha_cycle_totals_120_years():
    assert TOTAL_YEARS == 120
    assert len(DASHA_SEQUENCE) == 9


def test_nakshatra_lords_cycle_three_times():
    assert len(NAKSHATRA_LORDS) == 27
    assert NAKSHATRA_LORDS[:9] == NAKSHATRA_LORDS[9:18] == NAKSHATRA_LORDS[18:]


def test_balance_at_birth_is_a_fraction():
    for day in range(1, 29, 4):
        chart = cast_chart(BirthData("x", dt.date(1990, 6, day), dt.time(9, 0),
                                     19.07, 72.87, "Asia/Kolkata"))
        lord, balance = balance_at_birth(chart)
        assert lord in dict(DASHA_SEQUENCE)
        assert 0.0 < balance <= 1.0


def test_dashas_are_contiguous_and_span_120_years():
    chart = cast_chart(REFERENCE)
    periods = vimshottari(chart, depth=1)
    assert periods[0].start == chart.birth.date
    for earlier, later in zip(periods, periods[1:]):
        assert earlier.end == later.start, "gap or overlap between mahadashas"
    span = (periods[-1].end - periods[0].start).days / 365.25636
    assert 119.5 < span < 120.5


def test_antardashas_fill_their_mahadasha_exactly():
    chart = cast_chart(REFERENCE)
    for maha in vimshottari(chart, depth=2)[:4]:
        assert len(maha.children) == 9
        assert maha.children[0].start == maha.start
        assert maha.children[-1].end == maha.end
        for a, b in zip(maha.children, maha.children[1:]):
            assert a.end == b.start


def test_first_antardasha_is_ruled_by_its_mahadasha_lord():
    chart = cast_chart(REFERENCE)
    for maha in vimshottari(chart, depth=2)[:5]:
        assert maha.children[0].lord == maha.lord


def test_current_dasha_chain_is_nested():
    chart = cast_chart(REFERENCE)
    chain = current_dasha(chart, dt.date(2026, 6, 1))
    assert len(chain) >= 2
    for outer, inner in zip(chain, chain[1:]):
        assert outer.start <= inner.start and inner.end <= outer.end
        assert inner.level == outer.level + 1


# --- Doshas ---------------------------------------------------------------

def test_dosha_reports_are_well_formed():
    chart = cast_chart(REFERENCE)
    for report in (mangal_dosha(chart), kaal_sarp_dosha(chart), sade_sati(chart)):
        assert report.severity in {"none", "mild", "moderate", "severe"}
        assert len(report.detail) > 20
        assert (report.severity == "none") or report.present or report.name == "Sade Sati"


def test_mangal_absent_means_no_severity():
    """A chart with no affliction must not carry a severity grade."""
    rng = random.Random(7)
    for _ in range(40):
        chart = cast_chart(BirthData(
            "x", dt.date(rng.randint(1960, 2010), rng.randint(1, 12), rng.randint(1, 28)),
            dt.time(rng.randint(0, 23), rng.randint(0, 59)),
            19.07, 72.87, "Asia/Kolkata"))
        report = mangal_dosha(chart)
        if not report.present:
            assert report.severity == "none"
            assert report.cancellations == []


def test_kaal_sarp_requires_all_seven_on_one_side():
    rng = random.Random(11)
    for _ in range(60):
        chart = cast_chart(BirthData(
            "x", dt.date(rng.randint(1960, 2010), rng.randint(1, 12), rng.randint(1, 28)),
            dt.time(12, 0), 19.07, 72.87, "Asia/Kolkata"))
        report = kaal_sarp_dosha(chart)
        if report.present and report.severity == "moderate":
            assert "All seven" in report.detail


def test_nadi_exceptions_only_fire_on_real_grounds():
    chart = cast_chart(REFERENCE)
    assert nadi_exceptions(chart, chart), "identical charts share a sign lord"


# --- Porutham -------------------------------------------------------------

def test_rajju_covers_all_27_nakshatras():
    assert len(RAJJU_BY_NAKSHATRA) == 27
    counts = {r: RAJJU_BY_NAKSHATRA.count(r) for r in set(RAJJU_BY_NAKSHATRA)}
    assert counts == {"Paada": 6, "Jaanu": 6, "Naabhi": 6, "Kanta": 6, "Siro": 3}


def test_vedha_pairs_are_symmetric():
    for a, b in VEDHA_PARTNER.items():
        assert VEDHA_PARTNER[b] == a
        assert a != b


def test_ten_poruthams_exist():
    assert len(PORUTHAMS) == 10


def test_same_nakshatra_always_fails_rajju():
    """Identical stars share a rajju, which is the decisive South Indian objection."""
    for i in range(27):
        p = _position_for_nakshatra(i)
        rajju = next(fn for fn in PORUTHAMS if fn.__name__ == "rajju_porutham")
        assert not rajju(p, p).passed


def test_porutham_results_are_complete():
    for i in range(0, 27, 3):
        for j in range(0, 27, 4):
            a, b = _position_for_nakshatra(i), _position_for_nakshatra(j)
            for fn in PORUTHAMS:
                r = fn(a, b)
                assert isinstance(r.passed, bool)
                assert r.weight in {"essential", "supporting"}
                assert len(r.explanation) > 20


def test_porutham_match_counts_correctly():
    chart = cast_chart(REFERENCE)
    other = cast_chart(BirthData("o", dt.date(1994, 11, 2), dt.time(14, 10),
                                 19.076, 72.878, "Asia/Kolkata"))
    result = match_porutham(chart, other)
    assert result.total == 10
    assert result.passed == sum(1 for p in result.poruthams if p.passed)
    assert 0 <= result.passed <= 10


# --- Geocoding ------------------------------------------------------------

def test_historic_city_names_resolve():
    from .geocode import geocode
    for query, expected in [
        ("Bombay", "Mumbai"), ("Calcutta", "Kolkata"), ("Madras", "Chennai"),
        ("Bangalore", "Bengaluru"), ("Trivandrum", "Thiruvananthapuram"),
        ("Poona", "Pune"), ("Benares", "Varanasi"),
    ]:
        assert geocode(query).name == expected, query


def test_geocode_returns_a_usable_timezone():
    from .geocode import geocode
    from zoneinfo import ZoneInfo
    for query in ("Hyderabad", "Edison, New Jersey", "Southall"):
        place = geocode(query)
        ZoneInfo(place.timezone)  # raises if the name is not a real zone


def test_geocode_is_diacritic_insensitive():
    from .geocode import geocode
    assert geocode("sitapur").name == geocode("Sītāpur").name


def test_missing_place_suggests_alternatives():
    from .geocode import geocode, PlaceNotFound
    with pytest.raises(PlaceNotFound):
        geocode("Zzqxvillestan")


def test_chart_can_be_built_straight_from_a_place_name():
    from .geocode import geocode
    place = geocode("Chennai")
    birth = BirthData.from_place("x", dt.date(1990, 4, 4), dt.time(5, 30), place)
    chart = cast_chart(birth)
    assert chart.ascendant is not None
    assert chart.birth.timezone == "Asia/Kolkata"
