"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ChevronRight, Settings } from "lucide-react";

type AthleteProfileResponse = {
  user_id: string;
  profile: WizardProfile;
  updated_at?: string | null;
};

type LoadState = "loading" | "loaded" | "error";
type SaveState = "idle" | "saving" | "saved" | "error";

type WizardProfile = {
  physiology: {
    ftp?: number | null;
    lthr?: number | null;
    max_hr?: number | null;
    custom_zones?: string | null;
  };
  preferences: {
    sports?: string[] | null;
    excluded_sports?: string[] | null;
    injuries_limitations?: string | null;
    timezone?: string | null;
  };
  availability: {
    days_per_week?: number | null;
    time_windows?: string | null;
    upcoming_travel?: string | null;
  };
  goals: {
    primary_goal?: string | null;
    notes?: string | null;
  };
};

function asNumberOrNull(raw: string): number | null {
  const value = raw.trim();
  if (!value) return null;
  const numberValue = Number(value);
  return Number.isFinite(numberValue) ? numberValue : null;
}

function normalizeString(raw: string | null | undefined): string | null {
  if (raw == null) return null;
  const trimmed = raw.trim();
  return trimmed || null;
}

function normalizeStringList(raw: string): string[] | null {
  const items = raw
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  return items.length > 0 ? items : null;
}

function getBrowserTimezone(): string | null {
  const resolvedTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  return normalizeString(resolvedTimezone);
}

function getSupportedTimezones(): string[] {
  const intlWithSupportedValues = Intl as typeof Intl & {
    supportedValuesOf?: (key: string) => string[];
  };
  if (typeof intlWithSupportedValues.supportedValuesOf !== "function") return [];
  try {
    return intlWithSupportedValues.supportedValuesOf("timeZone");
  } catch {
    return [];
  }
}

function isRecognizedTimezone(timezoneName: string): boolean {
  try {
    new Intl.DateTimeFormat(undefined, { timeZone: timezoneName });
    return true;
  } catch {
    return false;
  }
}

function getTimezoneValidationMessage(timezoneName: string | null | undefined): string | null {
  const normalizedTimezone = normalizeString(timezoneName);
  if (!normalizedTimezone) return null;
  if (isRecognizedTimezone(normalizedTimezone)) return null;
  return "Enter a valid IANA timezone like Europe/Berlin or America/Los_Angeles.";
}

function extractErrorMessage(payload: unknown): string | null {
  if (typeof payload === "string") return normalizeString(payload);
  if (Array.isArray(payload)) {
    const firstMessage = payload.map(extractErrorMessage).find((message) => Boolean(message));
    return firstMessage ?? null;
  }
  if (!payload || typeof payload !== "object") return null;

  const record = payload as Record<string, unknown>;
  if (typeof record.msg === "string") {
    return normalizeString(record.msg.replace(/^Value error,\s*/, ""));
  }

  return (
    extractErrorMessage(record.detail) ??
    (typeof record.message === "string" ? normalizeString(record.message) : null) ??
    (typeof record.error === "string" ? normalizeString(record.error) : null)
  );
}

async function readErrorMessage(response: Response, fallback: string): Promise<string> {
  const raw = await response.text().catch(() => "");
  const normalized = normalizeString(raw);
  if (!normalized) return fallback;
  try {
    return extractErrorMessage(JSON.parse(normalized)) ?? normalized;
  } catch {
    return normalized;
  }
}

function defaultProfile(): WizardProfile {
  return {
    physiology: { ftp: null, lthr: null, max_hr: null, custom_zones: null },
    preferences: { sports: ["run", "bike", "swim"], excluded_sports: null, injuries_limitations: null, timezone: null },
    availability: { days_per_week: 5, time_windows: null, upcoming_travel: null },
    goals: { primary_goal: null, notes: null },
  };
}

