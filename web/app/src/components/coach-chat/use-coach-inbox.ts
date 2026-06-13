"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import {
  computeCoachInboxBadgeCount,
  deriveCoachThreadSignals,
  type CoachThreadSignals,
} from "@/lib/coach/inbox";
import type {
  CoachThreadListItem,
  CoachThreadResponse,
  CoachThreadsResponse,
  CoachThreadMessage,
  CoachTurnResponse,
  CoachTurnUiContext,
} from "@/lib/types/coach";
import {
  type BusyAction,
  type CoachTurnStatusEvent,
  type InboxView,
  DEFAULT_COACH_STATUS_MESSAGE,
  CoachStreamServerError,
  readErrorMessage,
  isThreadNotFoundError,
  readCoachTurnSse,
  idempotencyKey,
  trackCoachEvent,
  threadTitle,
  isCoachTurnResponse,
  buildThreadUrl,
} from "./coach-inbox-parts";

type UseCoachInboxOptions = {
  active?: boolean;
  onBadgeCountChange?: (count: number) => void;
  prefillMessage?: string | null;
  prefillContext?: CoachTurnUiContext | null;
  onPrefillConsumed?: () => void;
  initialThreadId?: string | null;
};

type ActionResult = {
  ok: boolean;
  turnPayload: CoachTurnResponse | null;
};

type OptimisticAthleteMessage = {
  id: string;
  created_at: string;
  text: string;
};

function fallbackThreadPayload(item: CoachThreadListItem): CoachThreadResponse {
  return {
    thread: {
      id: item.id,
      status: item.status,
      title: item.title,
      latest_seq: item.latest_seq,
      updated_at: item.updated_at,
    },
    week_anchor_utc: "",
    messages: item.messages ?? [],
    quota: { week_anchor_utc: "", used: 0, limit: 0, remaining: 0, is_limited: false },
    can_send_message: false,
    coach_gate_message: null,
    coach_gate_target: null,
    has_pending_proposal: item.has_pending_proposal ?? false,
    can_trigger_recap: false,
    training_provider_message: null,
    recap_gate_target: null,
    pending_proposal_ids: [],
    next_after_seq: null,
  };
}

function threadIncludesRecap(messages: CoachThreadMessage[] | undefined): boolean {
  return (messages ?? []).some((message) => message.kind === "recap");
}

function clearDraftThread(previous: CoachThreadResponse | null): CoachThreadResponse | null {
  if (!previous) return previous;
  return {
    ...previous,
    thread: undefined,
    messages: [],
    has_pending_proposal: false,
    pending_proposal_ids: [],
    next_after_seq: null,
  };
}

function toThreadResponsePayload(
  payload: CoachTurnResponse,
  previous: CoachThreadResponse | null
): CoachThreadResponse {
  return {
    thread: payload.thread,
    week_anchor_utc: previous?.week_anchor_utc ?? new Date().toISOString(),
    messages: payload.projection.messages,
    quota: payload.projection.quota,
    can_send_message: payload.projection.can_send_message,
    coach_gate_message: payload.projection.coach_gate_message ?? null,
    coach_gate_target: payload.projection.coach_gate_target ?? null,
    has_pending_proposal: payload.projection.has_pending_proposal,
    can_trigger_recap: payload.projection.can_trigger_recap,
    training_provider_message: payload.projection.training_provider_message ?? null,
    recap_gate_target: payload.projection.recap_gate_target ?? null,
    pending_proposal_ids: payload.projection.pending_proposal_ids,
    next_after_seq: payload.projection.next_after_seq ?? null,
  };
}

function upsertThreadListItem(items: CoachThreadListItem[], payload: CoachTurnResponse): CoachThreadListItem[] {
  const existing = items.find((item) => item.id === payload.thread.id);
  const nextItem: CoachThreadListItem = {
    id: payload.thread.id,
    status: payload.thread.status,
    title: payload.thread.title,
    latest_seq: payload.thread.latest_seq,
    created_at: existing?.created_at ?? payload.projection.messages[0]?.created_at ?? payload.thread.updated_at,
    updated_at: payload.thread.updated_at,
    messages: payload.projection.messages,
    has_pending_proposal: payload.projection.has_pending_proposal,
  };

  return [nextItem, ...items.filter((item) => item.id !== payload.thread.id)];
}

