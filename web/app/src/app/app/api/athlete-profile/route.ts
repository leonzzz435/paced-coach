import { apiFetch } from "@/lib/api";
import { apiProxyErrorResponse } from "@/lib/route_helpers";
import { NextResponse } from "next/server";

export async function GET() {
  try {
    const data = await apiFetch("/api/athlete-profile", { method: "GET" });
    return NextResponse.json(data);
  } catch (err) {
    return apiProxyErrorResponse(err);
  }
}

export async function PUT(req: Request) {
  try {
    const body = await req.json();
    const data = await apiFetch("/api/athlete-profile", { method: "PUT", body });
    return NextResponse.json(data);
  } catch (err) {
    return apiProxyErrorResponse(err);
  }
}
