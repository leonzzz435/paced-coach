"use client";

import { useEffect, useMemo } from "react";
import { ArrowRight, CalendarRange, ClipboardList, MessageSquareQuote, Sparkles, X } from "lucide-react";

import HtmlSnippet from "@/components/html_snippet";
import { openCoachThread } from "@/lib/types/ask-about";
import { weeklyRecapActionDescription, weeklyRecapActionLabel, weeklyRecapCoachCta, type WeeklyRecapReportResponse } from "@/lib/types/recap";

type Props = {
  open: boolean;
  report: WeeklyRecapReportResponse | null;
  loading: boolean;
  errorMessage: string | null;
  onClose: () => void;
};

const DATE_FORMATTER = new Intl.DateTimeFormat("en-US", {
  weekday: "short",
  month: "short",
  day: "numeric",
});

function formatWeekEnding(weekAnchorUtc: string): string {
  const parsed = new Date(weekAnchorUtc);
  if (Number.isNaN(parsed.getTime())) return "Weekly recap";
  return `Week ending ${DATE_FORMATTER.format(parsed)}`;
}

function formatAffectedDay(dayId: string): string {
  const parsed = new Date(dayId);
  if (Number.isNaN(parsed.getTime())) return dayId;
  return DATE_FORMATTER.format(parsed);
}

function summarizeProposalImpact(report: WeeklyRecapReportResponse | null): string | null {
  if (!report) return null;
  const ops = Array.isArray(report.recap.ops) ? report.recap.ops : [];
  if (ops.length === 0) return null;

  const affectedDays = Array.from(
    new Set(
      ops
        .map((op) => (typeof op?.day_id === "string" ? op.day_id : null))
        .filter((value): value is string => Boolean(value))
    )
  );

  if (affectedDays.length === 0) {
    return `${ops.length} proposed change${ops.length === 1 ? "" : "s"} ready for review.`;
  }

  const previewDays = affectedDays.slice(0, 3).map(formatAffectedDay);
  const overflow = affectedDays.length > 3 ? ` +${affectedDays.length - 3} more` : "";
  return `${ops.length} proposed change${ops.length === 1 ? "" : "s"} touching ${previewDays.join(", ")}${overflow}.`;
}

function LoadingState() {
  return (
    <div className="space-y-4">
      <div className="h-8 w-40 animate-pulse rounded-full bg-white/10" />
      <div className="h-24 animate-pulse rounded-2xl border border-white/10 bg-white/[0.04]" />
      <div className="grid gap-4">
        <div className="h-40 animate-pulse rounded-2xl border border-white/10 bg-white/[0.04]" />
        <div className="h-32 animate-pulse rounded-2xl border border-white/10 bg-white/[0.04]" />
      </div>
    </div>
  );
}

