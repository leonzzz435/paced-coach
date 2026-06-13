"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import type { AthleteProfileResponse, Competition, IntegrationsStatus, ProfilePayload } from "@/lib/types/athlete-context";
import {
  formatDateHuman,
  formatTrainingProviderBadge,
  getAttentionTrainingProviderNames,
  getPreviouslyConnectedProviderNames,
  hasEverConnectedTrainingProvider,
  hasLinkedTrainingProvider,
  hasOperationalTrainingProvider,
  profileCompleteness,
} from "@/lib/types/athlete-context";
import type { DashboardStateResponse } from "@/lib/types/dashboard";

type RunState = "idle" | "starting" | "error";
type ContextState = "loading" | "loaded" | "error";

function summarizeProfile(profile: ProfilePayload | null): string[] {
  if (!profile) return ["No stored profile found yet."];
  return [
    profile.goals?.primary_goal ? `Goal: ${profile.goals.primary_goal}` : "Goal: not set",
    profile.availability?.time_windows ? `Availability: ${profile.availability.time_windows}` : "Availability: not set",
    (profile.preferences?.sports ?? []).length > 0
      ? `Sports: ${(profile.preferences?.sports ?? []).join(", ")}`
      : "Sports: not set",
    profile.preferences?.injuries_limitations
      ? `Constraints: ${profile.preferences.injuries_limitations}`
      : "Constraints: not set",
  ];
}

