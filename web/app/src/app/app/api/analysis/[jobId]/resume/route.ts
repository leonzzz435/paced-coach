import { apiFetch } from "@/lib/api";
import { apiProxyErrorResponse } from "@/lib/route_helpers";
import { NextResponse } from "next/server";

export async function POST(
  req: Request,
  context: { params: Promise<{ jobId: string }> },
) {
  try {
    const params = await context.params;
    const body = await req.json();
    const data = await apiFetch(`/api/analysis/${params.jobId}/resume`, {
      method: "POST",
      body,
    });
    return NextResponse.json(data, { status: 202 });
  } catch (err) {
    return apiProxyErrorResponse(err);
  }
}
