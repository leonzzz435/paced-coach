import assert from "node:assert/strict";

import { POST } from "@/app/app/api/daily/run/route";

async function testRejectsNonJsonBodies(): Promise<void> {
  const response = await POST(
    new Request("http://localhost/app/api/daily/run", {
      method: "POST",
      headers: { "content-type": "text/plain" },
      body: "athlete_check_in=ok",
    }),
  );
  const payload = (await response.json()) as { detail?: string };

  assert.equal(response.status, 415);
  assert.equal(payload.detail, "Daily sync requests must be JSON.");
}

async function testRejectsInvalidJsonBodies(): Promise<void> {
  const response = await POST(
    new Request("http://localhost/app/api/daily/run", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: "{",
    }),
  );
  const payload = (await response.json()) as { detail?: string };

  assert.equal(response.status, 400);
  assert.match(payload.detail ?? "", /JSON|property|input/i);
}

async function run(): Promise<void> {
  await testRejectsNonJsonBodies();
  await testRejectsInvalidJsonBodies();
  console.log("Daily run route request validation tests passed.");
}

run();
