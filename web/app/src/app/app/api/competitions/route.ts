import { apiFetch } from "@/lib/api";
import { apiProxyErrorResponse } from "@/lib/route_helpers";
import { NextResponse } from "next/server";

export async function GET() {
  try {
    const data = await apiFetch("/api/competitions", { method: "GET" });
    return NextResponse.json(data);
  } catch (err) {
    return apiProxyErrorResponse(err);
  }
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const data = await apiFetch("/api/competitions", { method: "POST", body });
    return NextResponse.json(data);
  } catch (err) {
    return apiProxyErrorResponse(err);
  }
}
