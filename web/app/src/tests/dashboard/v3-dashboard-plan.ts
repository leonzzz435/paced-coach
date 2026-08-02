import assert from "node:assert/strict";

import { DEMO_WEEKLY_PLAN_BY_PERSONA } from "../../lib/demo/fixtures/v3/weekly";
import { toDashboardWeeklyPlan } from "../../lib/dashboard-plan";

const source = DEMO_WEEKLY_PLAN_BY_PERSONA["hybrid-operator"];
const projected = toDashboardWeeklyPlan(source);

assert.ok(projected);
assert.equal(projected.weeks.length, 4);
assert.equal(projected.weeks.flatMap((week) => week.days).length, 28);
assert.equal(projected.weeks[0].week_label, source.weeks[0].title);
assert.equal(projected.weeks[0].days[0].workout_title, source.weeks[0].days[0].sessions[0]?.title);
assert.equal(projected.weeks[0].days[0].estimated_duration_min, source.weeks[0].days[0].total_duration_min);
assert.equal(projected.weeks[0].days[0].estimated_intensity, source.weeks[0].days[0].intensity);

console.log("Schema v3 execution plans project into the compact dashboard calendar without legacy block parsing.");