export default function WeeklyRecapReportPanel({ open, report, loading, errorMessage, onClose }: Props) {
  const proposalImpact = useMemo(() => summarizeProposalImpact(report), [report]);

  useEffect(() => {
    if (!open) return undefined;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [onClose, open]);

  if (!open) {
    return null;
  }

  const action = report?.pending_action ?? "none";
  const actionDescription = weeklyRecapActionDescription(action);
  const coachCta = weeklyRecapCoachCta(action);
  const showCoachAction = Boolean(report?.thread_id);

  return (
    <div className="fixed inset-0 z-[90]">
      <button
        aria-label="Close weekly recap report"
        className="absolute inset-0 bg-slate-950/72 backdrop-blur-sm"
        onClick={onClose}
        type="button"
      />

      <aside
        aria-labelledby="weekly-recap-panel-title"
        aria-modal="true"
        className="absolute inset-y-0 right-0 flex w-full max-w-[860px] flex-col border-l border-white/10 bg-[linear-gradient(180deg,rgba(15,23,42,0.98),rgba(15,23,42,0.95))] shadow-[-32px_0_80px_rgba(2,6,23,0.4)]"
        role="dialog"
      >
        <header className="border-b border-white/10 px-5 py-4 sm:px-6">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full border border-sky-400/20 bg-sky-400/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-sky-100">
                  Weekly recap report
                </span>
                {report ? (
                  <span className="rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-[var(--text-muted)]">
                    {weeklyRecapActionLabel(report.pending_action)}
                  </span>
                ) : null}
              </div>
              <h2
                className="mt-3 text-2xl font-semibold tracking-[-0.03em] text-[var(--text-primary)] sm:text-[2rem]"
                id="weekly-recap-panel-title"
              >
                {report ? formatWeekEnding(report.recap.week_anchor_utc) : "Weekly recap"}
              </h2>
              <p className="mt-2 max-w-2xl text-sm leading-relaxed text-[var(--text-secondary)]">{actionDescription}</p>
            </div>

            <button
              aria-label="Close weekly recap report"
              className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.04] text-[var(--text-secondary)] transition hover:bg-white/[0.08] hover:text-[var(--text-primary)]"
              onClick={onClose}
              type="button"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5 sm:px-6 sm:py-6">
          {loading ? <LoadingState /> : null}

          {!loading && errorMessage ? (
            <div className="rounded-2xl border border-rose-400/20 bg-rose-400/10 px-4 py-3 text-sm font-medium text-rose-100">
              {errorMessage}
            </div>
          ) : null}

          {!loading && !errorMessage && report ? (
            <div className="space-y-5">
              <section className="rounded-[1.5rem] border border-sky-400/18 bg-[radial-gradient(circle_at_top_left,rgba(56,189,248,0.14),transparent_42%),linear-gradient(180deg,rgba(255,255,255,0.04),rgba(255,255,255,0.02))] p-5">
                <div className="flex items-start gap-3">
                  <MessageSquareQuote className="mt-1 h-5 w-5 text-sky-200" />
                  <div className="min-w-0">
                    <div className="text-xs font-semibold uppercase tracking-[0.18em] text-sky-100">Top takeaway</div>
                    <p className="mt-2 text-lg font-semibold leading-snug text-[var(--text-primary)]">
                      {report.summary_preview ?? "Weekly recap ready to review."}
                    </p>
                  </div>
                </div>
              </section>

              {proposalImpact ? (
                <section className="rounded-[1.35rem] border border-emerald-400/18 bg-[linear-gradient(180deg,rgba(16,185,129,0.08),rgba(255,255,255,0.03))] p-5">
                  <div className="flex items-start gap-3">
                    <ClipboardList className="mt-1 h-5 w-5 text-emerald-200" />
                    <div>
                      <div className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-100">Plan impact</div>
                      <p className="mt-2 text-sm font-medium leading-relaxed text-[var(--text-primary)]">{proposalImpact}</p>
                    </div>
                  </div>
                </section>
              ) : null}

              {report.recap.follow_up_question ? (
                <section className="rounded-[1.35rem] border border-amber-400/18 bg-[linear-gradient(180deg,rgba(251,191,36,0.08),rgba(255,255,255,0.03))] p-5">
                  <div className="flex items-start gap-3">
                    <Sparkles className="mt-1 h-5 w-5 text-amber-200" />
                    <div className="min-w-0">
                      <div className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-100">Coach follow-up</div>
                      <p className="mt-2 text-sm font-medium leading-relaxed text-[var(--text-primary)]">
                        {report.recap.follow_up_question}
                      </p>
                      {report.recap.athlete_response ? (
                        <div className="mt-3 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3">
                          <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--text-muted)]">
                            Your response
                          </div>
                          <p className="mt-2 text-sm leading-relaxed text-[var(--text-secondary)]">
                            {report.recap.athlete_response}
                          </p>
                        </div>
                      ) : null}
                    </div>
                  </div>
                </section>
              ) : null}

              <section className="rounded-[1.5rem] border border-white/10 bg-white/[0.03] p-5">
                <div className="flex items-center gap-2">
                  <CalendarRange className="h-4 w-4 text-sky-200" />
                  <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-sky-100">This week</h3>
                </div>
                <div className="mt-4 space-y-3">
                  {report.recap.narrative.this_week_blocks.map((block) => (
                    <article key={block.key} className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-4">
                      {block.title ? (
                        <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--text-muted)]">
                          {block.title}
                        </div>
                      ) : null}
                      <HtmlSnippet className="pv-content mt-2 text-sm leading-7 text-[var(--text-secondary)]" html={block.content_html} />
                    </article>
                  ))}
                </div>
              </section>

              {report.recap.narrative.looking_ahead_blocks.length > 0 ? (
                <section className="rounded-[1.5rem] border border-white/10 bg-white/[0.03] p-5">
                  <div className="flex items-center gap-2">
                    <ArrowRight className="h-4 w-4 text-emerald-200" />
                    <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-emerald-100">Looking ahead</h3>
                  </div>
                  <div className="mt-4 space-y-3">
                    {report.recap.narrative.looking_ahead_blocks.map((block) => (
                      <article key={block.key} className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-4">
                        {block.title ? (
                          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--text-muted)]">
                            {block.title}
                          </div>
                        ) : null}
                        <HtmlSnippet className="pv-content mt-2 text-sm leading-7 text-[var(--text-secondary)]" html={block.content_html} />
                      </article>
                    ))}
                  </div>
                </section>
              ) : null}
            </div>
          ) : null}
        </div>

        <footer className="border-t border-white/10 bg-slate-950/50 px-5 py-4 sm:px-6">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-xs leading-relaxed text-[var(--text-muted)]">
              Weekly recap is now a report surface. Coach remains the place for follow-up replies and adjustment decisions.
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <button
                className="rounded-xl border border-white/10 bg-white/[0.04] px-4 py-2.5 text-sm font-semibold text-[var(--text-primary)] transition hover:bg-white/[0.08]"
                onClick={onClose}
                type="button"
              >
                Close
              </button>
              {showCoachAction ? (
                <button
                  className="inline-flex items-center gap-2 rounded-xl bg-[var(--accent-primary)] px-4 py-2.5 text-sm font-semibold text-white transition hover:brightness-110"
                  onClick={() => {
                    if (report?.thread_id) {
                      openCoachThread(report.thread_id);
                    }
                    onClose();
                  }}
                  type="button"
                >
                  {coachCta}
                  <ArrowRight className="h-4 w-4" />
                </button>
              ) : null}
            </div>
          </div>
        </footer>
      </aside>
    </div>
  );
}
