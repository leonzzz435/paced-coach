export type CoachQuota = {
  week_anchor_utc: string;
  used: number;
  limit: number | null;
  remaining: number | null;
  is_limited: boolean;
};
