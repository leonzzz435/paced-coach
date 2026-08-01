import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";

import { renderToStaticMarkup } from "react-dom/server";

import CoachClarificationCard, {
  clearClarificationResumeKey,
  getOrCreateClarificationResumeKey,
} from "@/components/jobs/coach-clarification-card";

function memoryStorage(): Storage {
  const values = new Map<string, string>();
  return {
    get length() { return values.size; },
    clear: () => values.clear(),
    getItem: (key) => values.get(key) ?? null,
    key: (index) => [...values.keys()][index] ?? null,
    removeItem: (key) => { values.delete(key); },
    setItem: (key, value) => { values.set(key, value); },
  };
}

const html = renderToStaticMarkup(
  <CoachClarificationCard
    jobId="job-1"
    clarification={{
      question: "Which four days are reliably available?",
      reason_markdown: "This answer **materially changes** the weekly structure.",
      requested_field: "availability",
    }}
    onResumed={() => undefined}
  />,
);

assert.match(html, /Your coach needs one answer/);
assert.match(html, /Which four days are reliably available/);
assert.match(html, /<strong>materially changes<\/strong>/);
assert.match(html, /Continue building my plan/);
assert.match(html, /disabled=""/);

const storage = memoryStorage();
const firstAttemptKey = getOrCreateClarificationResumeKey("job-1", "availability", storage);
const ambiguousRetryKey = getOrCreateClarificationResumeKey("job-1", "availability", storage);
assert.equal(ambiguousRetryKey, firstAttemptKey, "ambiguous retries and reload recovery must reuse the request key");
assert.notEqual(
  getOrCreateClarificationResumeKey("job-1", "injury_status", storage),
  firstAttemptKey,
  "a distinct clarification must receive a distinct request key",
);
clearClarificationResumeKey("job-1", "availability", storage);
assert.notEqual(getOrCreateClarificationResumeKey("job-1", "availability", storage), firstAttemptKey);

const source = readFileSync(
  path.join(process.cwd(), "src/components/jobs/coach-clarification-card.tsx"),
  "utf8",
);
assert.match(source, /getOrCreateClarificationResumeKey/, "resume submissions need a durable idempotency key");
assert.match(source, /onStatusRecovery\?\.\(\)/, "ambiguous resume attempts must restart status recovery");
assert.match(source, /if \(!normalizedAnswer \|\| state === "sending"\) return/);
assert.match(source, /method: "POST"/);

const jobPageSource = readFileSync(path.join(process.cwd(), "src/app/app/jobs/[jobId]/page.tsx"), "utf8");
assert.match(jobPageSource, /resumeRecoveryUntilRef\.current = Date\.now\(\) \+ 10_000/);
assert.match(jobPageSource, /s\.status === "awaiting_input"[\s\S]*setTimeout\(poll, 1000\)/);

console.log("Head Coach clarification remains durable, accessible, and idempotent.");
