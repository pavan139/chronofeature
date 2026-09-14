"""
Build the bundled place database from GeoNames dumps.

Run once at build time. The output is a single indexed SQLite file that ships
with the package, so geocoding never makes a network call and never costs
anything per lookup.

SQLite rather than an in-memory dict because India alone has over half a million
populated places, and birth villages are exactly the small ones. Holding those in
Python dicts costs hundreds of megabytes; an indexed table costs almost nothing
and answers in well under a millisecond.

Coverage:
  - India: every populated place, including the ~551,000 villages GeoNames
    records with no population figure.
  - Rest of world: places above 15,000 population, for diaspora users.

Usage:
    python build_places.py data/ gunamilan/data/places.db
"""

from __future__ import annotations

import sqlite3
import sys
import unicodedata
from pathlib import Path

GID, NAME, ASCII, ALT, LAT, LON, FCLASS, FCODE, CC = 0, 1, 2, 3, 4, 5, 6, 7, 8
ADMIN1, POP, TZ = 10, 14, 17

POPULATED = {"PPL", "PPLC", "PPLA", "PPLA2", "PPLA3", "PPLA4",
             "PPLG", "PPLL", "PPLS", "PPLX", "PPLW"}

# Historic and colloquial names users still type. GeoNames' alternate-names
# column covers most of these, but not reliably for every city.
EXTRA_ALIASES = {
    "Mumbai": ["Bombay"], "Kolkata": ["Calcutta"], "Chennai": ["Madras"],
    "Bengaluru": ["Bangalore"], "Puducherry": ["Pondicherry"],
    "Thiruvananthapuram": ["Trivandrum"], "Kochi": ["Cochin"],
    "Vadodara": ["Baroda"], "Prayagraj": ["Allahabad"],
    "Varanasi": ["Banaras", "Benares", "Kashi"], "Kanpur": ["Cawnpore"],
    "Pune": ["Poona"], "Thrissur": ["Trichur"], "Tiruchirappalli": ["Trichy"],
    "Visakhapatnam": ["Vizag"], "Gurugram": ["Gurgaon"], "Shimla": ["Simla"],
    "Mysuru": ["Mysore"], "Hubli": ["Hubballi"], "Belagavi": ["Belgaum"],
    "Kozhikode": ["Calicut"], "Jabalpur": ["Jubbulpore"],
}

SCHEMA = """
PRAGMA journal_mode = OFF;
PRAGMA synchronous = OFF;

CREATE TABLE places (
    id         INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,
    region     TEXT NOT NULL DEFAULT '',
    country    TEXT NOT NULL,
    lat        REAL NOT NULL,
    lon        REAL NOT NULL,
    tz         TEXT NOT NULL,
    population INTEGER NOT NULL DEFAULT 0
);

-- One row per searchable spelling, folded to remove case and diacritics.
CREATE TABLE names (
    folded   TEXT NOT NULL,
    place_id INTEGER NOT NULL REFERENCES places(id)
);
"""

INDEXES = """
CREATE INDEX idx_names_folded ON names(folded);
CREATE INDEX idx_places_pop ON places(population DESC);
"""


def fold(text: str) -> str:
    """Strip diacritics and case so 'Sitapur', 'Sītāpur' and 'SITAPUR' all match."""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(stripped.lower().replace("-", " ").replace(".", "").split())


def load_admin1(path: Path) -> dict[str, str]:
    out = {}
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 2:
                out[parts[0]] = parts[1]
    return out


def spellings(row: list[str], keep_aliases: bool) -> list[str]:
    """Every Latin-script name this place should answer to, folded.

    Curated aliases go in before the GeoNames alternates. The list is capped,
    and GeoNames can carry dozens of transliterations for a major city, so
    appending the curated ones last silently drops exactly the names users are
    most likely to type.
    """
    names = [row[NAME]]
    if row[ASCII] and row[ASCII] != row[NAME]:
        names.append(row[ASCII])
    if keep_aliases:
        names.extend(EXTRA_ALIASES.get(row[NAME], []))
        for alt in row[ALT].split(","):
            alt = alt.strip()
            if alt and alt.isascii() and 1 < len(alt) <= 40:
                names.append(alt)

    seen, out = set(), []
    for n in names:
        key = fold(n)
        if key and key not in seen:
            seen.add(key)
            out.append(key)
    return out[:12]


def iter_rows(path: Path, india_only: bool):
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            r = line.rstrip("\n").split("\t")
            if len(r) < 18 or r[FCLASS] != "P" or r[FCODE] not in POPULATED:
                continue
            if india_only and r[CC] != "IN":
                continue
            yield r


def main(src: str, dest: str) -> None:
    src_dir, dest_path = Path(src), Path(dest)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.unlink(missing_ok=True)

    admin1 = load_admin1(src_dir / "admin1.txt")
    conn = sqlite3.connect(dest_path)
    conn.executescript(SCHEMA)

    seen_ids: set[int] = set()
    places, names = [], []

    def collect(row: list[str]) -> None:
        gid = int(row[GID])
        if gid in seen_ids:
            return
        seen_ids.add(gid)
        try:
            pop = int(row[POP] or 0)
        except ValueError:
            pop = 0
        places.append((
            gid, row[NAME], admin1.get(f"{row[CC]}.{row[ADMIN1]}", ""),
            row[CC], float(row[LAT]), float(row[LON]), row[TZ], pop,
        ))
        # Aliases balloon the index and add little for unnamed hamlets.
        for folded in spellings(row, keep_aliases=pop > 0):
            names.append((folded, gid))

    for row in iter_rows(src_dir / "IN.txt", india_only=True):
        collect(row)
    for row in iter_rows(src_dir / "cities15000.txt", india_only=False):
        collect(row)

    conn.executemany("INSERT INTO places VALUES (?,?,?,?,?,?,?,?)", places)
    conn.executemany("INSERT INTO names VALUES (?,?)", names)
    conn.executescript(INDEXES)
    conn.commit()
    conn.execute("VACUUM")
    conn.close()

    indian = sum(1 for p in places if p[3] == "IN")
    size_mb = dest_path.stat().st_size / 1024 / 1024
    print(f"{len(places):,} places ({indian:,} in India), "
          f"{len(names):,} spellings -> {dest_path} [{size_mb:.1f} MB]")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
