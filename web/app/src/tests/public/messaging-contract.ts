import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";

const appRoot = process.cwd();
const repoRoot = path.resolve(appRoot, "../..");

function readRepoFile(relativePath: string): string {
  return readFileSync(path.join(repoRoot, relativePath), "utf8");
}

const publicSurfaces = {
  readme: readRepoFile("README.md"),
  rootMetadata: readRepoFile("web/app/src/app/layout.tsx"),
  homeMetadata: readRepoFile("web/app/src/app/page.tsx"),
  demo: readRepoFile("web/app/src/app/demo/page.tsx"),
  socialPreview: readRepoFile("web/app/public/og.svg"),
};
const coachComposer = readRepoFile("web/app/src/components/coach-chat/coach-inbox-composer-bar.tsx");
const coachPage = readRepoFile("web/app/src/app/app/coach/page.tsx");
const coachCopy = readRepoFile("web/app/src/components/coach-chat/coach-inbox-parts.tsx");

for (const [surface, content] of Object.entries(publicSurfaces)) {
  assert.match(content, /no wearable required/i, `${surface} must state that no wearable is required`);
}

assert.doesNotMatch(
  [coachComposer, coachPage, coachCopy].join("\n"),
  /Strava|WHOOP|Connect Data Source|integration settings|connected activity|connected recovery|recap proposals|recap follow-ups/i,
  "coach surfaces must not expose removed connector or recap flows",
);

const combined = Object.values(publicSurfaces).join("\n");
assert.match(combined, /LLM key/i, "public messaging must identify a supported LLM key as required");
assert.match(combined, /goals/i, "public messaging must identify athlete-declared goals as coaching context");
assert.match(combined, /availability/i, "public messaging must identify athlete-declared availability as coaching context");
assert.match(combined, /constraints/i, "public messaging must identify athlete-declared constraints as coaching context");
assert.match(combined, /provider-free/i, "public messaging must state the provider-free product boundary");
assert.match(combined, /no external training-data connector|no activity-platform or recovery-device account/i);
assert.match(publicSurfaces.demo, /kpis:\s*\[\]/, "the public demo must not surface wearable-derived KPI fixtures");
assert.match(publicSurfaces.demo, /DEMO_SEASON_PLAN_BY_PERSONA/);
assert.match(publicSurfaces.demo, /DEMO_WEEKLY_PLAN_BY_PERSONA/);
assert.doesNotMatch(
  publicSurfaces.demo,
  /dashboard_kpis|analysis\.coach_action|ACWR|Recovery score|Sleep RHR|VO₂max/i,
  "the provider-free demo must not derive dashboard guidance from wearable-style fixture metrics",
);

for (const [surface, content] of Object.entries(publicSurfaces)) {
  assert.doesNotMatch(content, /Connected endurance coaching/i, `${surface} uses stale connector-first positioning`);
  assert.doesNotMatch(content, /paywalled dashboard/i, `${surface} uses stale competitor-first positioning`);
}

console.log("Public messaging keeps athlete value first and the release provider-free.");
