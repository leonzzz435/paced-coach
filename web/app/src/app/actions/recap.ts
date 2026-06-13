"use server";

import { revalidatePath } from "next/cache";
import { apiFetch } from "@/lib/api";
import type { CoachTurnResponse } from "@/lib/types/coach";

export async function runWeeklyRecapAction() {
    // Generate a unique idempotency key for this recap attempt
    const idempotencyKey = `recap-manual-${Date.now()}-${Math.random().toString(36).substring(7)}`;

    const res = await apiFetch<CoachTurnResponse>(`/api/coach/turn`, {
        method: "POST",
        timeoutMs: null,
        body: {
            action: "recap",
            idempotency_key: idempotencyKey,
            message: "Generate my weekly recap.",
        }
    });

    revalidatePath("/app/plan");
    revalidatePath("/app");
    return res;
}
