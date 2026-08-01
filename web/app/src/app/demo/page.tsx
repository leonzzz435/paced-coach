import { Suspense } from "react";
import Link from "next/link";

import DashboardClient from "@/components/dashboard/dashboard-client";
import PlanViewer from "@/components/plan-viewer/plan-viewer";
import { DEFAULT_DEMO_PERSONA } from "@/lib/demo/demo-data";
import { DEMO_SEASON_PLAN_BY_PERSONA } from "@/lib/demo/fixtures/v3/season";
import { DEMO_WEEKLY_PLAN_BY_PERSONA } from "@/lib/demo/fixtures/v3/weekly";
import { DEFAULT_DEMO_PERSONA_ID } from "@/lib/demo/personas";
import { buildPublicMetadata } from "@/lib/public-metadata";
import type { DashboardStateResponse } from "@/lib/types/dashboard";

export const metadata = buildPublicMetadata({
  title: "paced.coach demo - no wearable required",
  description:
    "See how your goals, availability, and constraints become a season roadmap, 28-day plan, and coach chat with your own LLM key. No wearable required.",
  path: "/demo",
});

const DEMO_NOW_ISO = "2026-08-04T07:45:00.000Z";
const DEMO_SEASON_PLAN = DEMO_SEASON_PLAN_BY_PERSONA[DEFAULT_DEMO_PERSONA_ID];
const DEMO_WEEKLY_PLAN = DEMO_WEEKLY_PLAN_BY_PERSONA[DEFAULT_DEMO_PERSONA_ID];

function demoDashboardState(): DashboardStateResponse {
  const today = DEMO_WEEKLY_PLAN.weeks[0]?.days[1] ?? null;

  return {
    athlete_time: {
      timezone: "Europe/Berlin",
      timezone_source: "profile",
      today_local_date: today?.date ?? "2026-08-04",
      now_local_iso: DEMO_NOW_ISO,
    },
    analysis: {
      analysis: DEFAULT_DEMO_PERSONA.analysis,
      version: DEFAULT_DEMO_PERSONA.analysis.version,
      updated_at: DEMO_NOW_ISO,
      source_job_id: "demo-analysis-job",
    },
    status_surface: {
      kpis: [],
      source: "none",
      label: null,
      updated_at: DEMO_NOW_ISO,
      target_date: today?.date ?? "2026-08-04",
    },
    coach_surface: {
      source: "analysis",
      scope: "training_block",
      primary_label: "Coach priority",
      primary_text:
        "Keep Saturday's long run easy and fueled. It anchors this block without requiring pace, heart-rate, or readiness targets.",
      secondary_text:
        "The agent reasons from the active plan and declared constraints, marks adaptation gates, and makes uncertainty explicit.",
      updated_at: DEMO_NOW_ISO,
    },
    season: {
      season_plan: DEMO_SEASON_PLAN,
      version: DEMO_SEASON_PLAN.version,
      updated_at: DEMO_NOW_ISO,
      source_job_id: "demo-season-job",
    },
    weekly: {
      weekly_plan: DEMO_WEEKLY_PLAN,
      version: DEMO_WEEKLY_PLAN.version,
      updated_at: DEMO_NOW_ISO,
      source_job_id: "demo-weekly-job",
    },
    first_run: {
      mode: "manual",
      evidence_level: "declared_only",
      llm_ready: true,
      profile_completeness: 100,
      profile_ready: true,
      goal_ready: true,
      has_competitions: true,
      has_active_plan: true,
      has_connected_source: false,
      next_step: "generated",
      title: "Your first local plan is ready",
      body: "This demo uses declared profile, goals, constraints, and sanitized fixture output. No external training-data provider is involved.",
      primary_action: { label: "View plan", href: "#plan" },
      secondary_actions: [{ label: "Ask coach", href: "#coach" }],
      blockers: [],
    },
    today_mission: {
      warnings: [
        "Demo mode: this is fixture data, not live medical or training advice.",
        "No device-derived readiness, sleep, or compliance signal is assumed; describe anything relevant in your own words.",
      ],
      day_override: null,
    },
    daily_sync: {
      visible: false,
      status: "idle",
      run_id: null,
      verdict_preview: null,
      sources_used: [],
      proposal_id: null,
      thread_id: "demo-thread",
      error_message: null,
      can_run: false,
      attention_message: null,
      gate_target: null,
    },
    weekly_recap: {
      visible: false,
      allowed: false,
      status: "completed_this_window",
      thread_id: null,
      proposal_id: null,
      follow_up_question: null,
      summary_preview: null,
      pending_action: "none",
      can_run: false,
      attention_message: null,
      gate_target: null,
    },
    pending_proposal_banner: null,
  };
}

