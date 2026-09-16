import { expect, test } from "@playwright/test";

test("schema-v3 calendar can be explored without writing local data", async ({ page }) => {
  const errors: string[] = [];
  const writes: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("request", (request) => {
    if (!["GET", "HEAD"].includes(request.method())) writes.push(request.url());
  });

  await page.goto("/demo?shot=plan");
  const calendar = page.getByRole("region", { name: "28-day training calendar" });
  await expect(calendar.getByRole("button")).toHaveCount(28);
  const day = calendar.getByRole("button").nth(4);
  await day.click();
  await expect(day).toHaveAttribute("aria-pressed", "true");
  const complete = page.getByRole("button", { name: "Mark complete", exact: true });
  await complete.click();
  await expect(page.getByRole("button", { name: "Completed", exact: true })).toBeVisible();
  await page.reload();
  await calendar.getByRole("button").nth(4).click();
  await expect(complete).toBeVisible();

  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
  expect(errors).toEqual([]);
  expect(writes).toEqual([]);
  await expect(page.getByText(/ACWR|HRV \(overnight\)|acute 88/)).toHaveCount(0);
});

test("demo dashboard checkmarks and navigation stay within the synthetic preview", async ({ page }) => {
  const localAppReads: string[] = [];
  const writes: string[] = [];
  page.on("request", (request) => {
    if (new URL(request.url()).pathname.startsWith("/app")) localAppReads.push(request.url());
    if (!["GET", "HEAD"].includes(request.method())) writes.push(request.url());
  });
  await page.goto("/demo");
  const checkmark = page.getByRole("button", { name: "Mark as done", exact: true }).first();
  await checkmark.click();
  await expect(page.getByRole("button", { name: "Mark as not done", exact: true })).toHaveCount(1);
  await page.getByRole("link", { name: "Preview coach", exact: true }).click();
  await expect(page).toHaveURL(/\/demo#coach$/);
  await page.reload();
  await expect(page.getByRole("button", { name: "Mark as not done", exact: true })).toHaveCount(0);
  expect(writes).toEqual([]);
  expect(localAppReads).toEqual([]);
});

test("public demo identifies synthetic context and leads to the local app", async ({ page }) => {
  await page.goto("/demo");
  await expect(page.getByRole("heading", { level: 1 }).first()).toHaveText(
    "Your season. Your next 28 days. One coach that knows the plan.",
  );
  await expect(page.getByText("No wearable required", { exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Open local app" })).toHaveAttribute("href", "/app");
  await expect(page.getByText(/Illustrative conversation, not a recorded model response/)).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
});
