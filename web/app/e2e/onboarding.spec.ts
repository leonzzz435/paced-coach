import { expect, test } from "@playwright/test";

const profile = {
  physiology: {},
  preferences: { sports: ["run"], timezone: "Europe/Berlin" },
  availability: { days_per_week: 4, time_windows: "Mon/Wed 45m, Sat 90m, Sun 60m" },
  goals: { primary_goal: "Finish a half marathon comfortably", notes: "Synthetic browser acceptance athlete" },
};

test("profile edits wait for stored data and cannot race an in-flight save", async ({ page }) => {
  let releaseLoad!: () => void;
  let releaseSave!: () => void;
  const loadGate = new Promise<void>((resolve) => { releaseLoad = resolve; });
  const saveGate = new Promise<void>((resolve) => { releaseSave = resolve; });
  let savedProfile = profile;
  await page.route("**/app/api/athlete-profile", async (route) => {
    if (route.request().method() === "PUT") {
      savedProfile = route.request().postDataJSON().profile;
      await saveGate;
    } else {
      await loadGate;
    }
    await route.fulfill({ json: { user_id: "synthetic-athlete", profile: savedProfile } });
  });

  await page.goto("/app/profile");
  const goal = page.getByRole("textbox", { name: "Primary goal", exact: true });
  await expect(goal).toBeDisabled();
  await expect(page.getByRole("button", { name: "Save profile", exact: true })).toBeDisabled();
  releaseLoad();
  await expect(goal).toBeEnabled();
  await expect(goal).toHaveValue(profile.goals.primary_goal);
  await goal.fill("A saved goal with all my constraints");
  await page.getByRole("button", { name: "Save profile", exact: true }).click();
  await expect(goal).toBeDisabled();
  releaseSave();
  await expect(goal).toBeEnabled();
  await page.reload();
  await expect(goal).toHaveValue("A saved goal with all my constraints");
});

test("a failed initial load cannot overwrite an existing profile with defaults", async ({ page }) => {
  let loads = 0;
  let saves = 0;
  await page.route("**/app/api/athlete-profile", async (route) => {
    if (route.request().method() === "PUT") saves += 1;
    else loads += 1;
    if (loads === 1) {
      await route.fulfill({ status: 503, json: { detail: "Synthetic load failure" } });
      return;
    }
    await route.fulfill({ json: { user_id: "synthetic-athlete", profile } });
  });

  await page.goto("/app/profile");
  await expect(page.getByRole("alert").filter({ hasText: "Failed to load athlete profile" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Save profile", exact: true })).toBeDisabled();
  const goal = page.getByRole("textbox", { name: "Primary goal", exact: true });
  await expect(goal).toBeDisabled();
  await page.getByRole("button", { name: "Retry loading profile", exact: true }).click();
  await expect(goal).toBeEnabled();
  await expect(goal).toHaveValue(profile.goals.primary_goal);
  expect(saves).toBe(0);
});

test("a failed profile save preserves edits and can be retried", async ({ page }) => {
  let saves = 0;
  let savedProfile = profile;
  await page.route("**/app/api/athlete-profile", async (route) => {
    if (route.request().method() === "PUT") {
      saves += 1;
      if (saves === 1) {
        await route.fulfill({ status: 503, json: { detail: "Synthetic temporary failure" } });
        return;
      }
      savedProfile = route.request().postDataJSON().profile;
    }
    await route.fulfill({ json: { user_id: "synthetic-athlete", profile: savedProfile } });
  });

  await page.goto("/app/profile");
  const goal = page.getByRole("textbox", { name: "Primary goal", exact: true });
  await expect(goal).toHaveValue(profile.goals.primary_goal);
  await goal.fill("Finish my first trail race");
  await page.getByRole("button", { name: "Save profile", exact: true }).click();
  await expect(goal).toHaveValue("Finish my first trail race");
  await page.getByRole("button", { name: "Retry save", exact: true }).click();
  await expect(page.getByRole("button", { name: "Saved", exact: true })).toBeVisible();
  await page.reload();
  await expect(goal).toHaveValue("Finish my first trail race");
  expect(saves).toBe(2);
});

test("missing API key prevents generation and explains the next step", async ({ page }) => {
  let generationRequests = 0;
  await page.route("**/app/api/athlete-profile", (route) =>
    route.fulfill({ json: { user_id: "synthetic-athlete", profile } }),
  );
  await page.route("**/app/api/competitions", (route) => route.fulfill({ json: [] }));
  await page.route("**/app/api/dashboard/state", (route) => route.fulfill({
    json: { first_run: { llm_ready: false, blockers: ["Set OPENAI_API_KEY in .env and restart the API."] } },
  }));
  await page.route("**/app/api/analysis/run", (route) => {
    generationRequests += 1;
    return route.fulfill({ status: 500, json: { detail: "Generation must not be requested" } });
  });

  await page.goto("/app/new");
  await expect(page.getByRole("button", { name: "Add an LLM key first" })).toBeDisabled();
  await expect(page.getByText("Set OPENAI_API_KEY in .env and restart the API.")).toBeVisible();
  expect(generationRequests).toBe(0);
});
