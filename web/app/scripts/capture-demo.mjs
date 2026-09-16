// Capture only the synthetic public route. Never navigate into /app.
import { chromium, expect } from "@playwright/test";
import { mkdir, rename } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
const origin = new URL(process.env.DEMO_BASE_URL ?? "http://127.0.0.1:3000");
if (!["127.0.0.1", "localhost"].includes(origin.hostname) || origin.username || origin.password) {
  throw new Error("Demo capture requires a loopback origin without credentials.");
}
const assets = path.join(root, "docs/assets/readme");
const recordings = path.join(root, ".tmp/demo-assets");
await mkdir(assets, { recursive: true });
await mkdir(recordings, { recursive: true });

const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
  timezoneId: "Europe/Berlin",
  reducedMotion: "reduce",
  recordVideo: { dir: recordings, size: { width: 1440, height: 1000 } },
});
const page = await context.newPage();
const forbidden = [];
await context.route("**/*", async (route) => {
  const request = route.request();
  const url = new URL(request.url());
  if (url.origin !== origin.origin || url.pathname.startsWith("/app") || request.method() !== "GET") {
    forbidden.push(`${request.method()} ${url.pathname}`);
    await route.abort();
    return;
  }
  await route.continue();
});
try {
  for (const shot of ["hero", "dashboard", "plan", "coach"]) {
    await page.goto(new URL(`/demo?shot=${shot}`, origin).href);
    await page.locator(`[data-screenshot="${shot}"]`).waitFor();
    await page.evaluate(() => document.fonts.ready);
    if (shot === "plan") {
      await expect(page.getByRole("region", { name: "28-day training calendar" }).getByRole("button")).toHaveCount(28);
    }
    await page.locator(`[data-screenshot="${shot}"]`).screenshot({ path: path.join(assets, `paced-coach-${shot}.png`) });
    // Intentional reading time in the demonstration recording, not a test wait.
    await page.waitForTimeout(3500);
    if (shot === "plan") {
      const calendar = page.getByRole("region", { name: "28-day training calendar" });
      await calendar.getByRole("button").nth(5).click();
      await page.waitForTimeout(2500);
      await calendar.getByRole("button").nth(10).click();
      await page.waitForTimeout(2500);
    }
  }
  if (forbidden.length) throw new Error(`Capture attempted non-demo requests: ${forbidden.join(", ")}`);
} finally {
  const video = page.video();
  await context.close();
  await browser.close();
  if (video) await rename(await video.path(), path.join(recordings, "paced-coach-synthetic-demo.webm"));
}
console.log("Synthetic screenshots: docs/assets/readme; review video: .tmp/demo-assets/paced-coach-synthetic-demo.webm");