function DemoShell({ children }: { children: React.ReactNode }) {
  return (
    <main className="min-h-screen overflow-hidden bg-[radial-gradient(circle_at_15%_0%,rgba(34,197,94,0.18),transparent_30%),radial-gradient(circle_at_85%_10%,rgba(14,165,233,0.17),transparent_28%),linear-gradient(180deg,#07111f_0%,#0b0f19_42%,#101827_100%)] text-[var(--text-primary)]">
      <div className="mx-auto flex w-full max-w-[1480px] flex-col gap-12 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
        {children}
      </div>
    </main>
  );
}

function DemoHero() {
  return (
    <section
      className="relative overflow-hidden rounded-[2.25rem] border border-white/10 bg-[linear-gradient(135deg,rgba(255,255,255,0.10),rgba(255,255,255,0.035))] p-5 shadow-[0_28px_90px_rgba(0,0,0,0.34)] sm:p-8 lg:p-10"
      data-screenshot="hero"
    >
      <div className="absolute inset-x-10 top-0 h-px bg-gradient-to-r from-transparent via-emerald-200/50 to-transparent" />
      <div className="grid gap-8 lg:grid-cols-[minmax(0,1.1fr)_minmax(460px,0.9fr)] lg:items-center">
        <div>
          <div className="inline-flex rounded-full border border-emerald-300/20 bg-emerald-300/10 px-3 py-1 text-[11px] font-bold uppercase tracking-[0.18em] text-emerald-100">
            No wearable required
          </div>
          <h1 className="mt-5 max-w-4xl text-4xl font-black tracking-[-0.06em] text-white sm:mt-6 sm:text-6xl lg:text-7xl">
            Your season. Your next 28 days. One coach that knows the plan.
          </h1>
          <p className="mt-5 max-w-2xl text-sm leading-7 text-slate-300 sm:text-lg sm:leading-8">
            Start with your goals, training history, availability, and constraints. Bring one supported LLM key.
            paced.coach builds the season roadmap, the execution calendar, and the coach conversation from that
            declared context.
          </p>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-400">
            Runs locally. Version 2.2.0 is provider-free: athlete-declared context is the product, not a fallback.
          </p>
          <div className="mt-7 flex flex-wrap gap-3">
            <Link
              className="rounded-2xl bg-white px-5 py-3 text-sm font-black text-slate-950 shadow-[0_12px_40px_rgba(255,255,255,0.18)] transition hover:scale-[1.02]"
              href="/app"
            >
              Open local app
            </Link>
            <Link
              className="rounded-2xl border border-white/12 bg-white/[0.04] px-5 py-3 text-sm font-bold text-slate-100 transition hover:bg-white/[0.08]"
              href="#plan"
            >
              See generated plan
            </Link>
          </div>
        </div>

        <div className="rounded-[2rem] border border-white/10 bg-slate-950/55 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] backdrop-blur">
          <div className="grid gap-3 sm:grid-cols-2">
            {[
              ["Athlete context", "You define it", "Goals, history, availability, and constraints"],
              ["Season roadmap", "3 phases", "Macro plan from August to November"],
              ["Execution block", "28 days", "Day-level sessions and adaptation gates"],
              ["Coach workspace", "Plan-aware", "Questions, reflections, and proposed changes"],
            ].map(([label, value, body]) => (
              <div className="rounded-3xl border border-white/10 bg-white/[0.045] p-5" key={label}>
                <div className="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500">{label}</div>
                <div className="mt-3 text-3xl font-black tracking-[-0.05em] text-white">{value}</div>
                <div className="mt-2 text-sm leading-6 text-slate-400">{body}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function SectionHeader({
  eyebrow,
  title,
  body,
}: {
  eyebrow: string;
  title: string;
  body: string;
}) {
  return (
    <div className="mx-auto max-w-3xl text-center">
      <div className="text-[11px] font-black uppercase tracking-[0.2em] text-emerald-200/80">{eyebrow}</div>
      <h2 className="mt-3 text-3xl font-black tracking-[-0.05em] text-white sm:text-5xl">{title}</h2>
      <p className="mt-4 text-sm leading-7 text-slate-400 sm:text-base">{body}</p>
    </div>
  );
}

function CoachPreview() {
  const messages = [
    {
      role: "Athlete",
      body: "I slept badly and my legs are flat. Should I still do the threshold run?",
    },
    {
      role: "Coach",
      body:
        "Modify, do not force. Keep the aerobic warm-up, replace threshold reps with 35 minutes easy plus strides only if the legs open up. I would protect tomorrow's bike quality.",
    },
    {
      role: "Patch proposal",
      body: "Move threshold to Thursday, keep swim technique, reduce today's load by 32 minutes.",
    },
  ];

  return (
    <section
      className="rounded-[2rem] border border-white/10 bg-[linear-gradient(135deg,rgba(139,92,246,0.16),rgba(15,23,42,0.72))] p-5 shadow-[0_24px_80px_rgba(0,0,0,0.32)] sm:p-8"
      data-screenshot="coach"
      id="coach"
    >
      <SectionHeader
        eyebrow="Coach workspace"
        title="Ask questions against the actual plan context."
        body="The public demo keeps the chat static, but the local app uses your saved profile, active plan, competitions, and athlete messages when generating responses."
      />
      <div className="mx-auto mt-8 grid max-w-5xl gap-4">
        {messages.map((message, index) => (
          <div
            className={`rounded-[1.5rem] border p-5 shadow-lg ${
              index === 1
                ? "ml-auto max-w-3xl border-violet-300/20 bg-violet-300/12"
                : "mr-auto max-w-3xl border-white/10 bg-white/[0.055]"
            }`}
            key={message.role}
          >
            <div className="text-[11px] font-black uppercase tracking-[0.18em] text-slate-500">{message.role}</div>
            <p className="mt-2 text-base font-semibold leading-7 text-slate-100">{message.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function DashboardPreview({ dashboardState }: { dashboardState: DashboardStateResponse }) {
  return (
    <section data-screenshot="dashboard" id="dashboard">
      <SectionHeader
        eyebrow="Training cockpit"
        title="See the whole plan — and know what matters today."
        body="Declared athlete context is the product: goals, history, availability, constraints, and the active plan. This preview uses sanitized fixtures and never touches your database."
      />
      <div className="mt-8 rounded-[2rem] border border-white/10 bg-[#0b0f19]/80 p-4 shadow-[0_24px_80px_rgba(0,0,0,0.36)] sm:p-6">
        <DashboardClient initialState={dashboardState} />
      </div>
    </section>
  );
}

function PlanPreview() {
  return (
    <section data-screenshot="plan" id="plan">
      <SectionHeader
        eyebrow="Generated training plan"
        title="Season architecture plus a 28-day execution block."
        body="The same versioned renderer handles roadmap, coach report, and calendar-style day plans."
      />
      <div className="mt-8 rounded-[2rem] border border-white/10 bg-[#0b0f19]/80 p-4 shadow-[0_24px_80px_rgba(0,0,0,0.36)] sm:p-6">
        <Suspense
          fallback={
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-8 text-center text-slate-400">
              Loading demo plan...
            </div>
          }
        >
          <PlanViewer
            analysis={DEFAULT_DEMO_PERSONA.analysis}
            nowIso={DEMO_NOW_ISO}
            publicPreview
            seasonPlan={DEMO_SEASON_PLAN}
            weeklyPlan={DEMO_WEEKLY_PLAN}
          />
        </Suspense>
      </div>
    </section>
  );
}

type DemoPageProps = {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

function readFirst(value: string | string[] | undefined): string | null {
  if (typeof value === "string") return value;
  if (Array.isArray(value) && typeof value[0] === "string") return value[0];
  return null;
}

export default async function DemoPage({ searchParams }: DemoPageProps) {
  const resolvedSearchParams = (await searchParams) ?? {};
  const screenshotTarget = readFirst(resolvedSearchParams.shot);
  const dashboardState = demoDashboardState();

  if (screenshotTarget === "hero") {
    return (
      <DemoShell>
        <DemoHero />
      </DemoShell>
    );
  }

  if (screenshotTarget === "dashboard") {
    return (
      <DemoShell>
        <DashboardPreview dashboardState={dashboardState} />
      </DemoShell>
    );
  }

  if (screenshotTarget === "plan") {
    return (
      <DemoShell>
        <PlanPreview />
      </DemoShell>
    );
  }

  if (screenshotTarget === "coach") {
    return (
      <DemoShell>
        <CoachPreview />
      </DemoShell>
    );
  }

  return (
    <DemoShell>
      <DemoHero />

      <DashboardPreview dashboardState={dashboardState} />

      <PlanPreview />

      <CoachPreview />
    </DemoShell>
  );
}
