export type ProfilePayload = {
  physiology?: {
    ftp?: number | null;
    lthr?: number | null;
    max_hr?: number | null;
    custom_zones?: string | null;
  } | null;
  preferences?: {
    sports?: string[] | null;
    excluded_sports?: string[] | null;
    injuries_limitations?: string | null;
    timezone?: string | null;
  } | null;
  availability?: {
    days_per_week?: number | null;
    time_windows?: string | null;
    upcoming_travel?: string | null;
  } | null;
  goals?: {
    primary_goal?: string | null;
    notes?: string | null;
  } | null;
};

export type AthleteProfileResponse = {
  user_id: string;
  profile: ProfilePayload;
  updated_at?: string | null;
};

export type Competition = {
  id: string;
  name: string;
  date?: string | null;
  date_text?: string | null;
  race_type?: string | null;
  priority?: string | null;
  target_time?: string | null;
  notes?: string | null;
};

export type CredentialsStatus = {
  stored: boolean;
  email_hint?: string | null;
  mode?: string | null;
};

export type IntegrationHealthState = "connected" | "attention_needed" | "disconnected";
export type ProviderConnectionState =
  | "disabled"
  | "unconfigured"
  | "disconnected"
  | "started"
  | "callback_failed"
  | "token_missing"
  | "token_expired"
  | "partial_permissions"
  | "stale"
  | "syncing"
  | "connected_no_data"
  | "connected_usable";

type BaseIntegrationStatus = {
  linked: boolean;
  ever_connected: boolean;
  connected: boolean;
  operational: boolean;
  state: IntegrationHealthState;
  connection_state: ProviderConnectionState;
  configured: boolean;
  oauth_enabled: boolean;
  attention_message?: string | null;
  first_connected_at?: string | null;
  last_connected_at?: string | null;
  last_disconnected_at?: string | null;
  last_disconnect_reason?: string | null;
};

export type StravaIntegrationStatus = {
  athlete_id?: number | null;
  expires_at?: string | null;
  scope?: string | null;
} & BaseIntegrationStatus;

export type WhoopIntegrationStatus = {
  whoop_user_id?: number | null;
  expires_at?: string | null;
  scope?: string | null;
} & BaseIntegrationStatus;

export type IntegrationsStatus = {
  strava: StravaIntegrationStatus;
  whoop: WhoopIntegrationStatus;
};

const TRAINING_PROVIDER_LABELS = {
  strava: "Strava",
  whoop: "WHOOP",
} as const;

type TrainingProviderName = keyof typeof TRAINING_PROVIDER_LABELS;

function collectProviderNames(
  integrations: IntegrationsStatus | null,
  predicate: (status: BaseIntegrationStatus) => boolean,
): string[] {
  if (!integrations) return [];
  const names: string[] = [];
  for (const providerName of Object.keys(TRAINING_PROVIDER_LABELS) as TrainingProviderName[]) {
    if (predicate(integrations[providerName])) {
      names.push(TRAINING_PROVIDER_LABELS[providerName]);
    }
  }
  return names;
}

function joinProviderNames(names: string[]): string {
  return names.join(" + ");
}

export function getOperationalTrainingProviderNames(integrations: IntegrationsStatus | null): string[] {
  return collectProviderNames(integrations, (status) => status.operational);
}

export function getAttentionTrainingProviderNames(integrations: IntegrationsStatus | null): string[] {
  return collectProviderNames(integrations, (status) => status.state === "attention_needed");
}

export function hasOperationalTrainingProvider(integrations: IntegrationsStatus | null): boolean {
  return getOperationalTrainingProviderNames(integrations).length > 0;
}

export function hasLinkedTrainingProvider(integrations: IntegrationsStatus | null): boolean {
  return collectProviderNames(integrations, (status) => status.linked).length > 0;
}

export function hasEverConnectedTrainingProvider(integrations: IntegrationsStatus | null): boolean {
  return collectProviderNames(integrations, (status) => status.ever_connected).length > 0;
}

export function getPreviouslyConnectedProviderNames(integrations: IntegrationsStatus | null): string[] {
  return collectProviderNames(integrations, (status) => status.ever_connected && !status.linked);
}

export function formatTrainingProviderBadge(integrations: IntegrationsStatus | null): string {
  if (!integrations) return "Provider status unavailable";

  const operationalProviders = getOperationalTrainingProviderNames(integrations);
  const attentionProviders = getAttentionTrainingProviderNames(integrations);
  const disconnectedProviders = getPreviouslyConnectedProviderNames(integrations);

  if (operationalProviders.length > 0 && attentionProviders.length > 0) {
    return `${joinProviderNames(operationalProviders)} active · ${joinProviderNames(attentionProviders)} needs attention`;
  }
  if (operationalProviders.length > 0 && disconnectedProviders.length > 0) {
    return `${joinProviderNames(operationalProviders)} active · ${joinProviderNames(disconnectedProviders)} disconnected`;
  }
  if (operationalProviders.length > 0) {
    return `${joinProviderNames(operationalProviders)} active`;
  }
  if (attentionProviders.length > 0) {
    return `${joinProviderNames(attentionProviders)} needs attention`;
  }
  if (disconnectedProviders.length > 0) {
    return `${joinProviderNames(disconnectedProviders)} disconnected`;
  }
  return "No training source connected";
}

export function profileCompleteness(profile: ProfilePayload | null): number {
  if (!profile) return 0;
  const checks = [
    Boolean(profile.physiology?.ftp || profile.physiology?.lthr || profile.physiology?.max_hr),
    Boolean((profile.preferences?.sports ?? []).length > 0),
    Boolean(profile.availability?.days_per_week),
    Boolean((profile.availability?.time_windows ?? "").trim()),
    Boolean((profile.goals?.primary_goal ?? "").trim()),
  ];
  return Math.round((checks.filter(Boolean).length / checks.length) * 100);
}

export function formatProfileCompletenessBadge(profile: ProfilePayload | null, options: { available: boolean }): string {
  const { available } = options;
  if (!available) return "Profile status unavailable";
  return `Profile ${profileCompleteness(profile)}% complete`;
}

export function formatCompetitionsBadge(count: number | null, options: { available: boolean }): string {
  const { available } = options;
  if (!available) return "Competitions unavailable";
  return `${count ?? 0} competitions saved`;
}

export function formatDateHuman(dateString: string): string {
  const parsed = new Date(dateString + "T00:00:00");
  if (Number.isNaN(parsed.getTime())) return dateString;
  return parsed.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export function daysUntil(dateString: string): number | null {
  const parsed = new Date(dateString + "T00:00:00");
  if (Number.isNaN(parsed.getTime())) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  parsed.setHours(0, 0, 0, 0);
  return Math.ceil((parsed.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
}
