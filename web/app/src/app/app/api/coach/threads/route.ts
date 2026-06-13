import { apiFetch } from "@/lib/api";
import { apiProxyErrorResponse } from "@/lib/route_helpers";
import { NextResponse } from "next/server";

export async function GET(req: Request) {
  try {
    const url = new URL(req.url);
    const params = url.searchParams.toString();
    const path = params ? `/api/coach/threads?${params}` : "/api/coach/threads";
    const data = await apiFetch(path, { method: "GET" });
    return NextResponse.json(data);
  } catch (err) {
    return apiProxyErrorResponse(err);
  }
}
