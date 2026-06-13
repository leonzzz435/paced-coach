import { NextResponse } from "next/server";

import { isApiError } from "@/lib/api_errors";

export function apiProxyErrorResponse(err: unknown) {
  if (isApiError(err) && typeof err.status === "number") {
    const body = err.bodyText ?? err.message ?? "Upstream error";
    return new NextResponse(body, {
      status: err.status,
      headers: { "Content-Type": "application/json" },
    });
  }
  const message = err instanceof Error ? err.message : "Unknown error";
  return NextResponse.json({ detail: message }, { status: 500 });
}

