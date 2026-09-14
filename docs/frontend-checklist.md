# Frontend checklist for AI-assisted changes

Use this alongside [the research record](ui-research.md). It is project documentation, not an installed agent skill.

## Define a bounded task

Give the agent the affected user journey, current files, intended behavior and acceptance cases. Request one coherent change. A screenshot is a visual reference, not proof of keyboard behavior, loading states, privacy or responsiveness.

Example brief:

> Improve birthplace selection within the existing FastAPI/Jinja frontend. Preserve the API and all 23 catalogs. A keyboard user must select a place, verify its timezone, and continue. A failed lookup must leave manual coordinates usable. Add browser checks for empty results, server failure, RTL and mobile overflow. Do not add a framework, tracking or persistence.

## Implementation contract

- Keep the primary action explicit. Do not auto-submit, skip review or preselect consequential choices to shorten a flow.
- Reuse native buttons, inputs, fieldsets, details and links before adding a runtime dependency. Use links for URLs and buttons for actions.
- Put visible labels outside inputs. Preserve paste, native date/time controls, browser zoom and clear focus.
- Validate the active logical group. Mark errors with text and `aria-invalid`, connect explanations through `aria-describedby`, and focus the first invalid field.
- Preserve user input on recoverable failures and locale changes. Abort stale requests, ignore old responses and prevent duplicate submissions.
- Keep scores separate from their interpretation. Do not convert them into compatibility probabilities. Keep unknown-time and essential-failure warnings visible.
- Never insert report or input strings as HTML. Build text nodes or rely on Jinja autoescaping.
- Keep birth details, undo state and reports in page memory only. Explicit downloads are local artifacts. Never put birth data in analytics, storage, links or third-party AI prompts.
- Retain the ink/copper identity. Use semantic tokens, logical CSS properties, nested corner hierarchy, readable contrast and tabular numeric figures.
- Use 16 px or larger input text and generous touch targets. Check long Indic labels, Arabic RTL, long names, narrow viewports and enlarged text.
- Use short opacity/transform feedback only where it explains an action. Honor reduced motion. Never add fake loading waits or animate keyboard selection.
- Put secondary report actions behind a clear disclosure. Give it keyboard access and Escape dismissal. Do not style a disclosure as an ARIA menu without implementing menu behavior.
- Keep static semantic pages, metadata, canonical rules and controlled indexing intact. A client-side state improvement must not erase crawlable content.

## Acceptance evidence

1. Check JavaScript syntax and run Python tests.
2. Complete compatibility and natal-chart journeys using real API calculations and synthetic birth details.
3. Check validation, backward navigation, review edits, language handoff, unknown time, same-place reuse, clear/undo and sample labelling.
4. Force calculation and PDF failures. Verify details survive and retry remains usable. Check that edits invalidate old results.
5. Download PDF and JSON. Parse the files and verify their inputs and locale. Keep PDF regression tests when editing the screen interface.
6. Check every locale on a narrow mobile viewport, plus desktop, dark mode, keyboard flow and reduced motion. Visually inspect screenshots, not just DOM assertions.
7. Preserve baseline audit gates and report actual CI results. Do not equate Lighthouse scores with ranking, field performance or full accessibility compliance.
8. Review the diff for unrelated files and third-party additions. Push to the existing feature branch. Merging and public deployment are separate decisions.

No accounts, payments, saved history, offline certification or complete narrative localization should be claimed until actually implemented and tested.
