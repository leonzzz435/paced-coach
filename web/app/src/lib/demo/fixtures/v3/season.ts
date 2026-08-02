import type { SeasonPlanV3 } from "@/components/plan-viewer/types";
import type { DemoPersonaId } from "@/lib/demo/personas";

const SEASON: SeasonPlanV3 = {
  type: "season_plan",
  schema_version: 3,
  plan_id: "season-demo-v3",
  version: 1,
  athlete_name: "Demo Athlete",
  created_at: "2026-08-03T09:00:00Z",
  title: "Build the engine, then make it race-specific",
  summary_markdown: "A three-phase season that protects consistency first, adds durable threshold work second, and arrives at race week with freshness intact.",
  start_date: "2026-08-03",
  end_date: "2026-11-01",
  goal_event_ids: ["autumn-endurance-event"],
  phases: [
    {
      phase_id: "foundation",
      title: "Foundation",
      start_date: "2026-08-03",
      end_date: "2026-08-30",
      objective_markdown: "Make four training days per week feel normal, calm, and repeatable.",
      success_signals: ["Four repeatable weeks", "Easy sessions finish with reserve"],
      blocks: [],
    },
    {
      phase_id: "specific-build",
      title: "Specific build",
      start_date: "2026-08-31",
      end_date: "2026-10-11",
      objective_markdown: "Convert the foundation into sustained race-specific durability without sacrificing the easy-day discipline.",
      success_signals: ["Threshold work remains controlled", "Long sessions recover within 48 hours"],
      blocks: [],
    },
    {
      phase_id: "sharpen-taper",
      title: "Sharpen and taper",
      start_date: "2026-10-12",
      end_date: "2026-11-01",
      objective_markdown: "Keep the race rhythm familiar while reducing fatigue and decision load.",
      success_signals: ["Legs feel responsive", "Race execution is rehearsed"],
      blocks: [],
    },
  ],
  sections: [
    {
      section_id: "strategy",
      title: "Why this progression works",
      summary_markdown: "Each phase earns the next. Missed work is information, never debt.",
      emphasis: "primary",
      disclosure_intent: "inline",
      blocks: [
        {
          type: "phase_timeline",
          block_id: "season-timeline",
          title: "Season progression",
          emphasis: "primary",
          milestones: [
            { phase_id: "foundation", label: "Repeatability", note: "Frequency before density" },
            { phase_id: "specific-build", label: "Durability", note: "Specific work with reserve" },
            { phase_id: "sharpen-taper", label: "Freshness", note: "Reduce fatigue, retain rhythm" },
          ],
        },
        {
          type: "narrative",
          block_id: "strategy-narrative",
          title: "The governing idea",
          emphasis: "secondary",
          markdown: "The most powerful plan is the one you can execute repeatedly. Optional wearable data can refine decisions later, but it is not required to create a strong season.\n\n- Use the [effort guide](https://example.com/effort)\n- Share honest feedback\n- Adapt from the current day",
        },
      ],
    },
    {
      section_id: "guardrails",
      title: "Non-negotiable guardrails",
      summary_markdown: "The plan adapts from honest feedback rather than forcing false precision.",
      emphasis: "secondary",
      disclosure_intent: "summary_first",
      blocks: [
        {
          type: "callout",
          block_id: "missed-work",
          title: "No training debt",
          emphasis: "primary",
          tone: "warning",
          markdown: "Do not stack a missed hard session onto the next day. Continue from the current calendar and let the coach reassess.",
        },
        {
          type: "checklist",
          block_id: "weekly-checks",
          title: "Weekly signals",
          emphasis: "secondary",
          items: [
            { item_id: "energy", label: "Energy is stable across normal workdays", detail_markdown: "Flag unusual fatigue in the coach chat." },
            { item_id: "pain", label: "No escalating pain pattern", detail_markdown: "Stop and seek qualified medical advice when symptoms are concerning." },
            { item_id: "repeat", label: "The next week still looks realistically executable" },
          ],
        },
      ],
    },
  ],
  assumptions: [
    { statement: "Four training days are normally available.", consequence: "The plan prioritizes frequency over session density.", needs_confirmation: true },
  ],
  evidence: [
    { source_kind: "athlete_declared", authority: "athlete_declared", source_id: "demo-profile", observed_at: "2026-08-03T08:00:00Z", limitations: ["No connected provider data"] },
  ],
  safety_concerns: [],
  unresolved_questions: ["Which weekday is most reliable for the long session?"],
  decision_ledger_entry: {
    decision_id: "initial-season-decision",
    decided_at: "2026-08-03T09:00:00Z",
    title: "Consistency before specificity",
    rationale_markdown: "Declared availability supports four repeatable training days without requiring wearable inputs.",
    changes_markdown: "Created the initial three-phase season strategy.",
    evidence_ids: ["demo-profile"],
  },
};

export const DEMO_SEASON_PLAN_BY_PERSONA: Record<DemoPersonaId, SeasonPlanV3> = {
  "hybrid-operator": SEASON,
};
