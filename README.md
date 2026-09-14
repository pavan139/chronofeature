# Guna Milan engine

Vedic marriage compatibility from Swiss Ephemeris. Both major traditions, full
natal charts, dashas, doshas with their exceptions, and offline geocoding for
half a million Indian places. No third-party astrology API, no per-call cost,
no network dependency at runtime.

```bash
pip install -r requirements.txt
python build_places.py data/ gunamilan/data/places.db   # once, see below
pytest gunamilan/                                        # 65 tests
uvicorn gunamilan.api:app --reload
```

```python
import datetime as dt
from gunamilan import geocode, BirthData, cast_chart, match, match_porutham

groom = BirthData.from_place("Arjun", dt.date(1992, 3, 14), dt.time(7, 25),
                             geocode("Hyderabad"))
bride = BirthData.from_place("Priya", dt.date(1994, 11, 2), dt.time(14, 10),
                             geocode("Bombay"))
g, b = cast_chart(groom), cast_chart(bride)

match(g, b).total            # 25.5 of 36, North Indian
match_porutham(g, b).passed  # 6 of 10, South Indian
```

## What it does

| Area | Detail |
|---|---|
| Ashtakoota | All eight kootas, 36 points, North Indian |
| Dasa Porutham | All ten poruthams, South Indian |
| Natal chart | Nine grahas, whole-sign houses, retrogression, combustion, dignity |
| Navamsa | D9 divisional chart |
| Dashas | Vimshottari to three levels, plus marriage-window candidates |
| Doshas | Mangal, Kaal Sarp, Sade Sati, and the Nadi and Bhakoot exceptions |
| Geocoding | 579,312 places across 244 countries, offline |
| Ayanamsa | Lahiri, Raman, Krishnamurti, Fagan-Bradley |

## Layout

| File | What it holds |
|---|---|
| `tables.py` | Every classical lookup table, annotated with the tradition it follows |
| `ephemeris.py` | Swiss Ephemeris wrapper; grahas, houses, Navamsa, transits |
| `matching.py` | The eight kootas and the 36-point total |
| `porutham.py` | The ten poruthams and the rajju and vedha tables |
| `dasha.py` | Vimshottari periods and sub-periods |
| `doshas.py` | Mangal, Kaal Sarp, Sade Sati, and koota exceptions |
| `geocode.py` | Offline place lookup with fuzzy and alias matching |
| `api.py` | FastAPI service |
| `test_gunamilan.py` | 65 tests across tables, bounds, ephemeris and geocoding |

## Decisions worth knowing about

**Two traditions, one set of birth details.** Ashtakoota is North Indian. Tamil,
Malayalam and much of Telugu practice uses the ten poruthams, and a Chennai
family handed a 36-point guna score will tell you it is the wrong system.
Supporting both is not a feature so much as the price of not being regional by
accident. It also happens to be the cheapest route into less contested search
terms.

**Rules live in tables, logic lives in functions.** Schools disagree on the
Vashya matrix, the Gana matrix, the Dina remainders and several Nadi and Bhakoot
exceptions. Every one is a table with a comment naming the variant. An astrologer
who wants their own tradition edits `tables.py` and nothing else, which is also
what makes a white-label version possible later.

**Exceptions are applied, not skipped.** Most free tools report Nadi dosha and
stop. The exceptions are where the skill sits, and omitting them is why people
are told a match is ruined when a practising astrologer would have waived it.
Every cancellation is named in the output. The arithmetic is never quietly
adjusted, because the 36-point total is a fixed convention and inflating it would
make the number incomparable with every other tool; exceptions change the verdict
and appear in their own field.

**Explanations are generated from the rule, not written by a model.** Each koota
and porutham returns its own sentence. An LLM layered on top can never contradict
the arithmetic, because it never produces the arithmetic. This is the answer to
the complaint users make most often about existing apps.

**Missing birth time degrades honestly.** The Moon changes nakshatra roughly
every 21 hours and the ascendant changes sign every two hours. Without a time the
ascendant returns `None` rather than a confident wrong answer, house numbers are
zero, the Mangal check runs from the Moon and Venus only, and the API attaches a
warning.

**Geocoding is offline and covers villages.** GeoNames records about 551,000
Indian populated places with no population figure, and those are exactly the
birth villages users type. SQLite with an index rather than an in-memory dict,
because half a million rows in Python costs hundreds of megabytes and the index
costs almost nothing. Ambiguous names return candidates rather than a silent
guess: picking the wrong Sitapur moves the coordinates hundreds of kilometres and
changes the ascendant.

## Building the place database

The database is generated, not committed. It needs three GeoNames dumps:

```bash
mkdir -p data && cd data
curl -LO https://download.geonames.org/export/dump/IN.zip
curl -LO https://download.geonames.org/export/dump/cities15000.zip
curl -L -o admin1.txt https://download.geonames.org/export/dump/admin1CodesASCII.txt
unzip -o IN.zip && unzip -o cities15000.zip && cd ..
python build_places.py data/ gunamilan/data/places.db
```

Produces a 71 MB file. GeoNames is CC BY 4.0, so attribution is required
wherever the data is surfaced.

## Verified against

15 August 1947, 00:00 IST, Delhi. Produces Vrishabha lagna and the Moon in Karka
at 3°58', giving Pushya pada 1, which matches the published chart. Held as a
regression test, along with exhaustive checks that no koota exceeds its maximum
across all 729 nakshatra pairs, that mahadashas tile 120 years without gaps, and
that Navamsa reproduces the movable, fixed and dual sign rules.

## Endpoints

| Route | Purpose |
|---|---|
| `GET /places?q=` | Typeahead for the birth-place field |
| `POST /chart` | Full natal chart with dashas and doshas |
| `POST /match/free` | Score, breakdowns and verdict; the shareable result |
| `POST /match/full` | Everything the paid report is built from |

The free and paid split lives in the API rather than the frontend, so the
paywall cannot be bypassed by reading the network tab.

## Not done yet

- **PDF report.** The paid artefact. Needs Devanagari and Tamil font embedding.
- **Web tool and the programmatic SEO pages.**
- **WhatsApp delivery and Razorpay checkout.** Both need your credentials.
- **Panchang and muhurat.** Natural second product from the same ephemeris.

## Needs you, not me

- Domain, hosting, Razorpay account (GST registration required)
- Meta Business verification for the WhatsApp API
- Two or three practising astrologers to check the tables against their own
  tradition before any of this goes public. The Vashya and Gana matrices and the
  Dina remainders are where schools diverge most.

## Licence note

Swiss Ephemeris is dual-licensed: AGPL, or a paid commercial licence from
Astrodienst. Shipping this closed-source requires the commercial licence. Budget
for it or plan to open-source. GeoNames data is CC BY 4.0 and needs attribution.
