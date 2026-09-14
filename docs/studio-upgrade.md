# Astro Studio upgrade

## Design and product decisions

The previous guided form reduced density but still surrounded numbers with unexplained terminology. This update replaces its ink/copper working surface with a violet/lime identity, stronger editorial typography, a dark report header and a concise preview panel. The repeated “traditional reading” headline is removed from all catalogs. A short outcome limitation stays at the report footer and contextual definitions explain specific limits.

The implementation retains FastAPI, server-rendered Jinja and vanilla JavaScript. No React migration, purchased component bundle, cursor gimmick, infinite animation or remote font is required. Decorative hero art is marked aria-hidden. The report's circular diagram is separately generated from actual graha longitudes and describes its scale limitations.

## Added journeys

- Birth form → contextual `?` → English definition and next action → Escape returns to the initiating control, with no data submitted.
- Result → numerical summary → full-point or reduced-point factor → exact rule, meaning and practical discussion prompt.
- Breakdown → review-only filter → print expands all factors and restores the prior filter afterward.
- Chart → select one of nine grahas → exact sidereal longitude, sign, nakshatra, pada, D9, house and condition, with field-specific help.
- Report → private checklist → PDF containing the same shared definitions, numerical summary and chart glossary.
- Public guide → one of three articles or 37 searchable terms → ordinary crawlable links back to the calculator.
- Review card → edit one person → return directly to review, including across a language handoff.

The `analysis` API property is deterministic, versioned and explicitly English. The summary does not generate personality traits, probabilities, fertility claims or future events. Points not earned order the arithmetic breakdown only. Essential checks and implemented exceptions remain separate from total points. Historical group labels are explicitly not classifications of human worth.

## Current research, checked 14 September 2026

| Primary source | Observed pattern or guidance | Decision for Astro |
| --- | --- | --- |
| [Prokerala Kundali matching](https://www.prokerala.com/astrology/kundali-matching/) | Public form accepts two people's birth details and presents 36-point matching. | These are baseline capabilities, not a differentiator. Add explanations at the moment of use. |
| [Prokerala birth chart](https://www.prokerala.com/astrology/birth-chart/) | A chart view complements input and tabular positions. | Add an actual longitude explorer with accessible controls and exact table values. Do not label it a North/South Indian chart layout. |
| [AstroSage matching](https://www.astrosage.com/free/kundlimatching.asp) | Its public calculator exposes birth details, coordinate settings and score explanations. | Differentiate through guided review, uncertainty context and low-friction help, not an unsupported superiority claim. |
| [Google AI features](https://developers.google.com/search/docs/appearance/ai-features) | Existing SEO fundamentals apply. No additional machine-readable files or special schema are required for eligibility. | Use server-rendered explanations, working links, accurate metadata and a fast interface. Do not market an AI-ranking hack. |
| [Google multilingual sites](https://developers.google.com/search/docs/specialty/international/managing-multi-regional-sites) | Separate language URLs are supported. Translating only navigation around unchanged main content is discouraged. | Keep 23 explicit UI routes but publish substantive English guides only under English until translated and reviewed. |
| [Google Search updates](https://developers.google.com/search/updates) | FAQ rich results stopped appearing from 7 May 2026. FAQ documentation was removed in June. | Keep useful visible FAQs without claiming FAQ rich-result eligibility or adding obsolete markup for that purpose. |
| [Web Vitals](https://web.dev/articles/vitals) | LCP, INP and CLS describe different parts of real user experience. | Retain repeatable synthetic audits but require production field data before claiming field performance. CI's TBT is not INP. |
| [MDN dialog](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/dialog) | Native modal dialogs provide focus/inert behavior and Escape dismissal. | Use a labelled dialog, explicit Close, search focus and return-focus tests. |
| [Pillow ImageFont](https://pillow.readthedocs.io/en/stable/reference/ImageFont.html) | The bundled default font can be loaded at a chosen size. | Generate a fixed public PNG social card without remote fonts or caller content. |

This is a focused comparison of public pages, not an exhaustive competitor audit, conversion study or ranking forecast. The earlier [UI modules research](ui-research.md) records component-library choices and licensing cautions. No X media or proprietary design resource was copied into the product.

## SEO implementation and remaining release work

Implemented: route-specific descriptions, visible English FAQs, four crawlable English guide pages, Article/CollectionPage/BreadcrumbList structured data matching visible text, no false review ratings, a fixed 1200 × 630 PNG social preview, absolute OG/X metadata, controlled sitemap inclusion, canonical/hreflang rules and real 404s. POST results and report files remain non-indexable and non-cacheable.

Before public launch:

1. Choose the actual production origin, HTTPS and access policy. A private GitHub repository is not web authentication.
2. Set `SITE_URL`, `INDEXABLE=true` and only reviewed `INDEX_LOCALES`. Submit the sitemap in the owner's Search Console after deployment. No external property has been created or submitted by this change.
3. Review all translation drafts with native speakers. Narrative definitions and guides are English, not silently machine-translated into 22 duplicate pages.
4. Validate licensing, request-rate limits, proxy/body log settings, uptime and error monitoring.
5. Collect real mobile LCP/INP/CLS and successful-flow completion data with an approved privacy policy. Synthetic CI scores do not establish field performance, ranking or conversion lift.
6. Test physical iOS/Android devices, screen readers, zoom and long translated text with users. Browser CI covers Chromium rather than universal device compatibility.
7. Independently validate inherited dasha subdivisions before using them for timing-sensitive features. No fabricated shared marriage window or predictive recommendation is added.

There is no account system, cloud history, chat model, payment processor, consultation booking or production host in this change. These require product and privacy decisions rather than empty interface controls.
