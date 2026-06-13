# Directions

Choose one dominant direction per task. A secondary accent is acceptable; a blended pile of styles is not.

## `product-premium`

Use for:
- core app surfaces
- settings, onboarding, summaries, and feature flows
- screens where trust, clarity, and polish matter more than novelty

Current repo fit:
- today this usually means a dark-first athletic coaching surface, not a bright luxury treatment

Signals:
- deep navy / slate surfaces with cool off-white text
- restrained palette
- precise spacing and one clear focal action
- typography that feels refined without shouting
- subtle depth and motion, not spectacle
- semantic accents used with discipline, especially blue / green / amber

Avoid:
- marketing hero treatment inside the product
- oversized display type in dense workflows
- ornamental gradients standing in for hierarchy
- “premium” interpreted as glassy, purple, or decorative-for-its-own-sake

## `dashboard-technical`

Use for:
- KPI-heavy screens
- analytics, comparisons, and status views
- plan / progress surfaces that need dense but legible information

Signals:
- information hierarchy before decoration
- compact chrome, stronger data contrast
- careful use of accent color to mark significance, not every series
- numerals and labels optimized for scanning
- dark product-shell compatibility by default, unless the surrounding context is explicitly light

Avoid:
- chart junk
- equal emphasis across every metric
- oversized cards that waste vertical space

## `editorial`

Use for:
- story-driven landing pages
- explainers, setup narratives, and premium public surfaces
- pages where typography should carry a large share of the mood

Signals:
- strong type hierarchy
- asymmetry when it improves pacing
- more breathing room
- imagery or proof blocks that feel curated, not templated
- in this repo, editorial often still sits on a dark or ink-heavy foundation rather than a magazine-white foundation

Avoid:
- dropping editorial styling into utilitarian app screens
- turning every section into a different visual system

## `campaign`

Use for:
- acquisition pages
- public onboarding sections
- high-energy CTA surfaces

Signals:
- immediate hook
- punchier contrast
- shorter copy bursts
- stronger section transitions and more visible call-to-action framing
- allowed to be bolder than the product, but should still feel like `paced.coach`, not a random growth landing page

Avoid:
- too many competing CTAs
- loud visual treatment without proof
- novelty that weakens trust

## Routing shorthand

- `web/app` default: `product-premium` with a dark-first athletic coaching baseline
- `web/app` data-heavy flows: `dashboard-technical`
- public setup/onboarding pages: `editorial` or `campaign`
