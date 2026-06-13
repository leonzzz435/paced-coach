# Typography

Curated and adapted for `paced.coach` from the pairing logic in `nextlevelbuilder/ui-ux-pro-max-skill` (MIT). Use this as a shortlist, not as a mandate to constantly swap type systems.

## How to use this file

1. Identify the surface:
   - product
   - dashboard
   - marketing
2. Pick the closest typography mode.
3. Prefer a small number of deliberate pairings over novelty.
4. If the codebase or asset pipeline already provides brand fonts, use these rules to guide behavior, not to force a font change.

## Product principles

- Typography should make the product feel precise, calm, and premium.
- Readability and hierarchy outrank novelty in the app.
- Display typography is a tool, not a default.
- Numbers, deltas, and plan data need special care; dashboards live or die on scanning quality.

## Current repo baseline

The current repo is not typography-blank. There is already a working split:

- core app body default: `"Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif`
- product shell: dark, scanable, fairly restrained
- marketing/public landing work already uses `Space Grotesk` + `Manrope`

Implication:
- The skill should treat these as the current approved baseline, not as something to overwrite casually.
- New typography decisions should either:
  - reinforce these choices,
  - or deliberately improve on them with a clear reason.

## Modes

### Product default

Mood:
- modern
- precise
- premium without looking luxurious-for-its-own-sake

Preferred behavior:
- use a strong, neutral or slightly friendly sans for most UI
- keep the scale tight and consistent
- let spacing and weight do more work than exotic letterforms

Current default:
- `Avenir Next` behavior is the current product baseline even if the skill recommends future alternatives.

Recommended families:
- `Avenir Next` when preserving the existing product voice
- `Plus Jakarta Sans`
- `Inter`
- `Work Sans`

Use when:
- building normal app flows
- forms, settings, summaries, navigation, onboarding

Avoid:
- editorial serif headlines inside dense workflows
- highly stylized display fonts in core product paths

### Dashboard / analytics

Mood:
- technical
- scannable
- high information clarity

Preferred behavior:
- use clean sans type with excellent numeral legibility
- slightly tighter vertical rhythm than marketing surfaces
- make metric hierarchy explicit with weight and size, not only color

Recommended families:
- `Avenir Next`
- `Inter`
- `IBM Plex Sans`
- `Source Sans 3`
- optional mono accent for code-like or precision labels: `JetBrains Mono`

Rules:
- use tabular numerals where possible for aligned metrics
- labels should stay readable at smaller sizes
- mono accents are for precision moments, not whole screens

Avoid:
- ultra-wide display fonts for KPI grids
- tiny gray helper text carrying critical meaning

### Marketing / editorial

Mood:
- more expressive
- more spacious
- more memorable

Preferred behavior:
- pair a distinctive heading voice with a readable body voice
- allow larger jumps in type scale
- use contrast between headline and body to create mood and pacing

Recommended pairings:
- current repo-approved: `Space Grotesk` + `Manrope`
- `Cormorant` or `Playfair Display` + `Inter`
- `Outfit` + `Work Sans`
- `Space Grotesk` + `DM Sans` for more modern/tech storytelling

Use when:
- landing pages
- public setup or onboarding sections
- premium product storytelling

Avoid:
- swapping typography pairing every other section
- expressive serif display type with cramped body copy

## Hierarchy rules

- Product UI:
  - compact, disciplined, low drama
- Marketing:
  - more contrast, more whitespace, more memorable headlines

If a screen or scene feels expensive but unclear, reduce typography variety before adding more decoration.

## Practical rules

- One primary body font across most product work is a feature, not a limitation.
- Use display faces mainly in marketing.
- Use mono selectively for metrics, technical callouts, or small data accents.
- If typography already feels strong, improve spacing and line length before changing families.

## A product-friendly shortlist

- Safest product baseline:
  - `Avenir Next`
  - `Inter`
  - `Plus Jakarta Sans`
- Best technical/dashboard support:
  - `Avenir Next`
  - `IBM Plex Sans`
  - `Source Sans 3`
  - `JetBrains Mono` for accents
- Best creative marketing support:
  - `Space Grotesk`
  - `Sora`
  - `Manrope`
  - `Cormorant` or `Playfair Display` only when the surface benefits from real editorial contrast

## Upgrade rule

Do not propose a new primary product type system unless the change is intentionally repo-wide.

For normal work:
- preserve `Avenir Next` behavior in the app
- preserve `Space Grotesk` + `Manrope` on existing marketing surfaces unless the task explicitly calls for a redesign
- use the shortlist above mostly as an expansion space for future world-class refinements

## Off-limits by default

- novelty display fonts in core product UX
- decorative scripts
- overusing mono as the primary UI voice
- giant headline scales in dense dashboard contexts
