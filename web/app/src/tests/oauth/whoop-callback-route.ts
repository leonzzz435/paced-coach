import assert from "node:assert/strict";

import { proxyWhoopOauthCallback } from "../../app/app/api/oauth/whoop/callback/route";

async function testSuccessfulCallbackRedirectsToPublicCompletionPage(): Promise<void> {
  const response = await proxyWhoopOauthCallback(
    new Request("http://localhost:3000/app/api/oauth/whoop/callback?code=abc&state=xyz"),
    {
      apiBaseUrl: "http://localhost:8000",
      fetchFn: async (input) => {
        assert.equal(
          String(input),
          "http://localhost:8000/api/oauth/whoop/callback?code=abc&state=xyz",
          "Expected callback query params to be proxied upstream",
        );
        return new Response(null, { status: 200 });
      },
    },
  );

  assert.equal(response.status, 307);
  assert.equal(response.headers.get("location"), "http://localhost:3000/whoop/complete?connected=whoop");
}

async function testFailedCallbackRedirectsToPublicCompletionErrorPage(): Promise<void> {
  const response = await proxyWhoopOauthCallback(
    new Request("http://localhost:3000/app/api/oauth/whoop/callback?error=access_denied"),
    {
      apiBaseUrl: "http://localhost:8000",
      fetchFn: async () => new Response(null, { status: 400 }),
    },
  );

  assert.equal(response.status, 307);
  assert.equal(response.headers.get("location"), "http://localhost:3000/whoop/complete?oauth_error=whoop");
}

async function run(): Promise<void> {
  await testSuccessfulCallbackRedirectsToPublicCompletionPage();
  await testFailedCallbackRedirectsToPublicCompletionErrorPage();
  console.log("WHOOP callback route redirect tests passed.");
}

run();
