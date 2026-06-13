import { apiFetch } from "@/lib/api";
import { NextResponse } from "next/server";

export async function POST(req: Request) {
  const body = await req.json();
  const data = await apiFetch("/api/uploads/init", { method: "POST", body });
  return NextResponse.json(data);
}

