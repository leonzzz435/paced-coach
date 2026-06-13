type CoachTurnProxyDeps = {
  fetchFn: typeof fetch;
  timeoutMs: number | null;
};

export async function proxyCoachTurn(req: Request, deps?: Partial<CoachTurnProxyDeps>) {
  try {
    const fetchFn = deps?.fetchFn ?? fetch;

    const bodyText = await req.text();
    const apiBase = (process.env.API_BASE_URL ?? "http://localhost:8000").replace(/\/+$/, "");
    const timeoutMs = deps?.timeoutMs ?? null;
    const controller = timeoutMs === null ? null : new AbortController();
    const timeoutId = timeoutMs === null ? null : setTimeout(() => controller?.abort(), timeoutMs);
    let upstream: Response;
    try {
      upstream = await fetchFn(`${apiBase}/api/coach/turn`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream, application/json",
        },
        body: bodyText,
        cache: "no-store",
        signal: controller?.signal,
      });
    } finally {
      if (timeoutId !== null) {
        clearTimeout(timeoutId);
      }
    }

    const headers = new Headers();
    const contentType = upstream.headers.get("content-type");
    if (contentType) headers.set("Content-Type", contentType);
    headers.set("Cache-Control", upstream.headers.get("cache-control") ?? "no-store");
    if (contentType?.includes("text/event-stream")) {
      headers.set("Connection", "keep-alive");
      headers.set("X-Accel-Buffering", "no");
    }

    return new Response(upstream.body, {
      status: upstream.status,
      headers,
    });
  } catch (err) {
    if (err instanceof Error && err.name === "AbortError") {
      return new Response(JSON.stringify({ detail: "Coach turn upstream timed out" }), {
        status: 504,
        headers: {
          "Content-Type": "application/json",
          "Cache-Control": "no-store",
        },
      });
    }
    const detail = err instanceof Error ? err.message : "Failed to proxy coach turn request";
    return new Response(JSON.stringify({ detail }), {
      status: 502,
      headers: {
        "Content-Type": "application/json",
        "Cache-Control": "no-store",
      },
    });
  }
}

export async function POST(req: Request) {
  return proxyCoachTurn(req);
}
