import { apiFetch } from "@/lib/api";
import { apiProxyErrorResponse } from "@/lib/route_helpers";
import { NextResponse } from "next/server";

export async function PATCH(
  req: Request,
  context: { params: Promise<{ competitionId: string }> },
) {
  try {
    const params = await context.params;
    const body = await req.json();
    const data = await apiFetch(`/api/competitions/${params.competitionId}`, { method: "PATCH", body });
    return NextResponse.json(data);
  } catch (err) {
    return apiProxyErrorResponse(err);
  }
}

export async function DELETE(
  _req: Request,
  context: { params: Promise<{ competitionId: string }> },
) {
  try {
    const params = await context.params;
    await apiFetch(`/api/competitions/${params.competitionId}`, { method: "DELETE" });
    return new NextResponse(null, { status: 204 });
  } catch (err) {
    return apiProxyErrorResponse(err);
  }
}
