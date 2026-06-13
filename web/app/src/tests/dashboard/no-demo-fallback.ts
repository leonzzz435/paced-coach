import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";

function assertNoDemoFallback(relativePath: string): void {
  const source = readFileSync(path.join(process.cwd(), relativePath), "utf8");
  const bannedPatterns: Array<{ pattern: RegExp; message: string }> = [
    {
      pattern: /@\/lib\/demo\/demo-data/,
      message: "must not import demo fixtures into signed-in app pages",
    },
    {
      pattern: /\bDEMO_[A-Z_]+\b/,
      message: "must not reference demo fixture constants in signed-in app pages",
    },
    {
      pattern: /\bshowDemo\b/,
      message: "must not branch signed-in app pages into demo mode",
    },
    {
      pattern: /\bbuildDemoDashboardState\b/,
      message: "must not build demo dashboard state for signed-in users",
    },
  ];

  for (const { pattern, message } of bannedPatterns) {
    assert.equal(pattern.test(source), false, `${relativePath} ${message}.`);
  }
}

assertNoDemoFallback("src/app/app/page.tsx");
assertNoDemoFallback("src/app/app/plan/page.tsx");

console.log("Signed-in dashboard and plan pages do not fall back to demo fixtures.");
