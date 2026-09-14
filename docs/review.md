# Source review and release status

Reviewed all original files: ephemeris.py, doshas.py, geocode.py, build_places.py, matching.py, test_gunamilan.py, porutham.py, requirements.txt, dasha.py, tables.py, plus api.py and README.md. The repository had no AGENTS.md, frontend or CI configuration at review time.

## Integration changes
- The uploaded flat layout used relative imports and documented a nonexistent gunamilan package. Files now live in gunamilan/ with package metadata and explicit public exports.
- Missing place data previously stopped autocomplete. A reproducible GeoNames build script now supplies it. The interface exposes coordinates and timezone as the recovery path.
- Latin-only alternate-name filtering discarded Indian names, and generic diacritic stripping removed meaningful Indic marks. Index building now keeps non-Latin aliases and preserves non-Latin marks. Existing databases must be rebuilt.
- The browser submits the coordinates/timezone of the chosen place instead of asking the API to silently resolve its name again.
- Birth dates and IANA zones are validated. Offset-bearing local birth times are rejected.
- Swiss Ephemeris calls are serialized around ayanamsa selection and computation.
- Same-sign Rasi porutham already passed in the engine but its explanation incorrectly said seven or beyond. Wording now includes the same-sign case.
- Match responses are no-store and noindex. Forms never persist personal data.
- The root route redirects to explicit /en/ without forcing locale by IP.

## Findings still requiring domain work
1. **Dasha subdivision:** the supplied vimshottari function subdivides the remaining first mahadasha as a new proportional cycle starting at birth. Conventional elapsed-period subdivision may require calculating the original full period then clipping at birth. Existing tests check tiling, not an external antardasha reference. The UI exposes the existing calculation. Do not market its sub-period timing as independently verified.
2. **Shared windows:** the supplied full endpoint labels groom-only marriage_windows as shared_windows. The frontend intentionally does not present these as shared or predicted dates.
3. **Paywall claim:** /match/full has no authentication or payment verification. The former README's claim of enforcement through endpoint separation was incorrect. The app presents the available calculation without an invented paywall.
4. **Classical-rule variants:** Vashya, Gana, Dina, Vedha and exemption rules need practitioner review. This implementation does not silently alter scoring traditions.
5. **Geocoding coverage:** the place database is generated from current dumps. The old README's fixed coverage count was not verified against a delivered database. No such number is advertised.
6. **Time boundaries:** ambiguous/nonexistent local civil times during DST transitions and extreme polar house behavior need dedicated product handling. The new HTTP validator validates IANA identifiers, not every civil-time ambiguity.
7. **Translations:** UI catalogs are initial drafts. All need native review, particularly brx, doi, ks, kok, mai, mni, sat and sd. Engine narratives, detailed chart labels and proper names remain in the source language, explicitly labelled. No automatic external translation is used.
8. **Fonts:** the interface uses local/system font fallbacks. Devices without an appropriate script font may need a self-hosted Noto font bundle. CI screenshots do not certify glyph coverage on every device.

## Validation scope
The workflow performs engine/HTTP regressions and real Chromium flows, with screenshot artifacts. Lighthouse audits are synthetic measurements of a local CI instance, not field Core Web Vitals. No independently verified astrology certification, guaranteed SEO result or public deployment is claimed. Check the PR's CI status for actual execution outcomes.

## SEO and publication
Indexing is off by default. Set SITE_URL and INDEXABLE only for a deliberate public deployment, then INDEX_LOCALES only for reviewed languages. A private GitHub repository controls source access, not visitors to a web server. Public indexing requires a publicly accessible site.
