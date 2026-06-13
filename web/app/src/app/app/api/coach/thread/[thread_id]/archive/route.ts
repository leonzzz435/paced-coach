import { apiFetch } from "@/lib/api";
import { apiProxyErrorResponse } from "@/lib/route_helpers";
import { NextResponse } from "next/server";

export async function POST(
  _req: Request,
  context: { params: Promise<{ thread_id: string }> },
) {
  try {
    const params = await context.params;
    const data = await apiFetch(`/api/coach/thread/${params.thread_id}/archive`, { method: "POST" });
    return NextResponse.json(data);
  } catch (err) {
    return apiProxyErrorResponse(err);
  }
}
