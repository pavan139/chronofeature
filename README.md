# Astro
A multilingual, server-rendered frontend for the supplied Guna Milan engine.

## Run
Requires Python 3.11 or newer. Use a virtual environment.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
python scripts/fetch_places.py
uvicorn gunamilan.api:app --reload
```

Open http://127.0.0.1:8000/en/. Coordinate-based charts and matching work without the place database. Place autocomplete needs the GeoNames build. The source files now live in the standard `gunamilan/` package. Original arithmetic and lookup tables are retained.

## Interface
- Two-person compatibility form with Ashtakoota and Dasa Porutham shown separately.
- Natal chart, Navamsa, Vimshottari periods, doshas and explicit exceptions.
- Responsive ink-and-copper theme, session-only dark mode, keyboard place selection, visible focus and reduced-motion support.
- Privacy-safe Web Share and link-copy actions. Shared URLs never contain names, dates, places or calculation inputs.
- Installable web-app manifest with standalone display metadata.
- Localized date formatting, explicit unknown-time state, print stylesheet.
- Language switching retains entered details in page memory. Refresh clears them.
- No birth details in URLs, cookies, localStorage, sessionStorage or application databases.
- API responses carry no-store and noindex headers.
- No account, checkout or paid-report gate has been implemented. `/match/full` is accessible like the original endpoint. Separate free/full endpoints do not constitute payment enforcement.

## Languages
All 34 interface messages have an explicit entry in each of 23 catalogs:
English, Hindi, Tamil, Telugu, Kannada, Malayalam, Marathi, Gujarati, Bengali, Punjabi, Odia, Assamese, Urdu, Nepali, Sanskrit, Konkani, Maithili, Dogri, Sindhi, Kashmiri, Bodo, Manipuri and Santali.

**Translation status:** initial translations, not native-speaker approved. Detailed engine explanations remain English, labelled as such. Proper names and some chart labels remain transliterated. Manipuri currently uses Bengali script, Santali uses Ol Chiki, and Kashmiri/Sindhi use Arabic script. Alternative scripts are not implemented.

This is a multilingual interface, not a claim that all generated astrological prose is fully translated. Native-language review and translation of rule templates remain release work. See `docs/review.md`.

## SEO
Pages render substantive controls and headings on the server. Each language has stable URLs:
- `/{locale}/`: Guna Milan
- `/{locale}/porutham/`: Dasa Porutham
- `/{locale}/birth-chart/`: natal chart

Route-specific titles and descriptions, Open Graph and X metadata, canonical URLs, supported-language hreflang alternates, x-default, WebSite/WebPage/WebApplication JSON-LD, sitemap, robots and a web-app manifest are generated from configuration. Unknown routes return 404. No invented testimonials, ratings, doorway location pages or unverified ranking claims are included.

By default all pages are **noindex** and robots disallows crawling. A private repository does not make a deployed web service private. Authentication belongs to the chosen host or reverse proxy.

For a deliberately public release, configure the actual HTTPS origin and the languages that passed review:
```text
SITE_URL=https://your-actual-domain.tld
INDEXABLE=true
INDEX_LOCALES=en,hi,ta
```
Unlisted languages remain usable but noindex and absent from the sitemap. Google hreflang uses supported two-letter language codes. Three-letter locale routes remain available through normal links. Do not claim ranking or Core Web Vitals scores until measured on the deployed host.

Primary references:
- [Google localized versions](https://developers.google.com/search/docs/specialty/international/localized-versions)
- [Google page experience](https://developers.google.com/search/docs/appearance/page-experience)
- [FastAPI templates](https://fastapi.tiangolo.com/advanced/templates/)
- [GeoNames data format](https://download.geonames.org/export/dump/readme.txt)

## Tests
```bash
python -m pytest -q
python -m playwright install --with-deps chromium
# With uvicorn running on port 8000:
python tests/browser_ui.py
```

GitHub Actions builds the real GeoNames database, runs the original engine tests plus HTTP/locale regressions, and exercises calculation, unknown time, language handoff, mobile overflow, RTL, keyboard place search and its failure state in Chromium. Screenshot artifacts use fictional test names. CI also builds the Docker image and runs three sequential Lighthouse audits against an indexable loopback instance, reporting every score and gating the median at 90 for performance, accessibility and SEO. This accounts for shared-runner variance using [Google's guidance](https://developers.google.com/web/tools/lighthouse/variability). Its synthetic scores are not production or field measurements.

## Deployment
The included Dockerfile runs FastAPI and serves static assets in one service.
```bash
docker build -t astro .
docker run --rm -p 8000:8000 -e INDEXABLE=false astro
```
Run `python scripts/fetch_places.py` before building the image to include its database. Alternatively mount a prebuilt database and point `PLACES_DB` at it. `.env.example` documents variables but is not automatically loaded by the application.

Before external release, configure the domain, HTTPS, host access, production monitoring and request-rate limits. Keep proxy/body logging disabled for personal requests. The repository does not contain a deployed host or credentials.

## Engine and licensing
The supplied engine uses Swiss Ephemeris with Lahiri, Raman, Krishnamurti and Fagan–Bradley ayanamsas. Calculation results follow the supplied traditional rules and are not scientific predictions of relationships, health or fertility.

The original README notes Swiss Ephemeris' AGPL/commercial licensing requirements. Preserve that licensing review before distributing or hosting proprietary code. GeoNames data is CC BY 4.0 and is attributed in the interface. No new license has been imposed on the user's source.
