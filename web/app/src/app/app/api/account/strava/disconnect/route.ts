import { apiFetch } from "@/lib/api";
import { NextResponse } from "next/server";

export async function POST() {
  const data = await apiFetch("/api/account/strava/disconnect", { method: "POST" });
  return NextResponse.json(data);
}