function normalizeForSave(profile: WizardProfile, sportsInput: string, excludedSportsInput: string): WizardProfile {
  return {
    physiology: {
      ftp: profile.physiology.ftp ?? null,
      lthr: profile.physiology.lthr ?? null,
      max_hr: profile.physiology.max_hr ?? null,
      custom_zones: normalizeString(profile.physiology.custom_zones),
    },
    preferences: {
      sports: normalizeStringList(sportsInput),
      excluded_sports: normalizeStringList(excludedSportsInput),
      injuries_limitations: normalizeString(profile.preferences.injuries_limitations),
      timezone: normalizeString(profile.preferences.timezone),
    },
    availability: {
      days_per_week: profile.availability.days_per_week ?? null,
      time_windows: normalizeString(profile.availability.time_windows),
      upcoming_travel: normalizeString(profile.availability.upcoming_travel),
    },
    goals: {
      primary_goal: normalizeString(profile.goals.primary_goal),
      notes: normalizeString(profile.goals.notes),
    },
  };
}

const INPUT_CLASS_NAME =
  "mt-1 w-full rounded-xl border border-white/10 bg-[var(--surface-elevated)]/88 px-3 py-2 text-[var(--text-primary)] outline-none transition placeholder:text-[var(--text-muted)] focus:border-sky-400/40 focus:ring-2 focus:ring-sky-400/10";
const TEXTAREA_CLASS_NAME = `${INPUT_CLASS_NAME} resize-y`;
const LABEL_CLASS_NAME = "block text-sm font-medium text-[var(--text-primary)]";
const HELP_TEXT_CLASS_NAME = "mt-1 text-xs text-[var(--text-muted)]";
const SECTION_TITLE_CLASS_NAME = "font-semibold text-[var(--text-primary)]";
const SECTION_COPY_CLASS_NAME = "text-xs text-[var(--text-secondary)]";
const PHYSIOLOGY_SECTION_CLASS_NAME =
  "rounded-[1.75rem] border border-sky-400/20 bg-[radial-gradient(circle_at_top_left,rgba(56,189,248,0.14),transparent_38%),linear-gradient(180deg,rgba(255,255,255,0.04),rgba(255,255,255,0.02))] p-4 shadow-[0_18px_36px_rgba(2,6,23,0.16)]";
const REALITY_SECTION_CLASS_NAME =
  "rounded-[1.75rem] border border-amber-400/20 bg-[radial-gradient(circle_at_top_left,rgba(245,158,11,0.14),transparent_36%),linear-gradient(180deg,rgba(255,255,255,0.04),rgba(255,255,255,0.02))] p-4 shadow-[0_18px_36px_rgba(2,6,23,0.16)]";
const AVAILABILITY_SECTION_CLASS_NAME =
  "rounded-[1.75rem] border border-emerald-400/20 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.14),transparent_36%),linear-gradient(180deg,rgba(255,255,255,0.04),rgba(255,255,255,0.02))] p-4 shadow-[0_18px_36px_rgba(2,6,23,0.16)]";
const GOALS_SECTION_CLASS_NAME =
  "rounded-[1.75rem] border border-violet-400/20 bg-[radial-gradient(circle_at_top_left,rgba(139,92,246,0.14),transparent_36%),linear-gradient(180deg,rgba(255,255,255,0.04),rgba(255,255,255,0.02))] p-4 shadow-[0_18px_36px_rgba(2,6,23,0.16)]";
const SECONDARY_BUTTON_CLASS_NAME =
  "rounded-xl border border-white/10 bg-[var(--surface-elevated)] px-4 py-2 text-[var(--text-primary)] transition hover:bg-white/[0.05] disabled:opacity-60";
const PRIMARY_BUTTON_CLASS_NAME =
  "rounded-xl bg-[linear-gradient(135deg,rgba(56,189,248,0.92),rgba(16,185,129,0.88))] px-4 py-2 font-semibold text-slate-950 transition hover:brightness-110 disabled:opacity-60";

