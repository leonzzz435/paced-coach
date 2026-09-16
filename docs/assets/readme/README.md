# Public screenshot provenance

The four `paced-coach-*.png` images are rendered from the current public `/demo`
route using the hand-authored schema-v3 fixtures in
`web/app/src/lib/demo/fixtures/v3/`. The old device-derived analysis is not part
of the current preview. The coach conversation is explicitly illustrative.

To reproduce, start the local frontend and run:

```bash
cd web/app
npx playwright install chromium
npm run capture:demo
```

`DEMO_BASE_URL` can select a different loopback port. The capture script blocks
requests to `/app`, non-GET requests and external origins, and fails if any are
attempted. It never reads a real athlete account. Screenshots go here; the WebM
recording goes to ignored `.tmp/demo-assets/` for review.

Review every image and recording before publication. Do not substitute a
screenshot from the real local application or publish Playwright traces from
private sessions. These fixtures demonstrate the interface; they do not prove
that a model generated a particular response or that coaching is effective.
