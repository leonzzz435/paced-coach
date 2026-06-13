import { apiFetch } from "@/lib/api";
import { apiProxyErrorResponse } from "@/lib/route_helpers";
import { NextResponse } from "next/server";

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const data = await apiFetch("/api/analysis/run", { method: "POST", body });
    return NextResponse.json(data);
  } catch (err) {
    return apiProxyErrorResponse(err);
  }
}
