import assert from "node:assert/strict";

import { formatPlanRangeLabel, getMonthGridColumnStartClass } from "@/lib/plan-calendar";

assert.equal(getMonthGridColumnStartClass(""), "");
assert.equal(getMonthGridColumnStartClass("2026-03-09"), "sm:col-start-1");
assert.equal(getMonthGridColumnStartClass("2026-03-10"), "sm:col-start-2");
assert.equal(getMonthGridColumnStartClass("2026-04-01"), "sm:col-start-3");
assert.equal(getMonthGridColumnStartClass("2026-04-02"), "sm:col-start-4");
assert.equal(getMonthGridColumnStartClass("2026-04-03"), "sm:col-start-5");
assert.equal(getMonthGridColumnStartClass("2026-04-04"), "sm:col-start-6");
assert.equal(getMonthGridColumnStartClass("2026-04-05"), "sm:col-start-7");

assert.equal(
    formatPlanRangeLabel("2026-05", [
        { date: "2026-05-04" },
        { date: "2026-05-31" },
    ]),
    "May 4-31, 2026",
);
assert.equal(
    formatPlanRangeLabel("2026-05", Array.from({ length: 31 }, (_, idx) => ({ date: `2026-05-${String(idx + 1).padStart(2, "0")}` }))),
    "May 2026",
);
assert.equal(formatPlanRangeLabel("2026-05", [{ date: "2026-05-04" }]), "May 4, 2026");

console.log("Plan calendar grid offset test passed.");
