import type { WeeklyPlanV3 } from "@/components/plan-viewer/types";
import type { UiWeeklyPlan } from "@/lib/types/ui-blocks";

export function toDashboardWeeklyPlan(plan: UiWeeklyPlan | WeeklyPlanV3 | undefined): UiWeeklyPlan | undefined {
  if (!plan || plan.schema_version !== 3 || !("summary_markdown" in plan)) return plan as UiWeeklyPlan | undefined;
  const v3Plan = plan as WeeklyPlanV3;

  return {
    type: "weekly_plan",
    plan_id: v3Plan.plan_id,
    schema_version: 3,
    version: v3Plan.version,
    athlete_name: v3Plan.athlete_name,
    created_at: v3Plan.created_at,
    plan_brief: v3Plan.summary_markdown,
    global_blocks: [],
    global_nodes: [],
    weeks: v3Plan.weeks.map((week) => ({
      week_id: week.week_id,
      week_label: week.title,
      week_theme: week.intent_markdown,
      start_date: week.start_date,
      end_date: week.end_date,
      notes_blocks: [],
      notes_nodes: [],
      days: week.days.map((day) => ({
        day_id: day.day_id,
        date: day.date,
        day_label: day.label,
        focus_type: day.focus_type,
        workout_title: day.sessions[0]?.title ?? (day.intensity === "rest" ? "Recovery day" : day.label),
        primary_distance_km: day.sessions[0]?.distance_km ?? null,
        blocks: [],
        nodes: [],
        estimated_duration_min: day.total_duration_min,
        estimated_intensity: day.intensity,
        is_completed: day.is_completed,
      })),
    })),
  };
}