export default function NewRunPage() {
  const router = useRouter();

  const [athleteName, setAthleteName] = useState("Athlete");
  const [analysisNotes, setAnalysisNotes] = useState("");
  const [planningNotes, setPlanningNotes] = useState("");
  const [temporaryConstraints, setTemporaryConstraints] = useState("");
  const [planStartDate, setPlanStartDate] = useState("");

  const [state, setState] = useState<RunState>("idle");
  const [message, setMessage] = useState<string | null>(null);

  const [contextState, setContextState] = useState<ContextState>("loading");
  const [contextError, setContextError] = useState<string | null>(null);
  const [profile, setProfile] = useState<ProfilePayload | null>(null);
  const [competitions, setCompetitions] = useState<Competition[]>([]);
  const [integrations, setIntegrations] = useState<IntegrationsStatus | null>(null);
  const [firstRun, setFirstRun] = useState<DashboardStateResponse["first_run"] | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadContext() {
      setContextState("loading");
      setContextError(null);
      try {
        const [profileRes, competitionRes, credentialsRes, dashboardRes] = await Promise.all([
          fetch("/app/api/athlete-profile", { cache: "no-store" }),
          fetch("/app/api/competitions", { cache: "no-store" }),
          fetch("/app/api/integrations/status", { cache: "no-store" }),
          fetch("/app/api/dashboard/state", { cache: "no-store" }),
        ]);

        if (!profileRes.ok) throw new Error("Failed to load athlete profile");
        if (!competitionRes.ok) throw new Error("Failed to load competitions");
        if (!credentialsRes.ok) throw new Error("Failed to load integrations status");
        if (!dashboardRes.ok) throw new Error("Failed to load generation readiness");

        const profileData = (await profileRes.json()) as AthleteProfileResponse;
        const competitionData = (await competitionRes.json()) as Competition[];
        const credentialsData = (await credentialsRes.json()) as IntegrationsStatus;
        const dashboardData = (await dashboardRes.json()) as DashboardStateResponse;

        if (cancelled) return;
        setProfile(profileData.profile);
        setCompetitions(competitionData);
        setIntegrations(credentialsData);
        setFirstRun(dashboardData.first_run);
        setContextState("loaded");
      } catch (error) {
        if (cancelled) return;
        setContextError(error instanceof Error ? error.message : "Failed to load profile context");
        setContextState("error");
      }
    }

    loadContext();
    return () => {
      cancelled = true;
    };
  }, []);

  const completeness = useMemo(() => profileCompleteness(profile), [profile]);
  const warnings = useMemo(() => {
    const nextWarnings: string[] = [];
    const operationalProviderReady = hasOperationalTrainingProvider(integrations);
    if (!operationalProviderReady) {
      if (hasLinkedTrainingProvider(integrations)) {
        const attentionProviders = getAttentionTrainingProviderNames(integrations);
        const attentionSummary = attentionProviders.length > 0 ? attentionProviders.join(" + ") : "A linked provider";
        nextWarnings.push(`${attentionSummary} needs attention. Draft Mode still works, but connected coaching will stay partial until those sources recover.`);
      } else if (hasEverConnectedTrainingProvider(integrations)) {
        const disconnectedProviders = getPreviouslyConnectedProviderNames(integrations);
        const providerSummary = disconnectedProviders.length > 0 ? disconnectedProviders.join(" + ") : "Your training source";
        nextWarnings.push(`${providerSummary} was disconnected. Draft Mode still works, but connected coaching stays partial until a source is reconnected.`);
      } else {
        nextWarnings.push("No connected training source yet. Draft Mode still works, but planning will rely on your stored profile and race calendar until you connect Strava or WHOOP.");
      }
    }
    if (completeness < 65) {
      nextWarnings.push("Profile context is still sparse, so training constraints may be interpreted too loosely.");
    }
    if (competitions.length === 0) {
      nextWarnings.push("No competitions are saved, so periodization will be more generic.");
    }
    if (firstRun && !firstRun.llm_ready) {
      nextWarnings.push("No supported LLM key is configured. Add OPENAI_API_KEY to .env and restart the API before generating.");
    }
    return nextWarnings;
  }, [competitions.length, completeness, firstRun, integrations]);

  const llmReady = firstRun?.llm_ready ?? true;
  const generationDisabled = state === "starting" || contextState === "loading" || !llmReady;

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!llmReady) {
      setState("error");
      setMessage("Add OPENAI_API_KEY to your local .env, restart the API, then retry generation.");
      return;
    }
    setState("starting");
    setMessage(null);

    try {
      const runRes = await fetch("/app/api/analysis/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          athlete_name: athleteName.trim() || "Athlete",
          plan_start_date: planStartDate || null,
          run_overrides: {
            analysis_notes: analysisNotes.trim() || null,
            planning_notes: planningNotes.trim() || null,
            temporary_constraints: temporaryConstraints.trim() || null,
          },
          enable_plotting: false,
        }),
      });
      if (!runRes.ok) {
        const text = await runRes.text().catch(() => "");
        throw new Error(text || runRes.statusText);
      }

      const data = (await runRes.json()) as { job_id?: string; jobId?: string };
      const jobId = data.job_id ?? data.jobId;
      if (!jobId) throw new Error(`Backend did not return job_id (got: ${JSON.stringify(data)})`);

      router.push(`/app/jobs/${jobId}`);
    } catch (error) {
      setState("error");
      setMessage(error instanceof Error ? error.message : "Failed to generate plans.");
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Generate coaching plans</h1>
        <Link className="text-sm text-[var(--text-muted)] hover:text-[var(--text-primary)]" href="/app">
          Back to dashboard
        </Link>
      </div>

      {contextState === "error" ? (
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4 text-sm text-red-400">{contextError}</div>
      ) : null}

      <form onSubmit={onSubmit} className="space-y-4">
        <section className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4 shadow-sm">
          <div className="rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--text-secondary)]">
            <div>Connected sources: {formatTrainingProviderBadge(integrations)}</div>
            <p className="mt-1 text-xs text-[var(--text-muted)]">
              Draft Mode uses your stored profile and race calendar immediately. Connected data improves precision and
              unlocks richer daily sync and weekly recap context once configured.
            </p>
          </div>
        </section>

        <section className="grid gap-4 lg:grid-cols-2">
          <article className="rounded-2xl border border-sky-500/20 bg-[var(--surface)] p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-[0.12em] text-sky-400">Stored profile snapshot</h2>
              <Link href="/app/profile" className="text-xs font-medium text-sky-400 hover:text-sky-300">
                Edit profile
              </Link>
            </div>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">This context is included in every plan generation before analysis and planning.</p>
            <ul className="mt-3 space-y-1 text-sm text-[var(--text-secondary)]">
              {summarizeProfile(profile).map((line) => (
                <li key={line}>• {line}</li>
              ))}
            </ul>
            <p className="mt-3 text-xs text-[var(--text-muted)]">Completeness: {completeness}%</p>
          </article>

          <article className="rounded-2xl border border-amber-500/20 bg-[var(--surface)] p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-[0.12em] text-amber-400">Stored competitions</h2>
              <Link href="/app/competitions" className="text-xs font-medium text-amber-400 hover:text-amber-300">
                Edit races
              </Link>
            </div>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">Competitions are sourced from the saved race calendar, not this generation form.</p>
            <ul className="mt-3 space-y-1 text-sm text-[var(--text-secondary)]">
              {competitions.length === 0 ? (
                <li>• No races saved yet.</li>
              ) : (
                competitions.slice(0, 4).map((competition) => (
                  <li key={competition.id}>
                    • {competition.name} — {competition.date ? formatDateHuman(competition.date) : competition.date_text || "Date pending"}
                  </li>
                ))
              )}
            </ul>
          </article>
        </section>

        {warnings.length > 0 ? (
          <section className="rounded-2xl border border-amber-500/20 bg-amber-500/10 p-4">
            <div className="text-sm font-semibold text-amber-300">Draft Mode notes</div>
            <p className="mt-1 text-xs text-amber-400">
              You can generate plans now. These gaps mainly reduce precision or limit later connected coaching surfaces.
            </p>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-amber-300">
              {warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
            {!hasOperationalTrainingProvider(integrations) ? (
              <Link className="mt-3 inline-flex text-sm font-semibold text-amber-200 hover:text-white" href="/app/settings">
                Open connected sources
              </Link>
            ) : null}
          </section>
        ) : null}

        <section className="rounded-2xl border border-emerald-500/20 bg-[var(--surface)] p-4 shadow-sm space-y-3">
          <h2 className="text-sm font-semibold uppercase tracking-[0.12em] text-emerald-400">Temporary overrides</h2>

          <div>
            <label className="block text-sm font-medium text-[var(--text-primary)]">Athlete display name</label>
            <input
              className="mt-1 w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-[var(--text-primary)] placeholder:text-[var(--text-dim)]"
              value={athleteName}
              onChange={(e) => setAthleteName(e.target.value)}
              placeholder="Athlete"
              required
            />
            <p className="mt-1 text-xs text-[var(--text-muted)]">This name appears in generated plans and analysis output headers.</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-[var(--text-primary)]">Current status notes (analysis)</label>
            <textarea
              className="mt-1 w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-dim)] resize-y"
              rows={3}
              value={analysisNotes}
              onChange={(e) => setAnalysisNotes(e.target.value)}
              placeholder="How you feel right now, recent fatigue, unusual sessions, confidence, stress..."
            />
            <p className="mt-1 text-xs text-[var(--text-muted)]">Use this for immediate context that should influence interpretation of recent training signals.</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-[var(--text-primary)]">Planning notes (planning)</label>
            <textarea
              className="mt-1 w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-dim)] resize-y"
              rows={3}
              value={planningNotes}
              onChange={(e) => setPlanningNotes(e.target.value)}
              placeholder="Session preferences, execution requests, focus areas for the next block..."
            />
            <p className="mt-1 text-xs text-[var(--text-muted)]">Use this to steer the next block without changing your persistent baseline profile.</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-[var(--text-primary)]">Temporary constraints</label>
            <textarea
              className="mt-1 w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-dim)] resize-y"
              rows={2}
              value={temporaryConstraints}
              onChange={(e) => setTemporaryConstraints(e.target.value)}
              placeholder="Travel window, no pool, no gym access, limited weekday time, etc."
            />
            <p className="mt-1 text-xs text-[var(--text-muted)]">Add generation-specific constraints here so they affect this plan build without overwriting your baseline profile.</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-[var(--text-primary)]">Plan start date</label>
            <input
              className="mt-1 w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-[var(--text-primary)] sm:w-56"
              type="date"
              value={planStartDate}
              onChange={(e) => setPlanStartDate(e.target.value)}
            />
            <p className="mt-1 text-xs text-[var(--text-muted)]">Set a future start date if you want the generated weeks aligned to a specific kickoff day.</p>
          </div>
        </section>


        <div className="space-y-2">
          <button
            className="rounded-md bg-[var(--accent-primary)] px-4 py-2 text-white disabled:opacity-60"
            disabled={generationDisabled}
            type="submit"
          >
            {state === "starting"
              ? "Generating..."
              : !llmReady
                ? "Add an LLM key first"
              : contextState === "loading"
                ? "Loading context..."
                : "Generate season plan + 28-day block"}
          </button>
          {message ? <p className="text-sm text-[var(--text-secondary)]">{message}</p> : null}
          {contextState === "loading" ? <p className="text-xs text-[var(--text-muted)]">Loading stored context…</p> : null}
        </div>
      </form>
    </div>
  );
}
