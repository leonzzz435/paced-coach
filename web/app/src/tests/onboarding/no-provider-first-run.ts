import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";

function readSource(relativePath: string): string {
  return readFileSync(path.join(process.cwd(), relativePath), "utf8");
}

const generationPage = readSource("src/app/app/new/page.tsx");
const planPage = readSource("src/app/app/plan/page.tsx");

assert.doesNotMatch(generationPage, /Draft Mode/, "generation must not frame declared-context coaching as a draft");
assert.doesNotMatch(planPage, /Draft Mode/, "empty plan state must not frame declared-context coaching as a draft");
assert.match(generationPage, /No wearable (?:is )?required/i, "generation must say the provider-free path is complete");
assert.match(generationPage, /saved profile/i, "generation must identify the saved athlete profile as baseline context");
assert.match(generationPage, /race calendar/i, "generation must identify goals or races as baseline context");
assert.match(generationPage, /contextState !== "loaded"/, "generation must wait for saved context to load successfully");
assert.match(generationPage, /Retry loading context/, "a failed context load must offer a non-destructive retry");
assert.match(
  generationPage,
  /saved profile and race context are unchanged/i,
  "generation errors must confirm that saved context was preserved",
);
assert.doesNotMatch(generationPage, /integrations|Strava|WHOOP/i, "generation must not load or advertise connectors");
assert.doesNotMatch(
  generationPage,
  /generationDisabled\s*=.*(?:hasOperationalTrainingProvider|hasLinkedTrainingProvider)/,
  "provider state must not disable plan generation",
);

console.log("Provider-free first run stays complete, retryable, and independent of connector state.");
