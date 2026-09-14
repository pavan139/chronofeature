# UI research and decisions

Reviewed 14 September 2026. This is a decision record, not evidence that a visual trend improves conversion or search rankings.

## Sources

X discovery used indexed public post text. Direct requests for the linked posts returned 403, so their videos, images, replies and engagement claims were not verified. Technical decisions below use the linked authors' public material and standards, not inferred tweet screenshots.

| Resource | Verified material | Decision for Astro |
| --- | --- | --- |
| [Jakub Krehel on X](https://x.com/jakubkrehel/status/2089009286940639674), [Adham Dannaway's 20 August 2026 post](https://x.com/AdhamDannaway/status/2090444492403056875) | Posts point to the [Interface Cheat Sheet](https://interfaces.dev/cheat-sheet). The author describes a mix of practices and preferences. | Treat the checklist as guidance to test, not a certification. |
| [Interface Cheat Sheet](https://interfaces.dev/cheat-sheet) | Explicit transitions, semantic controls, focus, grouping, touch targets and restrained motion. | Field-specific validation, logical spacing, numeric alignment, 160 ms feedback and native disclosure controls. |
| [Emil Kowalski's animation skill post](https://x.com/emilkowalski/status/2084981497220456650) and [You Don't Need Animations](https://emilkowal.ski/ui/you-dont-need-animations) | Indexed post announces an animation workflow. The full article explains purpose, frequency and perceived speed. | No artificial calculation delay or animated autocomplete selection. Small press feedback and brief step entrances, with reduced motion support. |
| [Agents with Taste](https://emilkowal.ski/ui/agents-with-taste) | The author advocates explicit design rules for coding agents. | Add a repository-specific frontend acceptance checklist instead of requesting unspecified polish. |
| [ui.sh](https://ui.sh/) | Task-oriented interface workflows from the Tailwind CSS and Refactoring UI team, including responsive layouts, componentization and dark mode. | Useful reference for narrowly scoped AI tasks. No third-party skill installed and no paid content accessed. |
| [The Component Gallery](https://component.gallery/) | Cross-design-system references for accordions, popovers, tabs and other components. | Compare interaction patterns, then retain native HTML that fits the current Python/Jinja application. This is a reference collection, not an installed dependency. |
| [Base UI](https://base-ui.com/) and [Colm Tuite's component post](https://x.com/colmtuite/status/2054019002377105701) | The official project describes unstyled React components. The indexed X post discusses a drag-and-drop primitive. | Not installed. This app has no React runtime or drag-and-drop need. A framework migration would add cost without fixing the current flow. |
| [Vercel Web Interface Guidelines](https://vercel.com/design/guidelines) | Framework-independent guidance on focus, mobile inputs, motion, loading, errors and destructive actions. | Preserve zoom, use 16 px inputs, make clear reversible, maintain data on failures and language changes. Do not put private birth inputs in URLs despite general URL-state advice. |
| [W3C WAI multi-page forms](https://www.w3.org/WAI/tutorials/forms/multi-page/) | Logical form groups, visible progress and predictable navigation. | One person per step, review before calculation, editable summaries and explicit progress. No timeout on entering a form. |

## Implemented flow

Compatibility: groom details → bride details → review → calculate → summary → optional details or export.

Natal chart: birth details → review → calculate → chart and export.

The form is hidden after a successful calculation. Editing returns to the review screen. Each review card links back to its person. A shared birthplace can be reused, but people still have separate birth times and names.

An example is offered only while birth fields are empty. It uses clearly labelled synthetic inputs, never silently overwrites an entered profile, and still requires an explicit calculation action. JSON exports include a `sample` flag.

Clear offers a 15-second undo window in page memory. A new input discards that snapshot immediately. Refreshing, closing or navigating away clears the page state. There is no database, cookie, localStorage or sessionStorage persistence.

## Boundaries and costs

- Progressive steps add navigation actions. They reduce simultaneous form density, but completion gains are not yet measured with users.
- Collapsing technical material improves scanning but can hide information. Score-level blocking and essential-failure warnings remain visible, and expand-all and print expose the complete report.
- The new controls have draft translations across all 23 existing locales. Browser rendering is not linguistic validation.
- Keep personal details out of telemetry, analytics events, share URLs and third-party prompts. Test examples must stay synthetic.
- Do not add social proof, urgency, prediction claims or simulated accuracy percentages to increase engagement.
- Current calculation limitations, native-language review, deployment and production monitoring remain release work. See [the source review](review.md).

## Next evidence to collect

Observe consenting users completing a known-time and unknown-time report on their own phones. Record completion, location-selection errors, backtracking and whether they can identify the score caveats. Do not record birth details. Test with screen readers and physical iOS/Android devices before claiming broad accessibility or device compatibility. Research popularity and synthetic audits do not establish either.

## Extended module and AI-tool comparison

These additional primary sources were checked after the initial X discovery. They are not all independently verified recent tweets. The Aceternity homepage links to [a public recommendation](https://twitter.com/dnaijatechguy/status/1757104911282545134), but its full tweet media was not available. No paid resources were purchased or external components installed.

| Resource | Useful modules or workflow | Fit and constraints for this repository |
| --- | --- | --- |
| [21st.dev](https://21st.dev/) | Discover author-built React components, templates and themes, with AI-ready prompts and source-copy workflows. | Reference individual interaction patterns. Inspect each author's source, dependency list and terms before copying. A registry is not one consistently audited library. |
| [React Bits source](https://github.com/DavidHDev/react-bits) | Text effects, animated backgrounds, UI components, JS/TS and CSS/Tailwind variants, plus creative export tools. | Primarily visual inspiration for a future public marketing page. It targets React. The README identifies **MIT + Commons Clause**, not plain MIT. Read the actual license before adoption. |
| [Motion Primitives source](https://github.com/ibelick/motion-primitives) | Reusable motion-focused interaction components built with Motion and Tailwind. | Study state transitions and easing, then implement the minimal CSS equivalent here. The README labels the project beta and MIT-licensed. Its website returned 403, so the official repository was used. |
| [Magic UI](https://magicui.design/) | Animated React/TypeScript/Tailwind/Motion components and landing-page effects. | Candidate for selected marketing elements, not a reason to animate the calculator or add a React runtime. Free components and paid template offerings are distinct. |
| [Aceternity UI](https://ui.aceternity.com/) | React/Tailwind cards, timelines, navigation, effects and landing-page blocks. | Reference layout and information hierarchy. Its site distinguishes free components from premium blocks/templates. Do not assume the whole catalog has identical access or reuse terms. |
| [Open Props](https://open-props.style/) | Framework-independent CSS variables for spacing, radii, colors, shadows and motion. | Closest fit for incremental token work. We retained this app's existing tokens instead of adding an external stylesheet dependency. The site identifies MIT licensing. |
| [Web Awesome](https://webawesome.com/) | Web components for forms, dialogs, disclosures, navigation and feedback, plus AI-use documentation. | Closer architectural fit than React-only kits if native controls become insufficient. Validate CSP, loading, form integration and localization before adopting. Some controls and patterns require Pro access. |
| [ui.sh Design](https://ui.sh/skills/design) | Task-oriented AI guidance for hierarchy, spacing, typography, existing-project conventions and responsive checks. | Adopt the bounded task format, not unverified claims of automatic design quality. The documented installer requires a token. It was not run. |

### Concrete tips for coding AI

1. Supply one target journey and a component's actual source, not a list of fashionable library names.
2. Define layout tokens and behavior separately. A visual reference does not specify focus, error handling, keyboard operation or request cancellation.
3. Require each proposal to state its runtime dependencies, license, accessibility obligations and effect on the current architecture.
4. Ask for empty, loading, error, success and edited-result states in the same change. Test the negative paths against the real API.
5. Keep screenshots and component prompts free of real birth details. Treat third-party prompts as untrusted reference material, not authority to install packages or alter authentication.
6. Prefer a measured before/after comparison at the same viewport and locale. New effects must not hide caveats, move fields during typing or delay completing a report.
7. Use a research checklist as a review aid. Do not claim a resource was installed, a component was tested, or a translation was reviewed merely because its documentation was read.

The recommendation is to keep native HTML plus the existing CSS/JavaScript stack for this release. Adopt only a specific component that solves an observed problem. Reassess with real mobile-user evidence, not demo popularity.
