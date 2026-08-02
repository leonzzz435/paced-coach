"use client";

import { FormEvent, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkBreaks from "remark-breaks";
import remarkGfm from "remark-gfm";

type CoachClarification = {
  question: string;
  reason_markdown: string;
  requested_field: string;
};

const RESUME_KEY_PREFIX = "paced-coach:clarification-resume";

export function clarificationResumeStorageKey(jobId: string, requestedField: string): string {
  return `${RESUME_KEY_PREFIX}:${jobId}:${requestedField}`;
}

function browserSessionStorage(): Storage | undefined {
  try {
    return typeof window === "undefined" ? undefined : window.sessionStorage;
  } catch {
    return undefined;
  }
}

export function getOrCreateClarificationResumeKey(
  jobId: string,
  requestedField: string,
  storage: Storage | undefined = browserSessionStorage(),
): string {
  const storageKey = clarificationResumeStorageKey(jobId, requestedField);
  let existing: string | undefined;
  try {
    existing = storage?.getItem(storageKey)?.trim();
  } catch {
    existing = undefined;
  }
  if (existing) return existing;

  const idempotencyKey = crypto.randomUUID();
  try {
    storage?.setItem(storageKey, idempotencyKey);
  } catch {
    // A blocked session store must not prevent a local resume request.
  }
  return idempotencyKey;
}

export function clearClarificationResumeKey(
  jobId: string,
  requestedField: string,
  storage: Storage | undefined = browserSessionStorage(),
): void {
  try {
    storage?.removeItem(clarificationResumeStorageKey(jobId, requestedField));
  } catch {
    // Nothing else is required once the server acknowledged the request.
  }
}

export default function CoachClarificationCard({
  jobId,
  clarification,
  onResumed,
  onStatusRecovery,
}: {
  jobId: string;
  clarification: CoachClarification;
  onResumed: () => void;
  onStatusRecovery?: () => void;
}) {
  const [answer, setAnswer] = useState("");
  const [state, setState] = useState<"idle" | "sending" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedAnswer = answer.trim();
    if (!normalizedAnswer || state === "sending") return;
    setState("sending");
    setError(null);
    try {
      const idempotencyKey = getOrCreateClarificationResumeKey(jobId, clarification.requested_field);
      const response = await fetch(`/app/api/analysis/${jobId}/resume`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          answer: normalizedAnswer,
          idempotency_key: idempotencyKey,
        }),
      });
      if (!response.ok) throw new Error(await response.text());
      clearClarificationResumeKey(jobId, clarification.requested_field);
      onResumed();
    } catch (caught) {
      setState("error");
      setError(caught instanceof Error ? caught.message : "Could not send your answer");
    } finally {
      onStatusRecovery?.();
    }
  }

  return (
    <section className="overflow-hidden rounded-2xl border border-sky-400/30 bg-[linear-gradient(145deg,rgba(14,116,144,0.16),rgba(15,23,42,0.96))] p-5 shadow-[0_24px_70px_rgba(14,165,233,0.14)] sm:p-6">
      <div className="text-xs font-bold uppercase tracking-[0.18em] text-sky-300">Your coach needs one answer</div>
      <h2 className="mt-3 max-w-2xl text-xl font-semibold leading-8 text-[var(--text-primary)]">
        {clarification.question}
      </h2>
      <div className="mt-2 max-w-2xl text-sm leading-6 text-[var(--text-secondary)]">
        <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>{clarification.reason_markdown}</ReactMarkdown>
      </div>
      <form className="mt-5 space-y-3" onSubmit={submit}>
        <label className="block text-sm font-medium text-[var(--text-primary)]" htmlFor="coach-clarification-answer">
          Your answer
        </label>
        <textarea
          id="coach-clarification-answer"
          className="min-h-28 w-full resize-y rounded-xl border border-[var(--border-accent)] bg-black/20 px-4 py-3 text-sm leading-6 text-[var(--text-primary)] outline-none transition placeholder:text-[var(--text-muted)] focus:border-sky-400 focus:ring-2 focus:ring-sky-400/20"
          maxLength={4000}
          placeholder={`Add the information for ${clarification.requested_field.replaceAll("_", " ")}...`}
          value={answer}
          onChange={(event) => setAnswer(event.target.value)}
        />
        <div className="flex flex-wrap items-center gap-3">
          <button
            className="rounded-xl bg-sky-500 px-5 py-2.5 text-sm font-bold text-white transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={!answer.trim() || state === "sending"}
            type="submit"
          >
            {state === "sending" ? "Sending..." : "Continue building my plan"}
          </button>
          <span className="text-xs text-[var(--text-muted)]">The same planning run will continue from here.</span>
        </div>
        {error ? <p className="text-sm text-rose-300">{error}</p> : null}
      </form>
    </section>
  );
}
