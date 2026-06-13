import assert from "node:assert/strict";

import { buildSeasonProgressState } from "@/lib/season-progress";
import type { UiSeasonPlan } from "@/lib/types/ui-blocks";

const seasonPlan: UiSeasonPlan = {
    type: "season_plan",
    plan_id: "season-1",
    schema_version: 1,
    version: 1,
    athlete_name: "Test Athlete",
    start_date: "2026-03-04",
    end_date: "2026-10-25",
    phases: [
        {
            phase_id: "p1",
            title: "Base",
            start_date: "2026-03-04",
            end_date: "2026-03-29",
            summary: null,
            blocks: [],
        },
        {
            phase_id: "p2",
            title: "Build",
            start_date: "2026-03-30",
            end_date: "2026-04-20",
            summary: null,
            blocks: [],
        },
    ],
    global_blocks: [],
};

const state = buildSeasonProgressState(seasonPlan, "2026-03-05T12:00:00.000Z");

assert.ok(state);
assert.equal(state?.nowMs, new Date("2026-03-05T12:00:00.000Z").getTime());
assert.equal(state?.nextPhaseEndMs, new Date("2026-03-29").getTime());
assert.ok(state!.progress > 0);
assert.ok(state!.progress < 1);

console.log("Season progress time snapshot test passed.");
