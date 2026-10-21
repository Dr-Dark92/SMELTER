# SMELTER workbench design system

Reference: [UI UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/tree/56ea9cf174ed86786187daa9de0e6247cb0747e4), pinned at `56ea9cf174ed86786187daa9de0e6247cb0747e4`. Read SKILL.md, the web quick reference and professional rules before implementation. The skill is reference material; it is not installed as a runtime tool or authority source.

## Product and implementation

SMELTER is a local developer/asset workbench with a Python HTTP backend and vanilla JavaScript/HTML/CSS. It is not a SaaS marketing page. Keep the existing framework, APIs, IDs and controller boundaries; add no frontend build system, remote fonts, CDN icons or analytics.

The skill generator was actually run in disposable CI with:
`"developer tools dashboard dark" --design-system --variance 4 --motion 1 --density 8 -p SMELTER --json`.

Verified identities: Developer Tool / IDE; Dark Mode (OLED); Developer Tool / IDE color profile; Developer Mono typography. The generated FAQ/Documentation Landing composition does not fit an operational workbench and is explicitly rejected. The GSAP scroll-reveal snippet is unnecessary for this tool; plain reduced-motion-aware CSS is used.

The generated slate/green palette informed the dark developer surface and semantic success color. SMELTER uses an amber primary action and mint permission/success state as deliberate brand overrides. System sans/monospace stacks replace the recommended hosted IBM Plex Sans/JetBrains Mono to keep the interface offline and avoid new font downloads.

## Tokens and measured representative pairs

| Role | Value |
| --- | --- |
| Canvas | #0d1117 |
| Surface | #141c26 |
| Raised surface | #1b2735 |
| Main text | #edf2f8 |
| Secondary text | #a3b2c5 |
| Primary action | #ffb169 |
| Primary action text | #211407 |
| Success/access | #8cdecf |
| Input boundary | #52677e |
| Focus | #b1deff |

Representative contrast ratios: body 15.24:1, secondary 7.95:1, primary button 10.06:1, input boundary 3.09:1, focus 12.06:1, user-message text 10.22:1. These are token calculations, not a blanket WCAG certification.

Use a 4/8px spacing rhythm, compact navigation, 40px desktop action height and 44px touch actions. Native checkbox targets use 24px CSS dimensions; preserve explicit accessible labels. Inline vector geometry uses one stroke family. No decorative emoji as structural icons.

## Information architecture

- Persistent conversation rail on desktop; keyboard-dismissable drawer on smaller screens.
- One workbench with title, distinct message roles, evidence cards and an integrated composer.
- One searchable Settings centre. Full model/context/output/timeout details live in next-task access; the main screen shows a compact selection summary.
- Skill and location management remain tables with bulk controls. Changes to location policy remain staged until Apply.
- Folder selection uses server-side operator metadata navigation. Browsing never grants access.
- Configured-model badges distinguish saved selection from successful inference. Host metrics distinguish model allocation from GPU utilization.
- External MCP remains visibly blocked. Managed OpenCode clearly states its read-only container boundary.

## States and interaction

Provide meaningful empty states, real loading text, preserved form errors, disabled busy controls, explicit conflict/revert states and visible focus. Restore focus after dialogs. Search settings by both labels and common task terms such as locations, context, tokens and permissions.

Honor reduced motion. Auto-rotation requires a user action. GLB preview callbacks, exports and animation timers belong to one active owner and must not update released/replaced instances.

Responsive checks target 375, 768, 1024 and 1440 CSS pixels. Wide data tables scroll inside their own labelled region; page-wide overflow is rejected. The composer and status areas must leave usable space for the conversation on mobile.

## Verification

Use `tools/analysis/check_workbench_browser.mjs` with the explicit test dependencies and disposable fixture. It verifies actual UI/HTTP flows and generated embedded GLB rendering/playback/labels/PNG/WebM, including cancellation and late callbacks. It calls no live model. CI screenshots are evidence of the synthetic fixture; they are not the user's live rig.
