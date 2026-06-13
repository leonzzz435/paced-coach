import assert from "node:assert/strict";

import { proxyStravaOauthCallback } from "../../app/app/api/oauth/strava/callback/route";

async function testSuccessfulCallbackRedirectsToPublicCompletionPage(): Promise<void> {
  const response = await proxyStravaOauthCallback(
    new Request("http://localhost:3000/app/api/oauth/strava/callback?code=abc&state=xyz&scope=activity:read_all"),
    {
      apiBaseUrl: "http://localhost:8000",
      fetchFn: async (input) => {
        assert.equal(
          String(input),
          "http://localhost:8000/api/oauth/strava/callback?code=abc&state=xyz&scope=activity%3Aread_all",
          "Expected callback query params to be proxied upstream",
        );
        return new Response(null, { status: 200 });
      },
    },
  );

  assert.equal(response.status, 307);
  assert.equal(response.headers.get("location"), "http://localhost:3000/strava/complete?connected=strava");
}

async function testFailedCallbackRedirectsToPublicCompletionErrorPage(): Promise<void> {
  const response = await proxyStravaOauthCallback(
    new Request("http://localhost:3000/app/api/oauth/strava/callback?error=access_denied"),
    {
      apiBaseUrl: "http://localhost:8000",
      fetchFn: async () => new Response(null, { status: 400 }),
    },
  );

  assert.equal(response.status, 307);
  assert.equal(response.headers.get("location"), "http://localhost:3000/strava/complete?oauth_error=strava");
}

async function run(): Promise<void> {
  await testSuccessfulCallbackRedirectsToPublicCompletionPage();
  await testFailedCallbackRedirectsToPublicCompletionErrorPage();
  console.log("Strava callback route redirect tests passed.");
}

run();
