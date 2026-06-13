"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import WhoopConnectButton from "@/components/whoop/whoop-connect-button";
import type { IntegrationsStatus } from "@/lib/types/athlete-context";

type LoadState = "idle" | "loading" | "loaded" | "error";
type ProviderStatus = IntegrationsStatus["strava"] | IntegrationsStatus["whoop"];
type ProviderId = "strava" | "whoop";
type ProviderName = "Strava" | "WHOOP";

function providerHeadline(providerName: ProviderName, status: ProviderStatus | undefined): string {
  if (status?.connection_state === "disabled") return `${providerName} connector is disabled.`;
  if (status?.connection_state === "unconfigured") return `${providerName} connector is not configured.`;
  if (status?.connection_state === "started") return `${providerName} connection is in progress.`;
  if (status?.connection_state === "callback_failed") return `${providerName} connection failed.`;
  if (!status?.linked && status?.ever_connected) return `${providerName} was disconnected.`;
  if (!status?.linked) return `${providerName} is not connected yet.`;
  if (status.operational) return `${providerName} is active.`;
  return `${providerName} needs attention.`;
}

function providerSubtext(providerId: ProviderId, providerName: ProviderName, status: ProviderStatus | undefined): string {
  if (status?.connection_state === "disabled") {
    return `Set ${providerId === "strava" ? "STRAVA_OAUTH_ENABLED" : "WHOOP_OAUTH_ENABLED"}=true when you want to use ${providerName} as an optional data connector.`;
  }
  if (status?.connection_state === "unconfigured") {
    return `Add the local OAuth app credentials and callback URL before connecting ${providerName}.`;
  }
  if (status?.connection_state === "started") {
    return `Complete the provider approval tab, or restart the ${providerName} connection flow if it expired.`;
  }
  if (status?.connection_state === "callback_failed") {
    return status.attention_message ?? `Restart the ${providerName} connection flow from this page.`;
  }
  if (!status?.linked && status?.ever_connected) {
    if (status.last_disconnect_reason === "user_initiated") {
      return `Reconnect ${providerName} anytime to resume ${providerId === "strava" ? "activity import" : "readiness import"}.`;
    }
    return `Reconnect ${providerName} to restore ${providerId === "strava" ? "activity import" : "readiness import"}.`;
  }
  if (!status?.linked) {
    return providerId === "strava"
      ? "Connect Strava to import activity history and execution context."
      : "Connect WHOOP to import recovery and readiness context.";
  }
  if (status.operational) {
    return providerId === "strava" ? "Imported from Strava." : "Imported from WHOOP.";
  }
  return status.attention_message ?? `${providerName} is linked, but syncing is not operational right now.`;
}

function providerStatusTone(status: ProviderStatus | undefined): string {
  if (
    status?.state === "attention_needed" ||
    status?.connection_state === "unconfigured" ||
    status?.connection_state === "started" ||
    status?.connection_state === "callback_failed" ||
    (status?.ever_connected && !status?.linked)
  ) {
    return "text-amber-400";
  }
  return "text-[var(--text-muted)]";
}

function ConnectLinkButton({
  enabled,
  href,
  label,
  disabledTitle,
}: {
  enabled: boolean;
  href: string;
  label: string;
  disabledTitle: string;
}) {
  const className =
    "inline-flex items-center rounded-md bg-[#fc4c02] px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-[#e34502] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#fc4c02]";
  if (!enabled) {
    return (
      <button className={`${className} cursor-not-allowed opacity-60 hover:bg-[#fc4c02]`} disabled type="button" title={disabledTitle}>
        {label}
      </button>
    );
  }
  return (
    <a className={className} href={href}>
      {label}
    </a>
  );
}

async function fetchIntegrationsStatus() {
  const res = await fetch("/app/api/integrations/status", { cache: "no-store" });
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as IntegrationsStatus;
}

