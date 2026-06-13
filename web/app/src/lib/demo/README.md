# Demo data (client-safe)

This folder contains **baked, anonymized demo artifacts** for the public `/demo` page.

## Rules

- **Strict anonymization:** no athlete names, race names tied to real people, trace IDs, run IDs, token/cost metadata.
- **No live DB serving for public users:** anonymous visitors must never read local DB rows at runtime.
- **No raw exports in web runtime:** do not import from repository `data/` directly in the web app.
- **UI schemas:** TypeScript types in `demo-data.ts` mirror `services/ai/langgraph/schemas/ui_blocks.py`.
- **Single curated persona:** demo output is deterministic, keyed by `hybrid-operator`.

## Canonical source of truth

- `web/app/src/lib/demo/fixtures/v1/analysis.ts`
- `web/app/src/lib/demo/fixtures/v1/season.ts`
- `web/app/src/lib/demo/fixtures/v1/weekly.ts`
- `web/app/src/lib/demo/personas.ts`

`web/app/src/lib/demo/demo-data.ts` re-exports the canonical persona bundles consumed by UI.

## Manual refresh workflow (release cadence)

1. Run a real local e2e analysis for the target athlete account.
2. Export sanitized artifacts with `scripts/export_demo_fixtures.py` (one persona per run).
3. Review exported JSON manually and confirm no identity leaks.
4. Promote selected content into `fixtures/v1/*` persona bundles.
5. Run validation:
   - `npm test` (fixture schema + leak scan)
   - `npm run lint`
   - `npm run build`

Example:

```bash
pixi run python scripts/export_demo_fixtures.py \
  --persona-slug hybrid-operator \
  --user-id 11111111-2222-3333-4444-555555555555 \
  --display-alias "Demo Athlete" \
  --out-dir ./data/demo_exports
```

The script output is **intermediate review material**, not auto-committed fixtures.
