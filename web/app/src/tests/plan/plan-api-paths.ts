import { activeWeeklyDayCompletionPath } from "../../lib/plan-api-paths";

function assertCondition(condition: boolean, message: string): void {
  if (!condition) {
    throw new Error(message);
  }
}

function run(): void {
  const path = activeWeeklyDayCompletionPath("2026-03-05");
  assertCondition(
    path === "/api/plans/active/weekly/days/2026-03-05/completion",
    `Unexpected completion path: ${path}`,
  );
  console.log("Plan API path tests passed.");
}

run();
