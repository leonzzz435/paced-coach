import { NextResponse } from "next/server";

import { apiFetch } from "@/lib/api";
import { apiProxyErrorResponse } from "@/lib/route_helpers";

export async function GET() {
  try {
    const data = await apiFetch("/api/weekly-recap/latest", { method: "GET" });
    return NextResponse.json(data);
  } catch (err) {
    return apiProxyErrorResponse(err);
  }
}
