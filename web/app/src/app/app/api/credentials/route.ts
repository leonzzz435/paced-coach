import { apiFetch } from "@/lib/api";
import { NextResponse } from "next/server";

export async function POST(req: Request) {
  const body = await req.json();
  const data = await apiFetch("/api/credentials", { method: "POST", body });
  return NextResponse.json(data);
}

export async function GET() {
  const data = await apiFetch("/api/credentials", { method: "GET" });
  return NextResponse.json(data);
}

export async function DELETE() {
  const data = await apiFetch("/api/credentials", { method: "DELETE" });
  return NextResponse.json(data);
}