export default function SettingsPage() {
  const router = useRouter();

  const stravaOauthEnabled = (process.env.NEXT_PUBLIC_STRAVA_OAUTH_ENABLED ?? "false") === "true";
  const whoopOauthEnabled = (process.env.NEXT_PUBLIC_WHOOP_OAUTH_ENABLED ?? "false") === "true";
  const localDataDeleteAllowed = (process.env.NEXT_PUBLIC_ALLOW_LOCAL_DATA_DELETE ?? "false") === "true";

  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [disconnecting, setDisconnecting] = useState<ProviderId | null>(null);
  const [integrationsState, setIntegrationsState] = useState<LoadState>("idle");
  const [integrationsError, setIntegrationsError] = useState<string | null>(null);
  const [integrations, setIntegrations] = useState<IntegrationsStatus | null>(null);

  const canDisconnectStrava = Boolean(integrations?.strava.linked);
  const canDisconnectWhoop = Boolean(integrations?.whoop.linked);
  const canStartStrava =
    stravaOauthEnabled && integrations?.strava.oauth_enabled !== false && integrations?.strava.configured !== false;
  const canStartWhoop =
    whoopOauthEnabled && integrations?.whoop.oauth_enabled !== false && integrations?.whoop.configured !== false;

  async function refreshIntegrations() {
    setIntegrationsState("loading");
    setIntegrationsError(null);
    try {
      const data = await fetchIntegrationsStatus();
      setIntegrations(data);
      setIntegrationsState("loaded");
      return data;
    } catch (err) {
      setIntegrationsState("error");
      setIntegrationsError(err instanceof Error ? err.message : "Failed to load integration status.");
      return null;
    }
  }

  useEffect(() => {
    const { searchParams } = new URL(window.location.href);
    const connected = searchParams.get("connected");
    const oauthError = searchParams.get("oauth_error");

    if (connected === "strava") {
      setActionMessage("Strava connected. Activity sync is active.");
      router.replace("/app/settings");
      router.refresh();
      return;
    }
    if (connected === "whoop") {
      setActionMessage("WHOOP connected. Readiness sync is active.");
      router.replace("/app/settings");
      router.refresh();
      return;
    }
    if (oauthError === "strava") {
      setActionMessage("Strava connection failed. Please try again.");
      router.replace("/app/settings");
      return;
    }
    if (oauthError === "whoop") {
      setActionMessage("WHOOP connection failed. Please try again.");
      router.replace("/app/settings");
    }
  }, [router]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      setIntegrationsState("loading");
      setIntegrationsError(null);

      const integrationsResult = await Promise.allSettled([fetchIntegrationsStatus()]);
      if (cancelled) return;

      const [result] = integrationsResult;
      if (result.status === "fulfilled") {
        setIntegrations(result.value);
        setIntegrationsState("loaded");
      } else {
        setIntegrationsState("error");
        setIntegrationsError(
          result.reason instanceof Error
            ? result.reason.message
            : "Failed to load integration status.",
        );
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function onDisconnect(provider: ProviderId) {
    setActionMessage(null);
    setDisconnecting(provider);
    try {
      const res = await fetch(`/app/api/account/${provider}/disconnect`, { method: "POST" });
      if (!res.ok) throw new Error(await res.text());
      setActionMessage(
        provider === "strava"
          ? "Strava disconnected. Activity sync is stopped."
          : "WHOOP disconnected. Readiness sync is stopped.",
      );
      await refreshIntegrations();
      router.refresh();
    } catch (err) {
      setActionMessage(err instanceof Error ? err.message : "Failed to disconnect.");
    } finally {
      setDisconnecting(null);
    }
  }

  async function onDeleteAccount() {
    setActionMessage(null);
    if (!localDataDeleteAllowed) {
      setActionMessage(
        "Local data reset is disabled by default. Back up your DB, then enable ALLOW_LOCAL_DATA_DELETE only if you really want to delete everything.",
      );
      return;
    }
    const ok = window.confirm(
      "Reset local app data permanently? This removes your profile, planning history, coaching outputs, and stored connection credentials from this app."
    );
    if (!ok) return;
    try {
      const res = await fetch("/app/api/account", { method: "DELETE" });
      const payload = await res.json().catch(() => null);
      if (!res.ok) {
        const detail = payload?.detail ?? payload;
        if (res.status === 502 && detail?.code === "auth_delete_failed") {
          window.location.assign(detail.redirect_path ?? "/delete?status=deleted&auth_cleanup=pending");
          return;
        }
        throw new Error(detail?.message ?? detail?.detail ?? JSON.stringify(payload));
      }
      window.location.assign(payload?.redirect_path ?? "/delete?status=deleted");
    } catch (err) {
      setActionMessage(err instanceof Error ? err.message : "Failed to delete this account.");
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

      <div className="space-y-2 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4">
        <div className="font-medium">Connected coaching sources</div>
        <p className="text-sm text-[var(--text-secondary)]">
          Strava brings activity history, WHOOP brings readiness context, and the local coach uses whichever evidence is
          actually available.
        </p>
        {integrationsState === "error" ? <p className="text-sm text-red-400">{integrationsError}</p> : null}
        {actionMessage ? <p className="text-sm text-[var(--text-secondary)]">{actionMessage}</p> : null}
      </div>

      <div className="space-y-2 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4">
        <div className="font-medium">Strava source</div>
        <p className="text-sm text-[var(--text-secondary)]">{providerHeadline("Strava", integrations?.strava)}</p>
        <p className={`text-xs ${providerStatusTone(integrations?.strava)}`}>
          {providerSubtext("strava", "Strava", integrations?.strava)}
        </p>
        <div className="flex flex-wrap gap-2">
          {integrations?.strava.operational ? (
            <button
              className="rounded-md border px-4 py-2 disabled:opacity-60"
              type="button"
              onClick={() => onDisconnect("strava")}
              disabled={!canDisconnectStrava || disconnecting === "strava"}
              aria-disabled={!canDisconnectStrava || disconnecting === "strava"}
            >
              {disconnecting === "strava" ? "Disconnecting..." : "Disconnect Strava"}
            </button>
          ) : (
            <>
              <ConnectLinkButton
                enabled={canStartStrava}
                href="/app/api/oauth/strava/start"
                label="Connect Strava"
                disabledTitle="Strava OAuth is disabled or not configured."
              />
              {integrations?.strava.linked ? (
                <button
                  className="rounded-md border px-4 py-2 disabled:opacity-60"
                  type="button"
                  onClick={() => onDisconnect("strava")}
                  disabled={!canDisconnectStrava || disconnecting === "strava"}
                  aria-disabled={!canDisconnectStrava || disconnecting === "strava"}
                >
                  {disconnecting === "strava" ? "Disconnecting..." : "Disconnect Strava"}
                </button>
              ) : null}
            </>
          )}
        </div>
        {integrations?.strava.linked && integrations?.strava.scope ? (
          <p className="text-xs text-[var(--text-muted)]">Scopes: {integrations.strava.scope}</p>
        ) : null}
        {integrations?.strava.linked && integrations?.strava.athlete_id ? (
          <p className="text-xs text-[var(--text-muted)]">Athlete ID: {integrations.strava.athlete_id}</p>
        ) : null}
        <p className="text-xs text-[var(--text-muted)]">
          Setup docs live in <code>docs/local-first/connect-strava.md</code>.
        </p>
      </div>

      <div className="space-y-2 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4">
        <div className="font-medium">WHOOP source</div>
        <p className="text-sm text-[var(--text-secondary)]">{providerHeadline("WHOOP", integrations?.whoop)}</p>
        <p className={`text-xs ${providerStatusTone(integrations?.whoop)}`}>
          {providerSubtext("whoop", "WHOOP", integrations?.whoop)}
        </p>
        <div className="flex flex-wrap gap-2">
          {integrations?.whoop.operational ? (
            <button
              className="rounded-md border px-4 py-2 disabled:opacity-60"
              type="button"
              onClick={() => onDisconnect("whoop")}
              disabled={!canDisconnectWhoop || disconnecting === "whoop"}
              aria-disabled={!canDisconnectWhoop || disconnecting === "whoop"}
            >
              {disconnecting === "whoop" ? "Disconnecting..." : "Disconnect WHOOP"}
            </button>
          ) : (
            <>
              <WhoopConnectButton enabled={canStartWhoop} href="/app/api/oauth/whoop/start" />
              {integrations?.whoop.linked ? (
                <button
                  className="rounded-md border px-4 py-2 disabled:opacity-60"
                  type="button"
                  onClick={() => onDisconnect("whoop")}
                  disabled={!canDisconnectWhoop || disconnecting === "whoop"}
                  aria-disabled={!canDisconnectWhoop || disconnecting === "whoop"}
                >
                  {disconnecting === "whoop" ? "Disconnecting..." : "Disconnect WHOOP"}
                </button>
              ) : null}
            </>
          )}
        </div>
        {integrations?.whoop.linked && integrations?.whoop.scope ? (
          <p className="text-xs text-[var(--text-muted)]">Scopes: {integrations.whoop.scope}</p>
        ) : null}
        <p className="text-xs text-[var(--text-muted)]">
          Setup docs live in <code>docs/local-first/connect-whoop.md</code>.
        </p>
      </div>

      <div className="space-y-3 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4">
        <div className="font-medium">Local privacy reset</div>
        <p className="text-sm text-[var(--text-secondary)]">
          In-app reset removes your local profile, planning history, coaching outputs, jobs, and stored connector
          credentials from this app. It is disabled by default in local mode to protect existing plans.
        </p>
        <div className="flex flex-col gap-2 sm:flex-row">
          <button
            className="rounded-md border px-4 py-2 text-red-400 disabled:opacity-60"
            type="button"
            onClick={onDeleteAccount}
            disabled={!localDataDeleteAllowed}
            title={
              localDataDeleteAllowed
                ? "Delete local account data"
                : "Set ALLOW_LOCAL_DATA_DELETE=true and NEXT_PUBLIC_ALLOW_LOCAL_DATA_DELETE=true to enable this."
            }
          >
            Reset local data
          </button>
        </div>
        {!localDataDeleteAllowed ? (
          <p className="text-xs text-[var(--text-muted)]">
            To enable this destructive action, set both server and web reset flags after backing up your local database.
          </p>
        ) : null}
      </div>
    </div>
  );
}
