# Interaction and reading comfort

This update keeps the existing Python calculations, server-rendered content, privacy model and exports unchanged.

- Quick report navigation opens the requested section and moves keyboard focus to its heading. No birth details are written to URLs.
- Four-item report checklists show real completion progress. Ticks survive in-page language changes and reset/undo, but are not stored or exported. A fresh calculation starts a fresh checklist.
- Help results and planet buttons accept arrow keys, Home and End. Selection remains explicit with Enter/Space. Normal Tab navigation is preserved. Arrow Down from help search reaches the first result.
- Help contains English-labelled reading preferences for larger report text and disabling animations. These survive in-page language changes but not reloads. Device reduced-motion settings always take precedence.
- Finite 120–180 ms feedback marks button presses, opened explanations and completed form steps. No parallax, continuous motion, fake progress or score-counting animation.
- Coarse-pointer help controls have 44px targets. High-contrast mode preserves selection outlines and chart marks. Navigation controls wrap instead of requiring horizontal dragging.

## Evidence and boundaries

The browser suite checks preference persistence, checklist persistence, keyboard focus and selection, reduced motion, forced colors and 320px chart reflow alongside the existing 23-language flows and real exports. Local syntax checks supplement CI, not replace browser testing.

This is not an accessibility certification. Screen-reader, physical-device and native-language review remain release requirements. New reading-preference copy and checklist narrative are explicitly English. No ranking or field-performance claims follow from these changes.

Primary guidance:
- [W3C interaction animation](https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html)
- [W3C target sizes](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html)
