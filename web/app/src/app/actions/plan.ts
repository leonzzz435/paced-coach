"use server";

import { revalidatePath } from "next/cache";

import { apiFetch } from "@/lib/api";
import { activeWeeklyDayCompletionPath } from "@/lib/plan-api-paths";

export async function toggleDayCompletionAction(dayId: string, isCompleted: boolean) {
    await apiFetch(activeWeeklyDayCompletionPath(dayId), {
        method: "POST",
        body: { is_completed: isCompleted },
    });

    // Invalidate the cache for the plan viewer so the UI component
    // re-fetches the updated ActiveWeeklyPlan from the database
    revalidatePath("/app/plan");
    revalidatePath("/app");
}
