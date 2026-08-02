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