export function useCoachInbox({
  active = true,
  onBadgeCountChange,
  prefillMessage = null,
  prefillContext = null,
  onPrefillConsumed,
  initialThreadId = null,
}: UseCoachInboxOptions) {
  const router = useRouter();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messageRefs = useRef<Record<string, HTMLDivElement | null>>({});

  const [loading, setLoading] = useState(false);
  const [threadsLoading, setThreadsLoading] = useState(false);
  const [thread, setThread] = useState<CoachThreadResponse | null>(null);
  const [threadList, setThreadList] = useState<CoachThreadsResponse | null>(null);
  const [threadSignals, setThreadSignals] = useState<Record<string, CoachThreadSignals>>({});
  const [selectedThreadId, setSelectedThreadId] = useState<string | null>(null);
  const [view, setView] = useState<InboxView>("thread_list");
  const [showAllArchived, setShowAllArchived] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [input, setInputValue] = useState("");
  const [busyAction, setBusyAction] = useState<BusyAction | null>(null);
  const [busyProposalId, setBusyProposalId] = useState<string | null>(null);
  const [liveStatusEvent, setLiveStatusEvent] = useState<CoachTurnStatusEvent | null>(null);
  const [proposalRejectReasons, setProposalRejectReasons] = useState<Record<string, string>>({});
  const [scrollTargetId, setScrollTargetId] = useState<string | null>(null);
  const [confirmingArchive, setConfirmingArchive] = useState(false);
  const [optimisticAthleteMessage, setOptimisticAthleteMessage] = useState<OptimisticAthleteMessage | null>(null);
  const [pendingUiContext, setPendingUiContext] = useState<CoachTurnUiContext | null>(null);
  const [prefillAnchorMessage, setPrefillAnchorMessage] = useState<string | null>(null);

  const clearPendingUiContext = useCallback(() => {
    setPendingUiContext(null);
    setPrefillAnchorMessage(null);
  }, []);

  const setInput = useCallback(
    (value: string) => {
      setInputValue(value);
      if (!pendingUiContext) return;

      const trimmedValue = value.trim();
      const anchor = prefillAnchorMessage?.trim() ?? null;
      if (!trimmedValue || !anchor || trimmedValue.startsWith(anchor)) {
        return;
      }

      clearPendingUiContext();
    },
    [clearPendingUiContext, pendingUiContext, prefillAnchorMessage]
  );

  const requestThread = useCallback(async (threadId: string | null): Promise<CoachThreadResponse> => {
    const response = await fetch(buildThreadUrl(threadId), { method: "GET", cache: "no-store" });
    if (!response.ok) throw new Error(await readErrorMessage(response));
    return (await response.json()) as CoachThreadResponse;
  }, []);

  const requestThreads = useCallback(async (): Promise<CoachThreadsResponse> => {
    const response = await fetch("/app/api/coach/threads?limit=30", { method: "GET", cache: "no-store" });
    if (!response.ok) throw new Error(await readErrorMessage(response));
    return (await response.json()) as CoachThreadsResponse;
  }, []);

  const refreshSignals = useCallback(
    async (items: CoachThreadListItem[], preloaded: Record<string, CoachThreadResponse> = {}) => {
      const signalsById: Record<string, CoachThreadSignals> = {};

      for (const item of items) {
        const payload = preloaded[item.id] ?? fallbackThreadPayload(item);
        signalsById[item.id] = deriveCoachThreadSignals(payload);
      }

      setThreadSignals(signalsById);
      const nextBadgeCount = computeCoachInboxBadgeCount(
        items
          .map((item) => {
            const signals = signalsById[item.id];
            return signals ? { status: item.status, signals } : null;
          })
          .filter((entry): entry is { status: "active" | "archived"; signals: CoachThreadSignals } => entry !== null)
      );
      onBadgeCountChange?.(nextBadgeCount);
    },
    [onBadgeCountChange]
  );

  const bootstrap = useCallback(
    async (preferredThreadId: string | null = null) => {
      setLoading(true);
      setThreadsLoading(true);
      setError(null);
      setOptimisticAthleteMessage(null);

      try {
        const threadsPayload = await requestThreads();
        let threadPayload: CoachThreadResponse;
        let resolvedThreadId = preferredThreadId;

        if (preferredThreadId) {
          try {
            threadPayload = await requestThread(preferredThreadId);
          } catch (threadError) {
            if (!isThreadNotFoundError(threadError)) throw threadError;
            const fallbackThreadId =
              threadsPayload.items.find((item) => item.status === "active")?.id ?? threadsPayload.items[0]?.id ?? null;
            threadPayload = await requestThread(fallbackThreadId);
            resolvedThreadId = fallbackThreadId;
          }
        } else {
          threadPayload = await requestThread(null);
          resolvedThreadId = threadPayload.thread?.id ?? null;
        }

        setThread(threadPayload);
        setThreadList(threadsPayload);

        setSelectedThreadId(resolvedThreadId);
        setView(resolvedThreadId ? "conversation" : "thread_list");

        const preload: Record<string, CoachThreadResponse> = {};
        if (threadPayload.thread?.id) {
          preload[threadPayload.thread.id] = threadPayload;
        }
        await refreshSignals(threadsPayload.items, preload);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load coach");
      } finally {
        setLoading(false);
        setThreadsLoading(false);
      }
    },
    [refreshSignals, requestThread, requestThreads]
  );

  useEffect(() => {
    if (!active) return;
    void bootstrap(initialThreadId);
  }, [active, bootstrap, initialThreadId]);

  useEffect(() => {
    if (!active) return;
    if (!thread && !optimisticAthleteMessage && busyAction !== "send" && busyAction !== "recap") return;
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [active, busyAction, optimisticAthleteMessage, thread]);

  useEffect(() => {
    if (!scrollTargetId) return;
    const node = messageRefs.current[scrollTargetId];
    if (node) {
      node.scrollIntoView({ behavior: "smooth", block: "center" });
      setScrollTargetId(null);
    }
  }, [scrollTargetId, thread]);

  useEffect(() => {
    if (prefillMessage !== null) {
      const trimmedPrefill = prefillMessage.trim();
      if (trimmedPrefill) {
        setInputValue(prefillMessage);
        setPendingUiContext(prefillContext ?? null);
        setPrefillAnchorMessage(trimmedPrefill);
      } else {
        clearPendingUiContext();
      }
      onPrefillConsumed?.();
    }
  }, [clearPendingUiContext, onPrefillConsumed, prefillContext, prefillMessage]);

  const orderedThreads = useMemo(() => {
    const items = [...(threadList?.items ?? [])];
    items.sort((left, right) => {
      if (left.status !== right.status) {
        return left.status === "active" ? -1 : 1;
      }

      const leftUpdated = Date.parse(left.updated_at);
      const rightUpdated = Date.parse(right.updated_at);
      return rightUpdated - leftUpdated;
    });
    return items;
  }, [threadList]);

  const activeThreads = useMemo(
    () => orderedThreads.filter((item) => item.status === "active"),
    [orderedThreads]
  );
  const archivedThreads = useMemo(
    () => orderedThreads.filter((item) => item.status === "archived"),
    [orderedThreads]
  );
  const visibleArchivedThreads = useMemo(
    () => (showAllArchived ? archivedThreads : archivedThreads.slice(0, 3)),
    [archivedThreads, showAllArchived]
  );
  const selectedThreadListItem = useMemo(
    () => orderedThreads.find((item) => item.id === selectedThreadId) ?? null,
    [orderedThreads, selectedThreadId]
  );

  const quota = thread?.quota ?? null;
  const quotaBlocked = Boolean(quota?.is_limited && (quota.remaining ?? 0) <= 0);
  const selectedThreadStatus = thread?.thread?.status ?? "active";
  const selectedSignals = selectedThreadId ? threadSignals[selectedThreadId] : null;
  const composerDisabled = selectedThreadStatus === "archived" || quotaBlocked || busyAction !== null;
  const listComposerDisabled = quotaBlocked || busyAction !== null;

  const applyTurnResponse = useCallback(
    async (payload: CoachTurnResponse) => {
      const nextThreadPayload = toThreadResponsePayload(payload, thread);
      const nextThreadItems = upsertThreadListItem(threadList?.items ?? [], payload);

      setThread(nextThreadPayload);
      setSelectedThreadId(payload.thread.id);
      setView("conversation");
      setThreadList((previous) =>
        previous
          ? { ...previous, items: upsertThreadListItem(previous.items, payload) }
          : {
              items: nextThreadItems,
              limit: nextThreadItems.length,
              offset: 0,
              has_more: false,
              next_offset: null,
            }
      );

      await refreshSignals(nextThreadItems, { [payload.thread.id]: nextThreadPayload });
    },
    [refreshSignals, thread, threadList]
  );

  const openThread = useCallback(
    async (threadId: string) => {
      if (busyAction !== null) return;

      setLoading(true);
      setError(null);
      setConfirmingArchive(false);
      setOptimisticAthleteMessage(null);
      setSelectedThreadId(threadId);
      setView("conversation");
      trackCoachEvent("coach_thread_switched", {
        thread_id: threadId,
        source: threadSignals[threadId]?.source ?? "unknown",
      });

      try {
        const payload = await requestThread(threadId);
        setThread(payload);
        const signals = threadSignals[threadId];
        if (signals?.hasPendingWork && signals.firstPendingMessageId) {
          setScrollTargetId(signals.firstPendingMessageId);
        } else if (signals?.source === "proactive" && signals.firstCoachMessageId) {
          setScrollTargetId(signals.firstCoachMessageId);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load selected thread");
      } finally {
        setLoading(false);
      }
    },
    [busyAction, requestThread, threadSignals]
  );

  const runAction = useCallback(
    async (action: BusyAction, operation: () => Promise<Response>, proposalId: string | null = null): Promise<ActionResult> => {
      setBusyAction(action);
      setBusyProposalId(proposalId);
      setError(null);

      try {
        const response = await operation();
        if (!response.ok) throw new Error(await readErrorMessage(response));

        const responsePayload = (await response.json().catch(() => null)) as unknown;
        if (isCoachTurnResponse(responsePayload)) {
          await applyTurnResponse(responsePayload);
          return { ok: true, turnPayload: responsePayload };
        }

        await bootstrap(selectedThreadId);
        return { ok: true, turnPayload: null };
      } catch (err) {
        setError(err instanceof Error ? err.message : "Coach action failed");
        return { ok: false, turnPayload: null };
      } finally {
        setBusyAction(null);
        setBusyProposalId(null);
      }
    },
    [applyTurnResponse, bootstrap, selectedThreadId]
  );

  const runStreamingTextAction = useCallback(
    async (
      action: BusyAction,
      payload: {
        thread_id?: string;
        action: "text" | "recap";
        message?: string;
        idempotency_key: string;
        ui_context?: CoachTurnUiContext;
      }
    ): Promise<ActionResult> => {
      setBusyAction(action);
      setBusyProposalId(null);
      setError(null);
      setLiveStatusEvent({ step: "preparing", message: DEFAULT_COACH_STATUS_MESSAGE, iteration: 1 });

      try {
        const response = await fetch("/app/api/coach/turn", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!response.ok) throw new Error(await readErrorMessage(response));

        const contentType = response.headers.get("content-type") ?? "";
        let turnPayload: CoachTurnResponse | null = null;

        if (contentType.includes("text/event-stream")) {
          try {
            turnPayload = await readCoachTurnSse(response, (statusEvent) => {
              setLiveStatusEvent(statusEvent);
            });
          } catch (streamError) {
            if (streamError instanceof CoachStreamServerError) {
              throw streamError;
            }
            await bootstrap(payload.thread_id ?? selectedThreadId ?? null);
            return { ok: true, turnPayload: null };
          }
        } else {
          const responsePayload = (await response.json().catch(() => null)) as unknown;
          if (isCoachTurnResponse(responsePayload)) {
            turnPayload = responsePayload;
          } else {
            await bootstrap(selectedThreadId);
            return { ok: true, turnPayload: null };
          }
        }

        if (!turnPayload) {
          await bootstrap(selectedThreadId);
          return { ok: true, turnPayload: null };
        }

        await applyTurnResponse(turnPayload);
        return { ok: true, turnPayload };
      } catch (err) {
        setError(err instanceof Error ? err.message : "Coach action failed");
        return { ok: false, turnPayload: null };
      } finally {
        setBusyAction(null);
        setBusyProposalId(null);
        setLiveStatusEvent(null);
      }
    },
    [applyTurnResponse, bootstrap, selectedThreadId]
  );

  const startNewTopic = useCallback(() => {
    trackCoachEvent("coach_thread_new_clicked", { previous_thread_id: selectedThreadId });
    setView("conversation");
    setSelectedThreadId(null);
    setError(null);
    setOptimisticAthleteMessage(null);
    clearPendingUiContext();
    setThread((previous) => clearDraftThread(previous));
  }, [clearPendingUiContext, selectedThreadId]);

  const closeSelectedThread = useCallback(async () => {
    if (!selectedThreadId || selectedThreadStatus !== "active") return;

    setBusyAction("archive");
    setError(null);
    try {
      const response = await fetch(`/app/api/coach/thread/${selectedThreadId}/archive`, { method: "POST" });
      if (!response.ok) throw new Error(await readErrorMessage(response));
      trackCoachEvent("coach_thread_archived", { thread_id: selectedThreadId });
      setView("thread_list");
      await bootstrap();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to close thread");
    } finally {
      setBusyAction(null);
    }
  }, [bootstrap, selectedThreadId, selectedThreadStatus]);

  const sendMessage = useCallback(
    async (forceNewThread = false) => {
      const trimmed = input.trim();
      const disabled = forceNewThread
        ? listComposerDisabled || !thread?.can_send_message
        : composerDisabled || !thread?.can_send_message;
      if (!trimmed || disabled) return;

      const targetThreadId = forceNewThread ? null : selectedThreadId;
      const wasNewTopic = targetThreadId === null;
      const nextOptimisticMessage = {
        id: `optimistic-athlete:${Date.now()}`,
        created_at: new Date().toISOString(),
        text: trimmed,
      };

      setInputValue("");
      setOptimisticAthleteMessage(nextOptimisticMessage);

      if (wasNewTopic) {
        setView("conversation");
        setSelectedThreadId(null);
        setConfirmingArchive(false);
        setThread((previous) => clearDraftThread(previous));
      }

      const sent = await runStreamingTextAction("send", {
        thread_id: targetThreadId ?? undefined,
        action: "text",
        message: trimmed,
        idempotency_key: idempotencyKey("coach-send"),
        ui_context: pendingUiContext ?? undefined,
      });

      setOptimisticAthleteMessage(null);

      if (!sent.ok) {
        setInputValue(trimmed);
        return;
      }

      clearPendingUiContext();

      if (wasNewTopic && sent.turnPayload?.thread.id) {
        trackCoachEvent("coach_thread_created_from_message", { thread_id: sent.turnPayload.thread.id });
      }

      const nextThreadId = sent.turnPayload?.thread.id ?? targetThreadId;
      if (nextThreadId) {
        setSelectedThreadId(nextThreadId);
        setView("conversation");
      }
      if (threadIncludesRecap(sent.turnPayload?.projection.messages) || selectedSignals?.source === "weekly_recap") {
        router.refresh();
      }
    },
    [
      clearPendingUiContext,
      composerDisabled,
      input,
      listComposerDisabled,
      pendingUiContext,
      router,
      runStreamingTextAction,
      selectedSignals?.source,
      selectedThreadId,
      thread?.can_send_message,
    ]
  );

  const triggerRecap = useCallback(async () => {
    if (composerDisabled || !thread?.can_trigger_recap) return;

    const triggered = await runStreamingTextAction("recap", {
      thread_id: selectedThreadId ?? undefined,
      action: "recap",
      idempotency_key: idempotencyKey("coach-recap"),
    });
    if (triggered.ok) {
      router.refresh();
    }
  }, [composerDisabled, router, runStreamingTextAction, selectedThreadId, thread?.can_trigger_recap]);

  const acceptProposal = useCallback(
    async (proposalId: string) => {
      if (!proposalId || composerDisabled) return;

      const accepted = await runAction(
        "accept",
        () =>
          fetch("/app/api/coach/turn", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              thread_id: selectedThreadId ?? undefined,
              action: "proposal_accept",
              proposal_id: proposalId,
              idempotency_key: idempotencyKey(`coach-accept:${proposalId}`),
            }),
          }),
        proposalId
      );

      if (accepted.ok) {
        trackCoachEvent("coach_proposal_accepted", { proposal_id: proposalId, thread_id: selectedThreadId });
        router.refresh();
      }
    },
    [composerDisabled, router, runAction, selectedThreadId]
  );

  const rejectProposal = useCallback(
    async (proposalId: string) => {
      const reason = (proposalRejectReasons[proposalId] ?? "").trim();
      if (!reason) {
        setError("Add a rejection reason before rejecting a proposal.");
        return;
      }
      if (!proposalId || composerDisabled) return;

      const rejected = await runAction(
        "reject",
        () =>
          fetch("/app/api/coach/turn", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              thread_id: selectedThreadId ?? undefined,
              action: "proposal_reject",
              proposal_id: proposalId,
              reason,
              idempotency_key: idempotencyKey(`coach-reject:${proposalId}`),
            }),
          }),
        proposalId
      );

      if (rejected.ok) {
        setProposalRejectReasons((previous) => ({ ...previous, [proposalId]: "" }));
        trackCoachEvent("coach_proposal_rejected", { proposal_id: proposalId, thread_id: selectedThreadId });
        router.refresh();
      }
    },
    [composerDisabled, proposalRejectReasons, router, runAction, selectedThreadId]
  );

  const selectedThreadTitle = threadTitle(
    selectedThreadId,
    thread?.thread?.title ?? selectedThreadListItem?.title ?? null,
    selectedSignals ?? undefined
  );
  const isConversationView = view === "conversation";

  const setProposalRejectReason = useCallback((proposalId: string, value: string) => {
    setProposalRejectReasons((previous) => ({ ...previous, [proposalId]: value }));
  }, []);

  return {
    messagesEndRef,
    messageRefs,
    loading,
    threadsLoading,
    thread,
    threadSignals,
    selectedThreadId,
    selectedThreadStatus,
    selectedSignals,
    selectedThreadTitle,
    activeThreads,
    archivedThreads,
    visibleArchivedThreads,
    view,
    setView,
    showAllArchived,
    setShowAllArchived,
    confirmingArchive,
    setConfirmingArchive,
    error,
    setError,
    input,
    setInput,
    busyAction,
    busyProposalId,
    liveStatusEvent,
    optimisticAthleteMessage,
    proposalRejectReasons,
    setProposalRejectReason,
    quota,
    quotaBlocked,
    canSendMessage: Boolean(thread?.can_send_message),
    coachGateMessage: thread?.coach_gate_message ?? null,
    coachGateTarget: thread?.coach_gate_target ?? null,
    threadCanTriggerRecap: Boolean(thread?.can_trigger_recap),
    trainingProviderMessage: thread?.training_provider_message ?? null,
    recapGateTarget: thread?.recap_gate_target ?? null,
    composerDisabled,
    listComposerDisabled,
    isConversationView,
    startNewTopic,
    openThread,
    closeSelectedThread,
    sendMessage,
    triggerRecap,
    acceptProposal,
    rejectProposal,
    trackCoachEvent,
  };
}
