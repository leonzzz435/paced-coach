"use client";

import Link from "next/link";
import { useState } from "react";

export default function SettingsPage() {
  const localDataDeleteAllowed = (process.env.NEXT_PUBLIC_ALLOW_LOCAL_DATA_DELETE ?? "false") === "true";
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  async function onDeleteAccount() {
    setActionMessage(null);
    if (!localDataDeleteAllowed) {
      setActionMessage(
        "Local data reset is disabled by default. Back up your database, then enable it only when you want to remove everything.",
      );
      return;
    }

    const confirmed = window.confirm(
      "Reset local app data permanently? This removes your profile, plans, coaching outputs, and job history from this app.",
    );
    if (!confirmed) return;

    try {
      const response = await fetch("/app/api/account", { method: "DELETE" });
      const payload = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(payload?.detail?.message ?? payload?.detail ?? payload?.message ?? "Local data reset failed.");
      }
      window.location.assign(payload?.redirect_path ?? "/delete?status=deleted");
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : "Local data reset failed.");
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Settings</h1>
        <Link className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]" href="/app">
          Back
        </Link>
      </div>

      <section className="space-y-2 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4">
        <div className="font-medium">Provider-free coaching</div>
        <p className="text-sm leading-6 text-[var(--text-secondary)]">
          This release coaches from the profile, goals, races, availability, constraints, and notes you choose to save.
          No wearable account or external training-data connection is required or available.
        </p>
      </section>

      <section className="space-y-3 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4">
        <div className="font-medium">Local privacy reset</div>
        <p className="text-sm leading-6 text-[var(--text-secondary)]">
          In-app reset removes the local profile, planning history, coaching outputs, and jobs. It is disabled by default
          to protect existing plans.
        </p>
        {actionMessage ? <p className="text-sm text-[var(--text-secondary)]">{actionMessage}</p> : null}
        <button
          className="rounded-md border px-4 py-2 text-red-400 disabled:opacity-60"
          type="button"
          onClick={onDeleteAccount}
          disabled={!localDataDeleteAllowed}
          title={
            localDataDeleteAllowed
              ? "Delete local app data"
              : "Set ALLOW_LOCAL_DATA_DELETE=true and NEXT_PUBLIC_ALLOW_LOCAL_DATA_DELETE=true to enable this."
          }
        >
          Reset local data
        </button>
        {!localDataDeleteAllowed ? (
          <p className="text-xs text-[var(--text-muted)]">
            Back up the local database before enabling both server and web reset flags.
          </p>
        ) : null}
      </section>
    </div>
  );
}
