import { apiFetch } from "@/lib/api";
import { isApiError } from "@/lib/api_errors";
import { NextResponse } from "next/server";

function readApiErrorPayload(err: unknown): object {
  if (!isApiError(err)) {
    return { detail: "Unexpected error" };
  }
  if (!err.bodyText) {
    return { detail: err.message };
  }
  try {
    return JSON.parse(err.bodyText) as object;
  } catch {
    return { detail: err.bodyText || err.message };
  }
}

export async function DELETE() {
  try {
    const data = await apiFetch("/api/account", { method: "DELETE" });
    return NextResponse.json(data);
  } catch (err) {
    if (isApiError(err)) {
      return NextResponse.json(readApiErrorPayload(err), { status: err.status ?? 500 });
    }
    throw err;
  }
}
