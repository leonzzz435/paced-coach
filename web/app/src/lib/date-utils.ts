import type { UiSeasonPlan, UiWeeklyPlan } from "@/lib/types/ui-blocks";

export function parseIsoDate(value?: string | null): Date | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function localYYYYMMDD(now = new Date()): string {
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

/**
 * Read the calendar date from an athlete-local ISO timestamp without first
 * converting it to UTC. Falling back to the browser clock keeps legacy and
 * job-result views useful when no athlete time context is available.
 */
export function athleteLocalYYYYMMDD(nowIso?: string | null): string {
  const localDate = nowIso?.match(/^(\d{4}-\d{2}-\d{2})(?:T|$)/)?.[1];
  return localDate ?? localYYYYMMDD();
}

export function getCurrentSeasonIndex(plan?: UiSeasonPlan | null, now = new Date()): number {
  if (!plan || plan.phases.length === 0) return 0;
  const currentIndex = plan.phases.findIndex((phase) => {
    const start = parseIsoDate(phase.start_date);
    const end = parseIsoDate(phase.end_date);
    return Boolean(start && end && start <= now && now <= end);
  });
  return currentIndex >= 0 ? currentIndex : 0;
}

export function getCurrentWeekIndex(plan?: UiWeeklyPlan | null, now = new Date()): number {
  if (!plan || plan.weeks.length === 0) return 0;
  const current = plan.weeks.findIndex((week) => {
    const start = parseIsoDate(week.start_date);
    const end = parseIsoDate(week.end_date);
    return Boolean(start && end && start <= now && now <= end);
  });
  if (current >= 0) return current;

  const next = plan.weeks.findIndex((week) => {
    const start = parseIsoDate(week.start_date);
    return Boolean(start && start >= now);
  });
  return next >= 0 ? next : 0;
}
