"use client";

import { useEffect, useMemo, useState } from "react";
import { usePathname } from "next/navigation";
import { MessageSquareQuote } from "lucide-react";

import CoachInbox from "@/components/coach-chat/coach-inbox";
import { COACH_NAME } from "@/components/coach-chat/coach-inbox-parts";
import type { CoachTurnUiContext } from "@/lib/types/coach";
import { subscribeCoachOpenThread, subscribeCoachPrefill } from "@/lib/types/ask-about";

export default function CoachMessenger() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [badgeCount, setBadgeCount] = useState(0);
  const [prefillMessage, setPrefillMessage] = useState<string | null>(null);
  const [prefillContext, setPrefillContext] = useState<CoachTurnUiContext | null>(null);
  const [navigateThreadId, setNavigateThreadId] = useState<string | null>(null);

  useEffect(() => {
    return subscribeCoachPrefill((payload) => {
      setPrefillMessage(payload.message);
      setPrefillContext(payload.uiContext ?? null);
      setOpen(true);
    });
  }, []);

  useEffect(() => {
    return subscribeCoachOpenThread((threadId) => {
      setNavigateThreadId(threadId);
      setOpen(true);
    });
  }, []);

  const hiddenOnCoachPage = useMemo(() => pathname.startsWith("/app/coach"), [pathname]);
  if (hiddenOnCoachPage) {
    return null;
  }

  return (
    <>
      {open ? (
        <button
          className="fixed inset-0 z-50 bg-zinc-950/35 backdrop-blur-[2px]"
          type="button"
          aria-label="Close coach panel"
          onClick={() => {
            setOpen(false);
            setNavigateThreadId(null);
          }}
        />
      ) : null}

      <div className="pointer-events-none fixed inset-0 z-[60] p-0 md:p-5" aria-hidden={!open}>
        <aside
          className={`ml-auto flex h-full w-full max-w-[560px] flex-col overflow-hidden border border-white/10 bg-[linear-gradient(180deg,rgba(15,23,42,0.98),rgba(15,23,42,0.94))] shadow-[0_30px_90px_rgba(2,6,23,0.36)] backdrop-blur-xl transition-all duration-300 ease-out md:rounded-[2rem] ${
            open ? "pointer-events-auto translate-y-0 opacity-100 md:translate-x-0" : "pointer-events-none translate-y-6 opacity-0 md:translate-x-8"
          }`}
        >
          <CoachInbox
            mode="panel"
            active
            onBadgeCountChange={setBadgeCount}
            prefillMessage={prefillMessage}
            prefillContext={prefillContext}
            onPrefillConsumed={() => {
              setPrefillMessage(null);
              setPrefillContext(null);
            }}
            initialThreadId={navigateThreadId}
            onRequestClose={() => {
              setOpen(false);
              setNavigateThreadId(null);
            }}
          />
        </aside>
      </div>

      <button
        className="fixed bottom-5 right-5 z-30 hidden items-center gap-3 rounded-[1.4rem] border border-white/10 bg-[linear-gradient(180deg,rgba(15,23,42,0.96),rgba(15,23,42,0.92))] px-3.5 py-3 text-left text-[var(--text-primary)] shadow-[0_16px_40px_rgba(2,6,23,0.24)] backdrop-blur transition hover:-translate-y-0.5 hover:shadow-[0_22px_48px_rgba(2,6,23,0.3)] lg:flex"
        type="button"
        onClick={() => setOpen((previous) => !previous)}
      >
        <span className="inline-flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-500 via-teal-500 to-sky-600 text-white shadow-[0_10px_24px_rgba(14,116,144,0.28)]">
          <MessageSquareQuote className="h-5 w-5" />
        </span>
        <span className="min-w-0">
          <span className="block text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--text-muted)]">{COACH_NAME}</span>
          <span className="block text-sm font-semibold">{open ? "Close coaching panel" : "Open coaching chat"}</span>
        </span>
        {badgeCount > 0 ? (
          <span className="inline-flex h-7 min-w-7 items-center justify-center rounded-full bg-emerald-500 px-1.5 text-[11px] font-semibold text-white">
            {badgeCount > 99 ? "99+" : badgeCount}
          </span>
        ) : null}
      </button>
    </>
  );
}
