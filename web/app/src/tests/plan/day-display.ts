import assert from "node:assert/strict";

import { getPrimaryWorkoutTitle } from "@/lib/day-display";
import type { UiDayPlan } from "@/lib/types/ui-blocks";

const baseDay: UiDayPlan = {
    day_id: "2026-03-06",
    date: "2026-03-06",
    blocks: [],
};

assert.equal(
    getPrimaryWorkoutTitle({
        ...baseDay,
        workout_title: "Old easy run",
        blocks: [
            {
                type: "html",
                key: "main",
                variant: "workout",
                title: "Aerobic ride + tempo taste",
                content_html: "<p>Ride</p>",
            },
        ],
    }),
    "Old easy run",
);

assert.equal(
    getPrimaryWorkoutTitle({
        ...baseDay,
        day_label: "Aerobic ride + tempo taste",
        blocks: [
            {
                type: "html",
                key: "main",
                variant: "workout",
                title: "Session overview",
                content_html: "<p>Ride</p>",
            },
        ],
    }),
    "Aerobic ride + tempo taste",
);

assert.equal(
    getPrimaryWorkoutTitle({
        ...baseDay,
        workout_title: "Controlled aerobic ride",
    }),
    "Controlled aerobic ride",
);

assert.equal(
    getPrimaryWorkoutTitle({
        ...baseDay,
        focus_type: "endurance",
    }),
    "endurance",
);

assert.equal(getPrimaryWorkoutTitle(baseDay), null);
