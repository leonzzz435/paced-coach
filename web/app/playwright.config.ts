import { defineConfig, devices } from "@playwright/test";

const baseURL = "http://127.0.0.1:13080";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: 2,
  reporter: "list",
  outputDir: "../../.tmp/playwright-results",
  use: {
    baseURL,
    timezoneId: "Europe/Berlin",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 1000 } } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
  webServer: {
    command: "npm run start -- --hostname 127.0.0.1 --port 13080",
    url: `${baseURL}/demo`,
    reuseExistingServer: false,
    env: { NEXT_TELEMETRY_DISABLED: "1", API_BASE_URL: "http://127.0.0.1:9" },
  },
});
