import { NextResponse } from "next/server";

type WhoopOauthCallbackDeps = {
  apiBaseUrl?: string;
  fetchFn?: typeof fetch;
};

function buildCompletionRedirectUrl(requestUrl: URL, { success }: { success: boolean }): URL {
  const redirectUrl = new URL("/whoop/complete", requestUrl);
  redirectUrl.searchParams.set(success ? "connected" : "oauth_error", "whoop");
  return redirectUrl;
}

export async function proxyWhoopOauthCallback(req: Request, deps?: WhoopOauthCallbackDeps) {
  const url = new URL(req.url);
  const qs = url.searchParams.toString();
  const apiBase = (deps?.apiBaseUrl ?? process.env.API_BASE_URL ?? "http://localhost:8000").replace(/\/+$/, "");
  const upstream = qs ? `${apiBase}/api/oauth/whoop/callback?${qs}` : `${apiBase}/api/oauth/whoop/callback`;
  const res = await (deps?.fetchFn ?? fetch)(upstream, {
    method: "GET",
    redirect: "manual",
    cache: "no-store",
  });

  return NextResponse.redirect(buildCompletionRedirectUrl(url, { success: res.ok }));
}

export async function GET(req: Request) {
  return proxyWhoopOauthCallback(req);
}
