import { apiError } from "@/lib/api_errors";
import { backendAuthHeaders } from "@/lib/server-auth";

function apiBaseUrl(): string {
  const base = process.env.API_BASE_URL ?? "http://localhost:8000";
  return base.replace(/\/+$/, "");
}

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
const DEFAULT_API_TIMEOUT_MS = 30_000;

function isFetchFailure(err: unknown): boolean {
  if (!(err instanceof Error)) return false;
  const msg = (err.message || "").toLowerCase();
  return msg.includes("fetch failed") || msg.includes("networkerror") || msg.includes("econnrefused");
}

function isAbortError(err: unknown): boolean {
  return err instanceof Error && err.name === "AbortError";
}

export function resolveApiTimeoutMs(overrideMs?: number | null): number | null {
  if (overrideMs === null) {
    return null;
  }
  if (Number.isFinite(overrideMs) && (overrideMs ?? 0) > 0) {
    return overrideMs as number;
  }
  const raw = process.env.API_FETCH_TIMEOUT_MS;
  const parsed = raw ? Number.parseInt(raw, 10) : Number.NaN;
  return Number.isFinite(parsed) && parsed > 0 ? parsed : DEFAULT_API_TIMEOUT_MS;
}

export async function apiFetch<T>(
  path: string,
  init?: {
    method?: HttpMethod;
    body?: unknown;
    timeoutMs?: number | null;
  },
): Promise<T> {
  const authHeaders = await backendAuthHeaders();

  let res: Response;
  const timeoutMs = resolveApiTimeoutMs(init?.timeoutMs);
  const controller = timeoutMs === null ? null : new AbortController();
  const timeoutId = timeoutMs === null ? null : setTimeout(() => controller?.abort(), timeoutMs);
  try {
    res = await fetch(`${apiBaseUrl()}${path}`, {
      method: init?.method ?? "GET",
      headers: {
        "Content-Type": "application/json",
        ...authHeaders,
      },
      body: init?.body === undefined ? undefined : JSON.stringify(init.body),
      cache: "no-store",
      signal: controller?.signal,
    });
  } catch (err) {
    if (isAbortError(err)) {
      throw apiError(`API 504: backend request timed out after ${timeoutMs}ms`, 504, "request_timeout");
    }
    if (isFetchFailure(err)) {
      throw new Error("Backend API not reachable yet (is it still starting?)");
    }
    throw err;
  } finally {
    if (timeoutId !== null) {
      clearTimeout(timeoutId);
    }
  }

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw apiError(`API ${res.status}: ${text || res.statusText}`, res.status, text);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return (await res.json()) as T;
}
