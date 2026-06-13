# Color

Curated and adapted for `paced.coach` from the palette logic in `nextlevelbuilder/ui-ux-pro-max-skill` (MIT). Keep this shortlist small on purpose. Expand only when repeated product work justifies a new family.

## How to use this file

1. Pick the surface:
   - core product
   - dashboard / analytics
   - public setup / onboarding
2. Start from the default family for that surface.
3. Stretch only when the task clearly benefits from it.
4. Do not introduce a new palette family just because a single screen wants novelty.

## Product principles

- The product should feel precise, trustworthy, athletic, and premium.
- Color should create hierarchy first and mood second.
- Primary actions and decision signals must stay obvious under real data density.
- Avoid making the app look like a crypto dashboard, gaming UI, or generic AI landing page.

## Current repo baseline

The current `web/app` product shell is dark-first, not light-first.

- app background: near-black / deep navy
- app surfaces: dark slate panels
- text: cool off-white with slate-muted secondary text
- accents already in use:
  - primary blue
  - success green
  - warning amber
  - danger red
  - info cyan
  - coach purple

This is visible in the live theme tokens under `web/app/src/app/globals.css`.

Implication:
- For core product work, prefer evolving the existing dark product language.
- Light surfaces are acceptable for public/legal/utility screens or specific preview shells, but they are not the main app default today.

## Surface families

### Core product

Default:
- dark-first foundation
- base hue: deep navy / mid blue
- support hue: slate / cool neutral
- action accent: warm amber or controlled orange
- text: cool off-white on dark surfaces

Why:
- This matches the current product shell and still tracks well with strong coaching and analytics palettes from the external repo.
- Blue communicates trust and precision.
- A warm accent makes CTAs and key next actions legible without turning the whole interface into marketing.

Good examples:
- foundation: `#0B0F19`, `#111827`, `#1A1F2E`, `#232938`
- primary: `#1F4ED8` to `#3B82F6`
- secondary: `#334155` to `#64748B`
- accent: `#D97706` to `#F59E0B`
- foreground: `#F0F2F5`

Stretch:
- cooler indigo-led variants for more technical surfaces
- slightly greener action accents for progress / success-heavy flows
- occasional lighter utility shells where the surface is explicitly public or document-like

Avoid:
- purple-pink “AI” gradients as the app default
- ultra-saturated neon accents for normal product workflows
- multiple competing accent colors in one view

### Dashboard / analytics

Default:
- deeper navy / blue foundation
- stronger neutral contrast
- restrained semantic accents for positive / warning / risk

Why:
- Data-heavy screens need stability and scanability.
- The external repo's dashboard palettes are useful here, especially the darker finance / analytics logic, but we should not blindly turn every dashboard dark.

Good examples:
- foundation: `#0F172A`, `#1E293B`, `#1D4ED8`
- positive: `#16A34A`
- warning: `#D97706`
- critical: `#DC2626`
- background: dark product panels by default; light analytic shells only when the surrounding product context supports them

Rules:
- Reserve the strongest accent for the most important series or state.
- Use semantic color consistently across charts and summary cards.
- If multiple series exist, do not rely on color alone; pair with line style, label clarity, or markers.

Avoid:
- rainbow charts
- 5 equally loud KPI cards in different colors
- dark mode dashboards used only because they look “more technical”

### Public setup / onboarding

Default:
- allow higher chroma and more contrast
- one emotional accent family plus one support family
- use background atmosphere sparingly and keep the CTA path obvious

Good directions:
- editorial / premium:
  - ink navy + warm cream + restrained gold / amber
- campaign / onboarding:
  - saturated blue or teal + citrus / amber accent

Current repo note:
- public marketing pages today are also dark-led in several places, with cyan / emerald / indigo glow treatments.
- Marketing freedom should therefore feel like a stronger extension of the existing brand mood, not a complete reset.

Rules:
- the hero can be more expressive than the body sections
- proof sections should usually calm the palette back down
- CTA colors should remain stable across the page

Avoid:
- every section changing color language
- loud gradient hero followed by flat, directionless sections
- colorful UI shells without evidence or trust cues

## Palette heuristics

- `deep navy + blue + amber`: safest current product baseline
- `indigo + cool neutral`: slightly more technical, good for dashboards
- `navy + cream + muted gold`: premium/editorial marketing
- `teal + deep navy + lime accent`: controlled high-energy analytics or onboarding

## Accessibility and restraint

- Accent colors should not carry meaning alone.
- Check contrast before committing to subtle palettes.
- A world-class result is usually one strong palette used with discipline, not five clever colors at once.