export default function AthleteProfilePage() {
  const [state, setState] = useState<LoadState>("loading");
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [profile, setProfile] = useState<WizardProfile>(defaultProfile());
  const [sportsInput, setSportsInput] = useState((defaultProfile().preferences.sports ?? []).join(", "));
  const [excludedSportsInput, setExcludedSportsInput] = useState("");
  const [browserTimezone, setBrowserTimezone] = useState<string | null>(null);
  const [timezoneSuggestions, setTimezoneSuggestions] = useState<string[]>([]);

  const hasAnyContent = useMemo(() => {
    const normalized = normalizeForSave(profile, sportsInput, excludedSportsInput);
    return Boolean(
      normalized.physiology.ftp ||
      normalized.physiology.lthr ||
      normalized.physiology.max_hr ||
      (normalized.preferences.sports ?? []).length > 0 ||
      (normalized.preferences.excluded_sports ?? []).length > 0 ||
      (normalized.preferences.injuries_limitations ?? "").trim() ||
      (normalized.preferences.timezone ?? "").trim() ||
      (normalized.availability.time_windows ?? "").trim() ||
      (normalized.availability.upcoming_travel ?? "").trim() ||
      (normalized.goals.primary_goal ?? "").trim() ||
      (normalized.goals.notes ?? "").trim(),
    );
  }, [excludedSportsInput, profile, sportsInput]);
  const timezoneValidationMessage = useMemo(
    () => getTimezoneValidationMessage(profile.preferences.timezone),
    [profile.preferences.timezone]
  );

  async function load() {
    setState("loading");
    setError(null);
    try {
      const res = await fetch("/app/api/athlete-profile", { cache: "no-store" });
      if (!res.ok) throw new Error("Failed to load athlete profile");
      const data = (await res.json()) as AthleteProfileResponse;
      const stored = data.profile ?? defaultProfile();
      const merged: WizardProfile = {
        ...defaultProfile(),
        ...stored,
        physiology: { ...defaultProfile().physiology, ...(stored.physiology ?? {}) },
        preferences: { ...defaultProfile().preferences, ...(stored.preferences ?? {}) },
        availability: { ...defaultProfile().availability, ...(stored.availability ?? {}) },
        goals: { ...defaultProfile().goals, ...(stored.goals ?? {}) },
      };
      const detectedTimezone = getBrowserTimezone();
      if (!merged.preferences.timezone && detectedTimezone) {
        merged.preferences.timezone = detectedTimezone;
      }

      setProfile(merged);
      setSportsInput((merged.preferences.sports ?? []).join(", "));
      setExcludedSportsInput((merged.preferences.excluded_sports ?? []).join(", "));
      setState("loaded");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load athlete profile");
      setState("error");
    }
  }

  useEffect(() => {
    setBrowserTimezone(getBrowserTimezone());
    setTimezoneSuggestions(getSupportedTimezones());
    void load();
  }, []);

  async function onSave(e: React.FormEvent) {
    e.preventDefault();
    setSaveState("saving");
    setError(null);
    try {
      if (timezoneValidationMessage) {
        throw new Error(timezoneValidationMessage);
      }
      const normalizedProfile = normalizeForSave(profile, sportsInput, excludedSportsInput);
      const res = await fetch("/app/api/athlete-profile", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile: normalizedProfile }),
      });
      if (!res.ok) throw new Error(await readErrorMessage(res, "Failed to save athlete profile"));

      setProfile(normalizedProfile);
      setSportsInput((normalizedProfile.preferences.sports ?? []).join(", "));
      setExcludedSportsInput((normalizedProfile.preferences.excluded_sports ?? []).join(", "));
      setSaveState("saved");
      setTimeout(() => setSaveState("idle"), 1200);
    } catch (e) {
      setSaveState("error");
      setError(e instanceof Error ? e.message : "Failed to save athlete profile");
    }
  }

  return (
    <div className="space-y-4">
      <div className="overflow-hidden rounded-[2rem] border border-[var(--border)] bg-[radial-gradient(circle_at_top_left,rgba(56,189,248,0.12),transparent_36%),radial-gradient(circle_at_bottom_right,rgba(16,185,129,0.10),transparent_34%),linear-gradient(180deg,rgba(255,255,255,0.04),rgba(255,255,255,0.02))] px-5 py-5 shadow-[0_18px_48px_rgba(2,6,23,0.16)]">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--text-muted)]">Athlete Profile</div>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight text-[var(--text-primary)]">Athlete profile</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--text-secondary)]">
              Lock in physiology, constraints, availability, and goals so every plan starts from the same trusted baseline.
            </p>
          </div>
          <Link className="text-sm text-sky-300 transition hover:text-sky-200" href="/app/new">
            Generate plans
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3">
        <Link
          className="group rounded-[1.75rem] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.04),rgba(255,255,255,0.02))] p-4 shadow-[0_18px_36px_rgba(2,6,23,0.14)] transition hover:border-sky-400/30 hover:bg-sky-400/8"
          href="/app/settings"
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--text-muted)]">Account & Data</div>
              <div className="mt-2 text-lg font-semibold tracking-tight text-[var(--text-primary)]">Settings</div>
              <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">
                Manage Strava, WHOOP, sync status, and account deletion from one place.
              </p>
            </div>
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-sky-400/10 text-sky-300">
              <Settings className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-4 flex items-center gap-2 text-sm font-semibold text-sky-300">
            Open settings
            <ChevronRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
          </div>
        </Link>
      </div>

      {state === "error" ? <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4 text-sm text-red-400">{error}</div> : null}

      <form onSubmit={onSave} className="space-y-4">
        <section className={PHYSIOLOGY_SECTION_CLASS_NAME}>
          <div className="mb-3">
            <div className={SECTION_TITLE_CLASS_NAME}>Physiology baselines</div>
            <p className={SECTION_COPY_CLASS_NAME}>Set trusted baseline numbers so your zones and workload interpretation stay anchored.</p>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div>
              <label className={LABEL_CLASS_NAME}>FTP (watts)</label>
              <input
                className={INPUT_CLASS_NAME}
                inputMode="numeric"
                value={profile.physiology.ftp ?? ""}
                onChange={(e) =>
                  setProfile((prev) => ({ ...prev, physiology: { ...prev.physiology, ftp: asNumberOrNull(e.target.value) } }))
                }
                placeholder="e.g. 250"
              />
              <p className={HELP_TEXT_CLASS_NAME}>Enter your latest trusted FTP so bike sessions use realistic intensity anchors.</p>
            </div>
            <div>
              <label className={LABEL_CLASS_NAME}>LTHR (bpm)</label>
              <input
                className={INPUT_CLASS_NAME}
                inputMode="numeric"
                value={profile.physiology.lthr ?? ""}
                onChange={(e) =>
                  setProfile((prev) => ({ ...prev, physiology: { ...prev.physiology, lthr: asNumberOrNull(e.target.value) } }))
                }
                placeholder="e.g. 172"
              />
              <p className={HELP_TEXT_CLASS_NAME}>Use your current threshold heart rate so threshold and tempo calls are personalized.</p>
            </div>
            <div>
              <label className={LABEL_CLASS_NAME}>Max HR (bpm)</label>
              <input
                className={INPUT_CLASS_NAME}
                inputMode="numeric"
                value={profile.physiology.max_hr ?? ""}
                onChange={(e) =>
                  setProfile((prev) => ({ ...prev, physiology: { ...prev.physiology, max_hr: asNumberOrNull(e.target.value) } }))
                }
                placeholder="e.g. 190"
              />
              <p className={HELP_TEXT_CLASS_NAME}>Add max HR when known so heart-rate guardrails remain safe under fatigue.</p>
            </div>
          </div>

          <div className="mt-3">
            <label className={LABEL_CLASS_NAME}>Custom zones (optional)</label>
            <textarea
              className={TEXTAREA_CLASS_NAME}
              rows={2}
              value={profile.physiology.custom_zones ?? ""}
              onChange={(e) =>
                setProfile((prev) => ({ ...prev, physiology: { ...prev.physiology, custom_zones: e.target.value } }))
              }
              placeholder="Define your own training zones. If left empty, the coach will calculate them based on FTP/LTHR/Max HR."
            />
            <p className={HELP_TEXT_CLASS_NAME}>Add caveats or custom zones if device zones are unreliable.</p>
          </div>
        </section>

        <section className={REALITY_SECTION_CLASS_NAME}>
          <div className="mb-3">
            <div className={SECTION_TITLE_CLASS_NAME}>Training reality</div>
            <p className={SECTION_COPY_CLASS_NAME}>Capture what you can train, what you avoid, and any limits that should shape every plan.</p>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label className={LABEL_CLASS_NAME}>Sports (comma separated)</label>
              <input
                className={INPUT_CLASS_NAME}
                value={sportsInput}
                onChange={(e) => setSportsInput(e.target.value)}
                placeholder="run, bike, swim"
              />
              <p className={HELP_TEXT_CLASS_NAME}>List the disciplines you actively train so weekly structure matches your real program.</p>
            </div>
            <div>
              <label className={LABEL_CLASS_NAME}>Excluded sports (comma separated)</label>
              <input
                className={INPUT_CLASS_NAME}
                value={excludedSportsInput}
                onChange={(e) => setExcludedSportsInput(e.target.value)}
                placeholder="no swim, no downhill running"
              />
              <p className={HELP_TEXT_CLASS_NAME}>List activities to avoid so the planner does not prescribe unusable sessions.</p>
            </div>
          </div>

          <div className="mt-3">
            <label className={LABEL_CLASS_NAME}>Injuries / limitations</label>
            <textarea
              className={TEXTAREA_CLASS_NAME}
              value={profile.preferences.injuries_limitations ?? ""}
              onChange={(e) =>
                setProfile((prev) => ({
                  ...prev,
                  preferences: { ...prev.preferences, injuries_limitations: e.target.value },
                }))
              }
              rows={3}
              placeholder="Anything that should shape training (e.g. Achilles load tolerance, no hard descents)"
            />
            <p className={HELP_TEXT_CLASS_NAME}>Describe constraints clearly so progression stays effective without re-triggering setbacks.</p>
          </div>

          <div className="mt-3">
            <div className="flex items-center justify-between gap-3">
              <label className={LABEL_CLASS_NAME}>Timezone</label>
              <button
                className="text-xs font-medium text-[var(--text-secondary)] underline decoration-[var(--border)] underline-offset-4 hover:text-[var(--text-primary)] disabled:cursor-not-allowed disabled:opacity-50"
                type="button"
                disabled={!browserTimezone}
                onClick={() => {
                  if (!browserTimezone) return;
                  setError(null);
                  setSaveState("idle");
                  setProfile((prev) => ({
                    ...prev,
                    preferences: { ...prev.preferences, timezone: browserTimezone },
                  }));
                }}
              >
                Use browser timezone
              </button>
            </div>
            <input
              className={INPUT_CLASS_NAME}
              list="athlete-timezone-options"
              aria-invalid={timezoneValidationMessage ? true : undefined}
              value={profile.preferences.timezone ?? ""}
              onChange={(e) => {
                setError(null);
                setSaveState("idle");
                setProfile((prev) => ({
                  ...prev,
                  preferences: { ...prev.preferences, timezone: e.target.value },
                }));
              }}
              placeholder="America/Los_Angeles"
            />
            {timezoneSuggestions.length > 0 ? (
              <datalist id="athlete-timezone-options">
                {timezoneSuggestions.map((timezone) => (
                  <option key={timezone} value={timezone} />
                ))}
              </datalist>
            ) : null}
            <p className={HELP_TEXT_CLASS_NAME}>
              Type or pick an IANA timezone so daily syncs and weekly recap windows reset on your local calendar day.
            </p>
            {browserTimezone ? (
              <p className={HELP_TEXT_CLASS_NAME}>Detected in this browser: {browserTimezone}</p>
            ) : null}
            {timezoneValidationMessage ? <p className="mt-1 text-xs text-red-400">{timezoneValidationMessage}</p> : null}
          </div>
        </section>

        <section className={AVAILABILITY_SECTION_CLASS_NAME}>
          <div className="mb-3">
            <div className={SECTION_TITLE_CLASS_NAME}>Availability</div>
            <p className={SECTION_COPY_CLASS_NAME}>Define training bandwidth so plans fit your week instead of fighting your schedule.</p>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label className={LABEL_CLASS_NAME}>Days per week</label>
              <input
                className={INPUT_CLASS_NAME}
                inputMode="numeric"
                value={profile.availability.days_per_week ?? ""}
                onChange={(e) =>
                  setProfile((prev) => ({
                    ...prev,
                    availability: { ...prev.availability, days_per_week: asNumberOrNull(e.target.value) },
                  }))
                }
                placeholder="e.g. 5"
              />
              <p className={HELP_TEXT_CLASS_NAME}>Set a realistic training frequency so progression logic stays sustainable.</p>
            </div>
            <div>
              <label className={LABEL_CLASS_NAME}>Time windows</label>
              <input
                className={INPUT_CLASS_NAME}
                value={profile.availability.time_windows ?? ""}
                onChange={(e) =>
                  setProfile((prev) => ({ ...prev, availability: { ...prev.availability, time_windows: e.target.value } }))
                }
                placeholder='Mon/Wed 45m, Sat 2h, Sun 90m'
              />
              <p className={HELP_TEXT_CLASS_NAME}>Write rough daily windows so workout placement reflects when you can actually train.</p>
            </div>
          </div>
          <div className="mt-3">
            <label className={LABEL_CLASS_NAME}>Upcoming travel</label>
            <input
              className={INPUT_CLASS_NAME}
              value={profile.availability.upcoming_travel ?? ""}
              onChange={(e) =>
                setProfile((prev) => ({ ...prev, availability: { ...prev.availability, upcoming_travel: e.target.value } }))
              }
              placeholder="Dates + constraints (time zone, no bike access, etc.)"
            />
            <p className={HELP_TEXT_CLASS_NAME}>Call out travel and logistics early so short-term plans absorb disruption cleanly.</p>
          </div>
        </section>

        <section className={GOALS_SECTION_CLASS_NAME}>
          <div className="mb-3">
            <div className={SECTION_TITLE_CLASS_NAME}>Goals</div>
            <p className={SECTION_COPY_CLASS_NAME}>State outcomes and timeline so load progression aligns with what success means for you.</p>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-1">
            <div>
              <label className={LABEL_CLASS_NAME}>Primary goal</label>
              <input
                className={INPUT_CLASS_NAME}
                value={profile.goals.primary_goal ?? ""}
                onChange={(e) => setProfile((prev) => ({ ...prev, goals: { ...prev.goals, primary_goal: e.target.value } }))}
                placeholder="e.g. Sub-1:40 half marathon"
              />
              <p className={HELP_TEXT_CLASS_NAME}>Describe the main objective so tradeoffs between fitness, risk, and specificity stay coherent.</p>
            </div>
          </div>

          <div className="mt-3">
            <label className={LABEL_CLASS_NAME}>Additional notes</label>
            <textarea
              className={TEXTAREA_CLASS_NAME}
              value={profile.goals.notes ?? ""}
              onChange={(e) => setProfile((prev) => ({ ...prev, goals: { ...prev.goals, notes: e.target.value } }))}
              rows={3}
              placeholder='Anything else the coach should know, including quoted constraints like "no doubles on Thursdays".'
            />
            <p className={HELP_TEXT_CLASS_NAME}>Use this for nuances that don’t fit elsewhere but strongly influence plan quality.</p>
          </div>
        </section>

        <section className="flex flex-wrap items-center justify-between gap-3 rounded-[1.75rem] border border-[var(--border)] bg-[var(--surface)] p-4 shadow-[0_18px_36px_rgba(2,6,23,0.14)]">
          <p className="text-sm text-[var(--text-secondary)]">Your profile is snapshotted into each run to make outputs reproducible and debuggable.</p>
          <div className="flex items-center gap-2">
            <button
              className={SECONDARY_BUTTON_CLASS_NAME}
              type="button"
              onClick={() => {
                if (!window.confirm("Reset all profile fields to defaults? Unsaved changes will be lost.")) return;
                const defaults = defaultProfile();
                setProfile(defaults);
                setSportsInput((defaults.preferences.sports ?? []).join(", "));
                setExcludedSportsInput("");
                setSaveState("idle");
              }}
            >
              Reset
            </button>
            <button
              className={PRIMARY_BUTTON_CLASS_NAME}
              disabled={saveState === "saving" || state === "loading" || !hasAnyContent || Boolean(timezoneValidationMessage)}
              type="submit"
            >
              {saveState === "saving"
                ? "Saving…"
                : saveState === "saved"
                  ? "Saved"
                  : saveState === "error"
                    ? "Retry save"
                    : "Save profile"}
            </button>
          </div>
        </section>

        {error ? <p className="text-sm text-red-400">{error}</p> : null}
      </form>
    </div>
  );
}
