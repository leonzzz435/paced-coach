import { NextResponse } from "next/server";

import { apiFetch } from "@/lib/api";
import { apiProxyErrorResponse } from "@/lib/route_helpers";

export const maxDuration = 900;

function normalizeAthleteCheckIn(value: unknown): string | undefined {
  if (typeof value !== "string") return undefined;
  const normalized = value.trim();
  return normalized ? normalized.slice(0, 2000) : undefined;
}

async function readRequestBody(request: Request): Promise<{ athlete_check_in?: unknown }> {
  const rawBody = await request.text();
  if (!rawBody.trim()) return {};

  const contentType = request.headers.get("content-type") ?? "";
  if (!contentType.toLowerCase().includes("application/json")) {
    throw new Response(JSON.stringify({ detail: "Daily sync requests must be JSON." }), {
      status: 415,
      headers: { "Content-Type": "application/json" },
    });
  }

  try {
    const parsed = JSON.parse(rawBody) as unknown;
    if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new Error("Daily sync request body must be a JSON object.");
    }
    return parsed as { athlete_check_in?: unknown };
  } catch (error) {
    throw new Response(
      JSON.stringify({
        detail: error instanceof Error ? error.message : "Invalid daily sync JSON body.",
      }),
      {
        status: 400,
        headers: { "Content-Type": "application/json" },
      },
    );
  }
}

export async function POST(request: Request) {
  try {
    const requestBody = await readRequestBody(request);
    const athleteCheckIn = normalizeAthleteCheckIn(requestBody.athlete_check_in);
    const data = await apiFetch("/api/daily/run", {
      method: "POST",
      body: athleteCheckIn ? { athlete_check_in: athleteCheckIn } : {},
      timeoutMs: null,
    });
    return NextResponse.json(data);
  } catch (err) {
    if (err instanceof Response) return err;
    return apiProxyErrorResponse(err);
  }
}
