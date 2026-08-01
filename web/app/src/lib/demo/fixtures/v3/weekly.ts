import type { WeeklyPlanV3 } from "@/components/plan-viewer/types";
import type { DemoPersonaId } from "@/lib/demo/personas";

const START = new Date("2026-08-03T00:00:00Z");

function isoDay(offset: number): string {
  const value = new Date(START);
  value.setUTCDate(value.getUTCDate() + offset);
  return value.toISOString().slice(0, 10);
}

function buildWeeks(): WeeklyPlanV3["weeks"] {
  return Array.from({ length: 4 }, (_, weekIndex) => {
    const weekStartOffset = weekIndex * 7;
    return {
      week_id: `week-${weekIndex + 1}`,
      title: ["Set the rhythm", "Repeat with confidence", "Add controlled pressure", "Consolidate and learn"][weekIndex],
      start_date: isoDay(weekStartOffset),
      end_date: isoDay(weekStartOffset + 6),
      intent_markdown: [
        "Establish a calm weekly rhythm and finish every aerobic session with reserve.",
        "Repeat the structure before adding complexity.",
        "Introduce one controlled progression while protecting recovery days.",
        "Hold the gains, reduce decision load, and capture honest feedback.",
      ][weekIndex],
      blocks: [],
      days: Array.from({ length: 7 }, (_, dayIndex) => {
        const date = isoDay(weekStartOffset + dayIndex);
        const rest = dayIndex === 2 || dayIndex === 6;
        const long = dayIndex === 5;
        const quality = dayIndex === 3;
        const title = long ? "Long aerobic run" : quality ? "Controlled progression" : "Easy aerobic run";
        const duration = rest ? 0 : long ? 75 + weekIndex * 5 : quality ? 55 : 40;
        const sessionId = `session-${date}`;
        return {
          day_id: `day-${date}`,
          date,
          label: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][dayIndex],
          focus_type: rest ? "recovery" : long ? "endurance" : quality ? "progression" : "aerobic",
          intensity: rest ? "rest" as const : quality ? "moderate" as const : "low" as const,
          total_duration_min: duration,
          is_completed: false,
          blocks: dayIndex === 0 && weekIndex === 0 ? [
            {
              type: "recovery" as const,
              block_id: "first-day-recovery",
              session_id: sessionId,
              title: "Close the loop",
              emphasis: "secondary" as const,
              markdown: "Finish with five quiet minutes of walking and record how repeatable the effort felt.",
            },
          ] : [],
          sessions: rest ? [] : [
            {
              session_id: sessionId,
              title,
              sport: "running",
              objective_markdown: long ? "Accumulate durable aerobic time without turning the final third into a test." : quality ? "Practice a smooth increase in effort while remaining in control." : "Build aerobic frequency with relaxed mechanics.",
              prescription_markdown: quality ? "15 min easy, then 3 × 8 min steady with 3 min easy between, finish relaxed." : long ? "Stay conversational throughout. Walk briefly if that preserves calm execution." : "Run conversationally. You should be able to continue at the finish.",
              duration_min: duration,
              intensity: quality ? "moderate" as const : "low" as const,
              distance_km: null,
              blocks: quality && weekIndex === 0 ? [
                {
                  type: "interval_table" as const,
                  block_id: "progression-intervals",
                  session_id: sessionId,
                  title: "Progression structure",
                  emphasis: "primary" as const,
                  intervals: [
                    { label: "Warm-up", duration: "15 min", prescription: "Easy and conversational", recovery: null },
                    { label: "Main set", duration: "3 × 8 min", prescription: "Steady, controlled pressure", recovery: "3 min easy" },
                    { label: "Cool-down", duration: "10 min", prescription: "Let effort fall gradually", recovery: null },
                  ],
                },
              ] : [],
            },
          ],
        };
      }),
    };
  });
}

