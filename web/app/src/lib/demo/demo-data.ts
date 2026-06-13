/* ─────────────────────────────────────────────
   Demo data — curated from production demo outputs.
   All identifiers abstracted (no internal topology).
   ───────────────────────────────────────────── */

export type {
  UiKpiStatus,
  UiKpi,
  UiAnalysisSectionTone,
  UiAnalysisSection,
  UiAnalysis,
  UiDisclosureNode,
  UiSeasonPhase,
  UiSeasonPlan,
  UiDayPlan,
  UiWeekPlan,
  UiWeeklyPlan,
} from "@/lib/types/ui-blocks";

import {
  DEFAULT_DEMO_PERSONA_ID,
  DEMO_PERSONA_META,
  resolveDemoPersonaId,
  type DemoPersonaId,
  type DemoPersonaMeta,
} from "@/lib/demo/personas";
import { DEMO_ANALYSIS_BY_PERSONA } from "@/lib/demo/fixtures/v1/analysis";
import { DEMO_SEASON_PLAN_BY_PERSONA } from "@/lib/demo/fixtures/v1/season";
import { DEMO_WEEKLY_PLAN_BY_PERSONA } from "@/lib/demo/fixtures/v1/weekly";
import type { UiAnalysis, UiSeasonPlan, UiWeeklyPlan } from "@/lib/types/ui-blocks";

export {
  DEFAULT_DEMO_PERSONA_ID,
  DEMO_PERSONA_IDS,
  DEMO_PERSONA_META,
  isDemoPersonaId,
  resolveDemoPersonaId,
  type DemoPersonaId,
  type DemoPersonaMeta,
} from "@/lib/demo/personas";

export type DemoPersonaBundle = DemoPersonaMeta & {
  analysis: UiAnalysis;
  season: UiSeasonPlan;
  weekly: UiWeeklyPlan;
};

export const DEMO_PERSONAS: Record<DemoPersonaId, DemoPersonaBundle> = {
  "hybrid-operator": {
    ...DEMO_PERSONA_META["hybrid-operator"],
    analysis: DEMO_ANALYSIS_BY_PERSONA["hybrid-operator"],
    season: DEMO_SEASON_PLAN_BY_PERSONA["hybrid-operator"],
    weekly: DEMO_WEEKLY_PLAN_BY_PERSONA["hybrid-operator"],
  },
};

export function getDemoPersonaBundle(personaId?: string | null): DemoPersonaBundle {
  const resolvedPersonaId = resolveDemoPersonaId(personaId);
  return DEMO_PERSONAS[resolvedPersonaId];
}

export const DEFAULT_DEMO_PERSONA = DEMO_PERSONAS[DEFAULT_DEMO_PERSONA_ID];

// Keep these direct exports so existing components can import compact defaults.
export const DEMO_ANALYSIS: UiAnalysis = DEFAULT_DEMO_PERSONA.analysis;
export const DEMO_SEASON_PLAN: UiSeasonPlan = DEFAULT_DEMO_PERSONA.season;
export const DEMO_WEEKLY_PLAN: UiWeeklyPlan = DEFAULT_DEMO_PERSONA.weekly;

export type DemoInputCategory =
  | "activity"
  | "recovery"
  | "physiology"
  | "competitions"
  | "context"
  | "constraints";

export type DemoInputCard = {
  id: string;
  category: DemoInputCategory;
  title: string;
  icon: string;
  color: string;
  metrics: Array<{ label: string; value: string }>;
};

export type DemoReasoningStep = {
  id: string;
  agent: string;
  text: string;
};

