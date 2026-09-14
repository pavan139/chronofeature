"""
Offline geocoding.

Users type "Sitapur", "sitapur up", "Bombay" or "Trivandrum, Kerala". They do
not type coordinates. This resolves all of those against the bundled database
with no network call, which matters because geocoding APIs charge per request
and a free tool has to cost nothing per use.

Ranking is by population, because a name collision almost always means the user
meant the larger place. Where it is genuinely ambiguous the caller gets the full
candidate list and should ask rather than guess: picking the wrong Sitapur moves
the birth coordinates by hundreds of kilometres and changes the ascendant.
"""

from __future__ import annotations

import sqlite3
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import os

DB_PATH = Path(os.environ.get("PLACES_DB", str(Path(__file__).parent / "data" / "places.db")))

# Trailing words users add that are not part of the place name.
NOISE_WORDS = {"india", "bharat", "city", "town", "village", "district", "dist"}

# Common state shorthand.
STATE_ALIASES = {
    "up": "uttar pradesh", "mp": "madhya pradesh", "ap": "andhra pradesh",
    "tn": "tamil nadu", "wb": "west bengal", "hp": "himachal pradesh",
    "jk": "jammu and kashmir", "uk": "uttarakhand", "mh": "maharashtra",
    "ka": "karnataka", "kl": "kerala", "gj": "gujarat", "rj": "rajasthan",
    "pb": "punjab", "hr": "haryana", "br": "bihar", "od": "odisha",
    "as": "assam", "cg": "chhattisgarh", "jh": "jharkhand", "ts": "telangana",
    "ncr": "delhi", "nct": "delhi",
}


@dataclass(frozen=True)
class Place:
    name: str
    region: str
    country: str
    latitude: float
    longitude: float
    timezone: str
    population: int

    @property
    def label(self) -> str:
        parts = [self.name]
        if self.region and self.region != self.name:
            parts.append(self.region)
        if self.country != "IN":
            parts.append(self.country)
        return ", ".join(parts)

    def describe(self) -> str:
        if self.population >= 1000:
            return f"{self.label} (population {self.population:,})"
        return f"{self.label} (village)"


class PlaceNotFound(LookupError):
    """Raised when nothing matches. Carries near-misses so callers can suggest."""

    def __init__(self, query: str, suggestions: list[Place] | None = None):
        self.query = query
        self.suggestions = suggestions or []
        hint = ""
        if self.suggestions:
            hint = " Did you mean: " + "; ".join(p.label for p in self.suggestions[:3]) + "?"
        super().__init__(f"No place matching {query!r}.{hint}")


def fold(text: str) -> str:
    # Keep vowel signs and other meaningful marks in Indic scripts.
    # Only Latin letters lose diacritics, preserving legacy Sitapur lookup.
    parts = []
    for char in unicodedata.normalize("NFC", text):
        if "LATIN" in unicodedata.name(char, ""):
            parts.append("".join(c for c in unicodedata.normalize("NFD", char)
                                 if not unicodedata.combining(c)))
        else:
            parts.append(char)
    return " ".join("".join(parts).casefold().replace("-", " ").replace(".", "").split())


@lru_cache(maxsize=1)
def _connection() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Place database missing at {DB_PATH}. Run build_places.py first."
        )
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _to_place(row: sqlite3.Row) -> Place:
    return Place(
        name=row["name"], region=row["region"], country=row["country"],
        latitude=row["lat"], longitude=row["lon"], timezone=row["tz"],
        population=row["population"],
    )


def _split_query(query: str) -> tuple[str, str | None]:
    """Separate 'Sitapur, Uttar Pradesh' into the place and its region hint."""
    if "," in query:
        head, _, tail = query.partition(",")
        region = fold(tail)
        return fold(head), STATE_ALIASES.get(region, region) or None

    words = fold(query).split()
    while words and words[-1] in NOISE_WORDS:
        words.pop()
    # A trailing state abbreviation, as in "sitapur up".
    if len(words) > 1 and words[-1] in STATE_ALIASES:
        return " ".join(words[:-1]), STATE_ALIASES[words[-1]]
    return " ".join(words), None


def _rank(rows: list[sqlite3.Row], region_hint: str | None) -> list[Place]:
    places = [_to_place(r) for r in rows]
    if region_hint:
        matching = [p for p in places if fold(p.region) == region_hint]
        if matching:
            places = matching
    places.sort(key=lambda p: -p.population)
    return places


def search(query: str, limit: int = 10) -> list[Place]:
    """All candidates for a query, best first. Empty list if nothing matches."""
    name, region_hint = _split_query(query)
    if not name:
        return []

    conn = _connection()
    sql = """
        SELECT DISTINCT p.* FROM names n
        JOIN places p ON p.id = n.place_id
        WHERE n.folded = ?
        LIMIT 200
    """
    rows = conn.execute(sql, (name,)).fetchall()

    if not rows:
        # Prefix fallback: "tiruchirapp" should still find Tiruchirappalli.
        sql = """
            SELECT DISTINCT p.* FROM names n
            JOIN places p ON p.id = n.place_id
            WHERE n.folded >= ? AND n.folded < ?
            ORDER BY p.population DESC
            LIMIT 200
        """
        rows = conn.execute(sql, (name, name + "\uffff")).fetchall()

    return _rank(rows, region_hint)[:limit]


def geocode(query: str) -> Place:
    """The single best match, or PlaceNotFound carrying suggestions."""
    results = search(query)
    if not results:
        raise PlaceNotFound(query, _near_misses(query))
    return results[0]


def is_ambiguous(query: str, threshold: float = 0.35) -> list[Place]:
    """Candidates worth asking the user about.

    Returns an empty list when the top hit clearly dominates. A second place
    whose population is within `threshold` of the first, or any collision
    between villages with no population data, is worth a disambiguation prompt
    rather than a silent guess.
    """
    results = search(query, limit=5)
    if len(results) < 2:
        return []
    top = results[0]
    if top.population == 0:
        return results
    rivals = [p for p in results[1:] if p.population >= top.population * threshold]
    return [top, *rivals] if rivals else []


def _near_misses(query: str, limit: int = 5) -> list[Place]:
    """Cheap suggestions for a failed lookup: progressively shorter prefixes."""
    name, _ = _split_query(query)
    conn = _connection()
    for cut in range(len(name) - 1, 2, -1):
        prefix = name[:cut]
        rows = conn.execute(
            """
            SELECT DISTINCT p.* FROM names n
            JOIN places p ON p.id = n.place_id
            WHERE n.folded >= ? AND n.folded < ?
            ORDER BY p.population DESC
            LIMIT ?
            """,
            (prefix, prefix + "\uffff", limit),
        ).fetchall()
        if rows:
            return [_to_place(r) for r in rows]
    return []


def stats() -> dict:
    conn = _connection()
    total = conn.execute("SELECT COUNT(*) FROM places").fetchone()[0]
    indian = conn.execute("SELECT COUNT(*) FROM places WHERE country='IN'").fetchone()[0]
    return {"places": total, "india": indian, "countries":
            conn.execute("SELECT COUNT(DISTINCT country) FROM places").fetchone()[0]}
