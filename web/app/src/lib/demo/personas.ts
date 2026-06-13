export const DEMO_PERSONA_IDS = ["hybrid-operator"] as const;

export type DemoPersonaId = (typeof DEMO_PERSONA_IDS)[number];

export type DemoPersonaMeta = {
  id: DemoPersonaId;
  title: string;
  tagline: string;
  focus: string;
  updated_at: string;
};

export const DEFAULT_DEMO_PERSONA_ID: DemoPersonaId = "hybrid-operator";

export const DEMO_PERSONA_META: Record<DemoPersonaId, DemoPersonaMeta> = {
  "hybrid-operator": {
    id: "hybrid-operator",
    title: "Hybrid Operator",
    tagline:
      "Multisport endurance athlete balancing run, bike, and swim with stacked races and real-life constraints.",
    focus: "Load stability, race-specific periodization, and recovery-gated progression across three disciplines",
    updated_at: "2026-03-07",
  },
};

export function isDemoPersonaId(value: string | null | undefined): value is DemoPersonaId {
  return typeof value === "string" && (DEMO_PERSONA_IDS as readonly string[]).includes(value);
}

export function resolveDemoPersonaId(value: string | null | undefined): DemoPersonaId {
  return isDemoPersonaId(value) ? value : DEFAULT_DEMO_PERSONA_ID;
}