export const DEMO_INPUTS: DemoInputCard[] = [
  {
    id: "activity",
    category: "activity",
    title: "Activity history",
    icon: "🏃",
    color: "ring-sky-400/30",
    metrics: [
      { label: "Window", value: "61-day load history" },
      { label: "Modalities", value: "Run · Bike · Ski · Strength" },
      { label: "Load trend", value: "↑ rebuilding from late-Feb reset" },
    ],
  },
  {
    id: "recovery",
    category: "recovery",
    title: "Recovery signals",
    icon: "💤",
    color: "ring-emerald-400/30",
    metrics: [
      { label: "HRV (overnight)", value: "108 ms — baseline 101–155" },
      { label: "Recovery score", value: "56% (↓ from 89–95%)" },
      { label: "Sleep RHR", value: "47 bpm — mildly elevated" },
    ],
  },
  {
    id: "physiology",
    category: "physiology",
    title: "Physiological markers",
    icon: "❤️",
    color: "ring-rose-400/30",
    metrics: [
      { label: "Run VO₂max", value: "52.0 (↑ from 49, stable)" },
      { label: "Threshold reps", value: "1 km @ 4:35–4:55/km" },
      { label: "Cross-sport transfer", value: "Positive (bike → run)" },
    ],
  },
  {
    id: "competitions",
    category: "competitions",
    title: "Race calendar",
    icon: "🏁",
    color: "ring-amber-400/30",
    metrics: [
      { label: "A-race #1", value: "Trail 38k — May 3" },
      { label: "A-race #2", value: "10k road — Jun 19 (44:00)" },
      { label: "A-race #3", value: "Olympic Tri — Aug 9" },
    ],
  },
  {
    id: "constraints",
    category: "constraints",
    title: "Preferences & constraints",
    icon: "⚙️",
    color: "ring-violet-400/30",
    metrics: [
      { label: "Weekly hours", value: "8–10h available" },
      { label: "Fixed sessions", value: "Team swim Sun, Club intervals Tue" },
      { label: "Blocked dates", value: "Travel Mar 15–18 (hotel gym only)" },
    ],
  },
  {
    id: "load-metrics",
    category: "activity",
    title: "Load & stress metrics",
    icon: "📊",
    color: "ring-indigo-400/30",
    metrics: [
      { label: "ACWR (7d/28d)", value: "0.76 (conservative rebuild)" },
      { label: "TSB (freshness)", value: "-3.3 (near-neutral)" },
      { label: "Acute load", value: "88.5 EWMA (↑ from reset)" },
    ],
  },
];

export const DEMO_REASONING_STEPS: DemoReasoningStep[] = [
  { id: "d1", agent: "Data ingestion", text: "Extracting 61-day load history across run, bike, ski, and strength\u2026" },
  { id: "d2", agent: "Data ingestion", text: "Merging overnight HRV 108 ms + sleep RHR 47 bpm with recovery score 56%\u2026" },
  { id: "d3", agent: "Data ingestion", text: "Mapping 5 races: Trail 38k (A), 10k road (A), Olympic Tri (A), Half Marathon (A), 5k (B)\u2026" },
  { id: "a1", agent: "Load analysis", text: "ACWR 0.76 \u2014 conservative rebuild from late-Feb reset. Acute 88.5, chronic 85.2. Ramp trajectory safe." },
  { id: "a2", agent: "Recovery analysis", text: "Recovery score 56% (↓ from 89–95%). Sleep fragmentation flagged. Sleep RHR mildly elevated at 47 bpm." },
  { id: "a3", agent: "Performance analysis", text: "Run VO\u2082max 52.0 (stable). 1 km threshold reps 4:35–4:55/km. 10k target 44:00 needs ~4:24 sustained." },
  { id: "s1", agent: "Cross-referencing", text: "Integrating load \u00d7 recovery \u00d7 performance across multi-source signals\u2026 risk: sleep + recovery dip." },
  { id: "p1", agent: "Periodization", text: "Building 11-phase arc: Rebuild \u2192 Trail build \u2192 Trail peak \u2192 10k rebuild \u2192 10k peak \u2192 Tri base \u2192 Tri peak \u2192 Reset \u2192 HM build \u2192 HM sharpen \u2192 HM taper\u2026" },
  { id: "p2", agent: "Scheduling", text: "Constructing 4-week block with 12 focus types: threshold, sweet-spot, hills, trail-endurance, recovery-bike\u2026" },
  { id: "f1", agent: "Output generation", text: "Generating 11 KPIs, 6 coaching sections, and an 11-phase season roadmap across 34 weeks\u2026" },
  { id: "f2", agent: "Output generation", text: "Building a 4-week training block with pacing targets, fueling protocol, and readiness gates\u2026" },
  { id: "v1", agent: "Validation", text: "Feasibility check passed: load ceiling respected, recovery gates honored, eccentric cost rules applied." },
];
