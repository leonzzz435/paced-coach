"use client";

import { useCallback, useSyncExternalStore } from "react";

const STORAGE_PREFIX = "paced_checkboxes_";
const EMPTY_STATE: Record<string, boolean> = Object.freeze({});

function getStoreKey(planId: string) {
    return `${STORAGE_PREFIX}${planId}`;
}

function loadState(planId: string): Record<string, boolean> {
    if (typeof window === "undefined") return EMPTY_STATE;
    try {
        const raw = localStorage.getItem(getStoreKey(planId));
        return raw ? (JSON.parse(raw) as Record<string, boolean>) : EMPTY_STATE;
    } catch {
        return EMPTY_STATE;
    }
}

function saveState(planId: string, state: Record<string, boolean>) {
    try {
        localStorage.setItem(getStoreKey(planId), JSON.stringify(state));
    } catch {
        // quota exceeded — degrade silently
    }
}

// Minimal external store so React re-renders on changes.
let listeners: Array<() => void> = [];
let snapshot: Record<string, Record<string, boolean>> = {};

function subscribe(cb: () => void) {
    listeners.push(cb);
    return () => {
        listeners = listeners.filter((l) => l !== cb);
    };
}

function emitChange() {
    for (const l of listeners) l();
}

function getSnapshot(planId: string): Record<string, boolean> {
    if (!snapshot[planId]) {
        snapshot[planId] = loadState(planId);
    }
    return snapshot[planId];
}

export function useCheckboxState(planId: string) {
    const state = useSyncExternalStore(
        subscribe,
        () => getSnapshot(planId),
        () => EMPTY_STATE
    );

    const isChecked = useCallback(
        (checkboxId: string): boolean => !!state[checkboxId],
        [state]
    );

    const toggle = useCallback(
        (checkboxId: string) => {
            const current = getSnapshot(planId);
            const next = { ...current, [checkboxId]: !current[checkboxId] };
            snapshot = { ...snapshot, [planId]: next };
            saveState(planId, next);
            emitChange();
        },
        [planId]
    );

    return { isChecked, toggle };
}
