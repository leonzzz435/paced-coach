import { proxyCoachTurn } from "../../app/app/api/coach/turn/route";

function assertCondition(condition: boolean, message: string): void {
  if (!condition) {
    throw new Error(message);
  }
}

async function testProxyPassesThroughSseResponses(): Promise<void> {
  const response = await proxyCoachTurn(new Request("http://localhost/app/api/coach/turn", { method: "POST", body: "{}" }), {
    fetchFn: async () =>
      new Response("event: done\n\n", {
        status: 200,
        headers: {
          "content-type": "text/event-stream",
          "cache-control": "no-cache",
        },
      }),
  });

  assertCondition(response.status === 200, "Expected passthrough status code");
  assertCondition(response.headers.get("Content-Type")?.includes("text/event-stream") === true, "SSE content type should be preserved");
  assertCondition(response.headers.get("Connection") === "keep-alive", "SSE connection header should be set");
  assertCondition(response.headers.get("X-Accel-Buffering") === "no", "SSE buffering header should be set");
}

async function testProxyReturnsDeterministicJsonOnFetchFailure(): Promise<void> {
  const response = await proxyCoachTurn(new Request("http://localhost/app/api/coach/turn", { method: "POST", body: "{}" }), {
    fetchFn: async () => {
      throw new Error("upstream unavailable");
    },
  });
  const payload = (await response.json()) as { detail?: string };

  assertCondition(response.status === 502, "Fetch failures should return 502");
  assertCondition(payload.detail === "upstream unavailable", "Error payload should surface fetch failure detail");
}

async function testProxyOmitsAuthorizationInLocalMode(): Promise<void> {
  let authorizationHeader: string | null = "not-inspected";
  const response = await proxyCoachTurn(new Request("http://localhost/app/api/coach/turn", { method: "POST", body: "{}" }), {
    fetchFn: async (_input, init) => {
      const headers = new Headers(init?.headers);
      authorizationHeader = headers.get("Authorization");
      return new Response("{}", { status: 200, headers: { "content-type": "application/json" } });
    },
  });

  assertCondition(response.status === 200, "Local mode should proxy without auth token");
  assertCondition(authorizationHeader === null, "Local mode must not send an Authorization header");
}

async function testProxyReturns504OnUpstreamTimeout(): Promise<void> {
  const response = await proxyCoachTurn(new Request("http://localhost/app/api/coach/turn", { method: "POST", body: "{}" }), {
    timeoutMs: 5,
    fetchFn: async (_input, init) =>
      new Promise<Response>((_resolve, reject) => {
        const signal = init?.signal as AbortSignal | undefined;
        if (!signal) {
          reject(new Error("Missing abort signal"));
          return;
        }
        signal.addEventListener("abort", () => {
          const abortError = new Error("aborted");
          abortError.name = "AbortError";
          reject(abortError);
        });
      }),
  });
  const payload = (await response.json()) as { detail?: string };

  assertCondition(response.status === 504, "Timeouts should return 504");
  assertCondition(payload.detail === "Coach turn upstream timed out", "Timeout message should be deterministic");
}

async function run(): Promise<void> {
  await testProxyPassesThroughSseResponses();
  await testProxyReturnsDeterministicJsonOnFetchFailure();
  await testProxyOmitsAuthorizationInLocalMode();
  await testProxyReturns504OnUpstreamTimeout();
  console.log("Coach turn route proxy tests passed.");
}

run();
