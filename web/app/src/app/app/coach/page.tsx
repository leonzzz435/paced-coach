import CoachInbox from "@/components/coach-chat/coach-inbox";
import { COACH_DESCRIPTION, COACH_LABEL, COACH_NAME } from "@/components/coach-chat/coach-inbox-parts";

type CoachInboxPageProps = {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

function readFirst(value: string | string[] | undefined): string | null {
  if (typeof value === "string") return value;
  if (Array.isArray(value) && value.length > 0 && typeof value[0] === "string") return value[0];
  return null;
}

export default async function CoachInboxPage({ searchParams }: CoachInboxPageProps) {
  const resolvedSearchParams = (await searchParams) ?? {};
  const initialThreadId = readFirst(resolvedSearchParams.thread_id);

  return (
    <div className="space-y-5">
      <div className="overflow-hidden rounded-[2rem] border border-[var(--border)]/80 bg-[radial-gradient(circle_at_top_left,_rgba(16,185,129,0.14),transparent_34%),radial-gradient(circle_at_top_right,_rgba(14,165,233,0.12),transparent_30%),linear-gradient(180deg,rgba(255,255,255,0.04),rgba(255,255,255,0.02))] px-5 py-5 shadow-[0_18px_54px_rgba(2,6,23,0.18)]">
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1.5fr)_minmax(280px,0.9fr)]">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--text-muted)]">{COACH_NAME}</div>
            <h1 className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-[var(--text-primary)]">{COACH_LABEL}</h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--text-secondary)]">{COACH_DESCRIPTION}</p>
            <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">
              Continue conversations, review recap proposals, and ask for schedule changes in one focused workspace.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
            <div className="rounded-[1.4rem] border border-white/10 bg-[var(--surface)]/92 px-4 py-3 shadow-[0_12px_28px_rgba(2,6,23,0.16)]">
              <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--text-muted)]">Good for</div>
              <div className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">Workout swaps, recovery questions, race planning, and recap follow-ups.</div>
            </div>
            <div className="rounded-[1.4rem] border border-white/10 bg-[var(--surface)]/92 px-4 py-3 shadow-[0_12px_28px_rgba(2,6,23,0.16)]">
              <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--text-muted)]">Context used</div>
              <div className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">
                Your declared profile, goals, current plan, prior coaching outputs, and connected activity/recovery data when available.
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="min-h-[72vh]">
        <CoachInbox active initialThreadId={initialThreadId} mode="embedded" />
      </div>
    </div>
  );
}
