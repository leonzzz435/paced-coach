import type { UiDayPlan } from "@/lib/types/ui-blocks";

const GENERIC_TITLES = new Set([
    "session",
    "session details",
    "session overview",
    "training session",
    "workout",
    "workout details",
    "workout overview",
]);

function compactTitle(value?: string | null): string | null {
    const title = value?.trim();
    if (!title) return null;
    return GENERIC_TITLES.has(title.toLowerCase()) ? null : title;
}

export function getPrimaryWorkoutTitle(day: UiDayPlan): string | null {
    const workoutBlockTitle = compactTitle(day.blocks.find((block) => block.variant === "workout")?.title);
    return compactTitle(day.workout_title) || workoutBlockTitle || compactTitle(day.day_label) || compactTitle(day.focus_type);
}
