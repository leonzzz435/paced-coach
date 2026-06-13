"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

import type { Competition } from "@/lib/types/athlete-context";
import { formatDateHuman } from "@/lib/types/athlete-context";

type LoadState = "loading" | "loaded" | "error";
type CompetitionFormState = {
  name: string;
  date: string;
  dateText: string;
  raceType: string;
  priority: string;
  targetTime: string;
  notes: string;
};

const INPUT_CLASS_NAME =
  "mt-1 w-full rounded-xl border border-white/10 bg-[var(--surface-elevated)]/88 px-3 py-2 text-[var(--text-primary)] outline-none transition placeholder:text-[var(--text-muted)] focus:border-amber-400/40 focus:ring-2 focus:ring-amber-400/10";
const TEXTAREA_CLASS_NAME = `${INPUT_CLASS_NAME} resize-y`;
const LABEL_CLASS_NAME = "block text-sm font-medium text-[var(--text-primary)]";
const HELP_TEXT_CLASS_NAME = "mt-1 text-xs text-[var(--text-muted)]";
const EMPTY_FORM_STATE: CompetitionFormState = {
  name: "",
  date: "",
  dateText: "",
  raceType: "",
  priority: "",
  targetTime: "",
  notes: "",
};

function nullableTrim(value: string): string | null {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function toCompetitionPayload(form: CompetitionFormState) {
  return {
    name: form.name,
    date: nullableTrim(form.date),
    date_text: nullableTrim(form.dateText),
    race_type: nullableTrim(form.raceType),
    priority: nullableTrim(form.priority),
    target_time: nullableTrim(form.targetTime),
    notes: nullableTrim(form.notes),
  };
}

function toCompetitionFormState(competition: Competition): CompetitionFormState {
  return {
    name: competition.name,
    date: competition.date ?? "",
    dateText: competition.date_text ?? "",
    raceType: competition.race_type ?? "",
    priority: competition.priority ?? "",
    targetTime: competition.target_time ?? "",
    notes: competition.notes ?? "",
  };
}

export default function CompetitionsPage() {
  const [state, setState] = useState<LoadState>("loading");
  const [items, setItems] = useState<Competition[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<CompetitionFormState>(EMPTY_FORM_STATE);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isEditing = editingId !== null;
  const canSubmit = useMemo(() => form.name.trim().length > 0 && !isSubmitting, [form.name, isSubmitting]);

  function updateForm(field: keyof CompetitionFormState, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function resetForm() {
    setEditingId(null);
    setForm(EMPTY_FORM_STATE);
  }

  async function load() {
    setState("loading");
    setError(null);
    try {
      const res = await fetch("/app/api/competitions", { cache: "no-store" });
      if (!res.ok) throw new Error("Failed to load competitions");
      const data = (await res.json()) as Competition[];
      setItems(data);
      setState("loaded");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load competitions");
      setState("error");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    const failureMessage = isEditing ? "Failed to update competition" : "Failed to add competition";
    try {
      const res = await fetch(editingId ? `/app/api/competitions/${editingId}` : "/app/api/competitions", {
        method: editingId ? "PATCH" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(toCompetitionPayload(form)),
      });
      if (!res.ok) throw new Error(failureMessage);
      resetForm();
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : failureMessage);
    } finally {
      setIsSubmitting(false);
    }
  }

  function onEdit(competition: Competition) {
    setError(null);
    setEditingId(competition.id);
    setForm(toCompetitionFormState(competition));
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function onDelete(id: string, competitionName: string) {
    if (!window.confirm(`Delete "${competitionName}"? This cannot be undone.`)) return;
    setError(null);
    try {
      const res = await fetch(`/app/api/competitions/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to delete competition");
      if (editingId === id) {
        resetForm();
      }
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete competition");
    }
  }

  return (
    <div className="space-y-4">
      <div className="overflow-hidden rounded-[2rem] border border-[var(--border)] bg-[radial-gradient(circle_at_top_left,rgba(245,158,11,0.12),transparent_34%),radial-gradient(circle_at_bottom_right,rgba(56,189,248,0.10),transparent_32%),linear-gradient(180deg,rgba(255,255,255,0.04),rgba(255,255,255,0.02))] px-5 py-5 shadow-[0_18px_48px_rgba(2,6,23,0.16)]">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--text-muted)]">Race Calendar</div>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight text-[var(--text-primary)]">Competitions</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--text-secondary)]">
              Save your races and target events so season periodization, specificity, and taper timing align with real demands.
            </p>
          </div>
          <Link className="text-sm text-amber-300 transition hover:text-amber-200" href="/app/new">
            Generate plans
          </Link>
        </div>
      </div>

      {state === "error" ? (
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4 text-sm text-red-400">{error}</div>
      ) : null}

      <form onSubmit={onSubmit} className="rounded-[1.75rem] border border-amber-400/20 bg-[radial-gradient(circle_at_top_left,rgba(245,158,11,0.14),transparent_36%),linear-gradient(180deg,rgba(255,255,255,0.04),rgba(255,255,255,0.02))] p-4 shadow-[0_18px_36px_rgba(2,6,23,0.16)]">
        <div className="mb-4">
          <div className="text-sm font-semibold text-[var(--text-primary)]">
            {isEditing ? "Edit competition" : "Add competition"}
          </div>
          <p className="mt-1 text-xs text-[var(--text-secondary)]">
            {isEditing
              ? "Update race timing and details without recreating the event."
              : "Add race timing and details so the coach can phase load and specificity around real demands."}
          </p>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <label className={LABEL_CLASS_NAME}>Name</label>
            <input className={INPUT_CLASS_NAME} value={form.name} onChange={(e) => updateForm("name", e.target.value)} required />
            <p className={HELP_TEXT_CLASS_NAME}>Use the exact event name so you can recognize it quickly in planning outputs.</p>
          </div>

          <div>
            <label className={LABEL_CLASS_NAME}>Exact date</label>
            <input className={INPUT_CLASS_NAME} type="date" value={form.date} onChange={(e) => updateForm("date", e.target.value)} />
            <p className={HELP_TEXT_CLASS_NAME}>Use an exact date whenever possible for accurate countdowns and taper timing.</p>
          </div>

          <div>
            <label className={LABEL_CLASS_NAME}>Approximate date</label>
            <input
              className={INPUT_CLASS_NAME}
              value={form.dateText}
              onChange={(e) => updateForm("dateText", e.target.value)}
              placeholder="e.g. Mid-October 2026"
            />
            <p className={HELP_TEXT_CLASS_NAME}>Use this when timing is fuzzy so planning still knows the rough target window.</p>
          </div>

          <div>
            <label className={LABEL_CLASS_NAME}>Race type</label>
            <input
              className={INPUT_CLASS_NAME}
              value={form.raceType}
              onChange={(e) => updateForm("raceType", e.target.value)}
              placeholder="Half Marathon / Olympic Tri / 38k Trail"
            />
            <p className={HELP_TEXT_CLASS_NAME}>Race type tells the planner which energy systems and session structures to prioritize.</p>
          </div>

          <div>
            <label className={LABEL_CLASS_NAME}>Priority</label>
            <select className={INPUT_CLASS_NAME} value={form.priority} onChange={(e) => updateForm("priority", e.target.value)}>
              <option value="">(none)</option>
              <option value="A">A</option>
              <option value="B">B</option>
              <option value="C">C</option>
            </select>
            <p className={HELP_TEXT_CLASS_NAME}>Priority defines which races deserve peak freshness versus training-race treatment.</p>
          </div>

          <div>
            <label className={LABEL_CLASS_NAME}>Target time</label>
            <input
              className={INPUT_CLASS_NAME}
              value={form.targetTime}
              onChange={(e) => updateForm("targetTime", e.target.value)}
              placeholder="01:40:00 or Sub 4h"
            />
            <p className={HELP_TEXT_CLASS_NAME}>Target time calibrates pacing ambition and helps balance risk versus goal pace.</p>
          </div>
        </div>

        <div className="mt-3">
          <label className={LABEL_CLASS_NAME}>Course and race notes</label>
          <textarea
            className={TEXTAREA_CLASS_NAME}
            value={form.notes}
            onChange={(e) => updateForm("notes", e.target.value)}
            rows={3}
            placeholder="Elevation profile, heat, terrain, fueling logistics..."
          />
          <p className={HELP_TEXT_CLASS_NAME}>
            Include terrain and course constraints so specificity is built early instead of crammed late.
          </p>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            className="rounded-xl bg-[linear-gradient(135deg,rgba(245,158,11,0.92),rgba(56,189,248,0.88))] px-4 py-2 font-semibold text-slate-950 transition hover:brightness-110 disabled:opacity-60"
            disabled={!canSubmit}
            type="submit"
          >
            {isSubmitting ? "Saving..." : isEditing ? "Save changes" : "Add competition"}
          </button>
          {isEditing ? (
            <button
              className="rounded-xl border border-white/10 px-4 py-2 text-sm font-semibold text-[var(--text-secondary)] transition hover:border-white/20 hover:text-[var(--text-primary)]"
              type="button"
              onClick={resetForm}
            >
              Cancel edit
            </button>
          ) : null}
        </div>
      </form>

      <div className="rounded-[1.75rem] border border-[var(--border)] bg-[var(--surface)] p-4 shadow-[0_18px_36px_rgba(2,6,23,0.14)]">
        <div className="mb-3 flex items-center justify-between">
          <div className="font-medium text-[var(--text-primary)]">Saved competitions</div>
          <button className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]" type="button" onClick={() => load()}>
            Refresh
          </button>
        </div>

        {state === "loading" ? <div className="text-sm text-[var(--text-secondary)]">Loading…</div> : null}
        {state === "loaded" && items.length === 0 ? <div className="text-sm text-[var(--text-secondary)]">No competitions yet.</div> : null}

        <ul className="space-y-3">
          {items.map((competition) => (
            <li key={competition.id} className="flex items-start justify-between gap-4 rounded-[1.2rem] border border-white/10 bg-white/[0.03] px-4 py-3">
              <div className="min-w-0">
                <div className="font-medium truncate text-[var(--text-primary)]">{competition.name}</div>
                <div className="text-sm text-[var(--text-secondary)]">
                  {competition.date ? formatDateHuman(competition.date) : competition.date_text || "No date"}
                  {competition.race_type ? ` · ${competition.race_type}` : ""}
                  {competition.priority ? ` · Priority ${competition.priority}` : ""}
                  {competition.target_time ? ` · Target ${competition.target_time}` : ""}
                </div>
                {competition.notes ? <div className="text-sm text-[var(--text-secondary)]">{competition.notes}</div> : null}
              </div>
              <div className="flex shrink-0 items-center gap-3">
                <button
                  className="text-sm text-amber-300 transition hover:text-amber-200"
                  type="button"
                  onClick={() => onEdit(competition)}
                >
                  Edit
                </button>
                <button
                  className="text-sm text-red-400 transition hover:text-red-300"
                  type="button"
                  onClick={() => onDelete(competition.id, competition.name)}
                >
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
