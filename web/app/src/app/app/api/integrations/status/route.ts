import { apiFetch } from "@/lib/api";
import { NextResponse } from "next/server";

export async function GET() {
  const data = await apiFetch("/api/integrations/status", { method: "GET" });
  return NextResponse.json(data);
}