const WEEKLY: WeeklyPlanV3 = {
  type: "weekly_plan",
  schema_version: 3,
  plan_id: "execution-demo-v3",
  season_plan_id: "season-demo-v3",
  version: 1,
  athlete_name: "Demo Athlete",
  created_at: "2026-08-03T09:00:00Z",
  title: "28 days of repeatable work",
  summary_markdown: "A local-first execution block built from your goals, availability, and constraints. Wearable data is optional—not a prerequisite for serious coaching.",
  start_date: "2026-08-03",
  end_date: "2026-08-30",
  weeks: buildWeeks(),
  sections: [
    {
      section_id: "execution-rules",
      title: "How to execute the block",
      summary_markdown: "Use perceived effort and honest feedback. The calendar is a decision aid, not a debt ledger.",
      emphasis: "primary",
      disclosure_intent: "inline",
      blocks: [
        {
          type: "workout",
          block_id: "anchor-workout",
          session_id: "session-2026-08-06",
          title: "Controlled progression",
          emphasis: "primary",
          objective_markdown: "Introduce pressure without losing form, breathing control, or tomorrow's training capacity.",
        },
        {
          type: "fueling",
          block_id: "long-run-fueling",
          session_id: null,
          title: "Fuel the longer days",
          emphasis: "secondary",
          before_markdown: "Eat a familiar meal two to three hours before the session.",
          during_markdown: "Bring water in warm conditions and practice a small carbohydrate intake on runs beyond 75 minutes.",
          after_markdown: "Eat a normal recovery meal with carbohydrate and protein.",
        },
        {
          type: "data_table",
          block_id: "effort-language",
          title: "Shared effort language",
          emphasis: "secondary",
          columns: [
            { key: "signal", label: "Signal", align: "left" },
            { key: "meaning", label: "What it means", align: "left" },
            { key: "response", label: "Response", align: "left" },
          ],
          rows: [
            { signal: "Conversational", meaning: "Full sentences remain easy", response: "Stay here on aerobic days" },
            { signal: "Controlled", meaning: "Focused but never straining", response: "Use for progression work" },
            { signal: "Form deteriorates", meaning: "The prescription is no longer serving its goal", response: "Back off and tell the coach" },
          ],
        },
      ],
    },
    {
      section_id: "adaptation",
      title: "When the week changes",
      summary_markdown: "Bring the new reality into coach chat. The Head Coach revises the plan; the UI does not invent a fallback.",
      emphasis: "secondary",
      disclosure_intent: "collapsible",
      blocks: [
        {
          type: "callout",
          block_id: "adapt-dont-stack",
          title: "Adapt, do not stack",
          emphasis: "secondary",
          tone: "warning",
          markdown: "If a session no longer fits, ask the coach to re-plan from the current day. Do not compress missed work into the remaining week.",
        },
      ],
    },
  ],
  assumptions: [
    { statement: "Four running days are normally available.", consequence: "Wednesday and Sunday remain recovery anchors.", needs_confirmation: true },
  ],
  evidence: [
    { source_kind: "athlete_declared", authority: "athlete_declared", source_id: "demo-availability", observed_at: "2026-08-03T08:00:00Z", limitations: ["No connected wearable observations"] },
  ],
  safety_concerns: [],
  unresolved_questions: ["Would Saturday or Sunday be more reliable for later long sessions?"],
  decision_ledger_entry: {
    decision_id: "initial-execution-decision",
    decided_at: "2026-08-03T09:00:00Z",
    title: "Establish a repeatable four-week rhythm",
    rationale_markdown: "The declared schedule supports four running days with two stable recovery anchors.",
    changes_markdown: "Created the first 28-day execution block.",
    evidence_ids: ["demo-availability"],
  },
};

export const DEMO_WEEKLY_PLAN_BY_PERSONA: Record<DemoPersonaId, WeeklyPlanV3> = {
  "hybrid-operator": WEEKLY,
};
