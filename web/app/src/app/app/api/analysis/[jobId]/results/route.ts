import { apiFetch } from "@/lib/api";
import { apiProxyErrorResponse } from "@/lib/route_helpers";
import { NextResponse } from "next/server";

export async function GET(
  _req: Request,
  context: { params: Promise<{ jobId: string }> },
) {
  try {
    const params = await context.params;
    const data = await apiFetch(`/api/analysis/${params.jobId}/results`, {
      method: "GET",
    });
    return NextResponse.json(data);
  } catch (err) {
    return apiProxyErrorResponse(err);
  }
}
