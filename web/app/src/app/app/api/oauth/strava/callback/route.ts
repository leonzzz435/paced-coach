import { NextResponse } from "next/server";

type StravaOauthCallbackDeps = {
  apiBaseUrl?: string;
  fetchFn?: typeof fetch;
};

function buildCompletionRedirectUrl(requestUrl: URL, { success }: { success: boolean }): URL {
  const redirectUrl = new URL("/strava/complete", requestUrl);
  redirectUrl.searchParams.set(success ? "connected" : "oauth_error", "strava");
  return redirectUrl;
}

export async function proxyStravaOauthCallback(req: Request, deps?: StravaOauthCallbackDeps) {
  const url = new URL(req.url);
  const qs = url.searchParams.toString();
  const apiBase = (deps?.apiBaseUrl ?? process.env.API_BASE_URL ?? "http://localhost:8000").replace(/\/+$/, "");
  const upstream = qs ? `${apiBase}/api/oauth/strava/callback?${qs}` : `${apiBase}/api/oauth/strava/callback`;
  const res = await (deps?.fetchFn ?? fetch)(upstream, {
    method: "GET",
    redirect: "manual",
    cache: "no-store",
  });

  return NextResponse.redirect(buildCompletionRedirectUrl(url, { success: res.ok }));
}

export async function GET(req: Request) {
  return proxyStravaOauthCallback(req);
}
