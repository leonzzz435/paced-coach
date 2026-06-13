import assert from "node:assert/strict";

import {
  buildCoachSurfaceFromAnalysis,
  buildCoachSurfaceFromDailySyncResult,
  buildCoachSurfaceFromWeeklyRecap,
  resolveDailySyncVerdictPreview,
  resolveRecapGuidancePreview,
  resolveRecapSummaryPreview,
  resolveWeeklyRecapPendingAction,
} from "@/lib/types/dashboard";
import type { DashboardAnalysisState, DashboardDailySyncState, DashboardStateResponse, DailyRunResponse } from "@/lib/types/dashboard";

const baseDailySyncState: DashboardDailySyncState = {
  visible: true,
  status: "completed",
  run_id: "run-1",
  verdict_preview: "Green light today. The 3-5 day trend says you have bounced back well from the dip on Saturday: HRV has risen from 85 to 126 to 141, resting HR is down to 39...",
  sources_used: ["strava", "whoop"],
  proposal_id: null,
  thread_id: null,
  error_message: null,
  can_run: true,
  attention_message: null,
  gate_target: null,
};

const dayOverride: DashboardStateResponse["today_mission"]["day_override"] = {
  day_id: "2026-03-09",
  date: "2026-03-09",
  blocks: [
    {
      type: "html",
      key: "focus-verdict",
      variant: "callout",
      content_html:
        "<div><strong>Green light today.</strong> The 3-5 day trend says you have bounced back well from the dip on Saturday: HRV has risen from 85 to 126 to 141, resting HR is down to 39, and both Strava and WHOOP show strong recovery this morning.</div>",
    },
  ],
};

assert.equal(
  resolveDailySyncVerdictPreview(baseDailySyncState, dayOverride),
  "Green light today. The 3-5 day trend says you have bounced back well from the dip on Saturday: HRV has risen from 85 to 126 to 141, resting HR is down to 39, and both Strava and WHOOP show strong recovery this morning.",
);

assert.equal(resolveDailySyncVerdictPreview(baseDailySyncState, null), baseDailySyncState.verdict_preview);

assert.equal(
  resolveRecapSummaryPreview({
    run_id: "recap-1",
    user_id: "user-1",
    week_anchor_utc: "2026-03-15T23:00:00+00:00",
    status: "completed",
    trigger_source: "manual",
    created_at: "2026-03-15T18:00:00+00:00",
    updated_at: "2026-03-15T18:01:00+00:00",
    narrative: {
      this_week_blocks: [
        {
          type: "html",
          key: "load-summary",
          variant: "callout",
          title: "High compliance, but load rose faster than ideal",
          content_html: "<p><strong>This week:</strong> strong compliance, but load rose fast.</p>",
        },
      ],
      looking_ahead_blocks: [],
    },
  }),
  "High compliance, but load rose faster than ideal",
);

assert.equal(
  resolveRecapGuidancePreview({
    run_id: "recap-1",
    user_id: "user-1",
    week_anchor_utc: "2026-03-15T23:00:00+00:00",
    status: "completed",
    trigger_source: "manual",
    created_at: "2026-03-15T18:00:00+00:00",
    updated_at: "2026-03-15T18:01:00+00:00",
    narrative: {
      this_week_blocks: [
        {
          type: "html",
          key: "load-summary",
          variant: "callout",
          title: "High compliance, but load rose faster than ideal",
          content_html: "<p><strong>This week:</strong> strong compliance, but load rose fast.</p>",
        },
      ],
      looking_ahead_blocks: [
        {
          type: "html",
          key: "next-week",
          variant: "callout",
          title: "Absorb the work before pushing again",
          content_html: "<p>Keep Tuesday controlled and do not chase extra volume.</p>",
        },
      ],
    },
  }),
  "Absorb the work before pushing again",
);

assert.equal(
  resolveWeeklyRecapPendingAction({
    proposalId: "proposal-1",
    followUpQuestion: "How did the long run feel?",
    athleteResponse: null,
  }),
  "follow_up_and_proposal",
);
assert.equal(
  resolveWeeklyRecapPendingAction({
    proposalId: null,
    followUpQuestion: "How did the long run feel?",
    athleteResponse: "Felt great",
  }),
  "none",
);

const analysisState: DashboardAnalysisState = {
  analysis: {
    type: "analysis",
    analysis_id: "analysis-1",
    schema_version: 1,
    version: 1,
    athlete_name: "Test Athlete",
    coach_action: "Protect recovery today.",
    headline_brief: "Your load is stable, but sleep still needs protecting before the next push.",
    dashboard_kpis: [],
    kpis: [],
    sections: [],
  },
  version: 1,
  updated_at: "2026-03-15T08:00:00+00:00",
  source_job_id: "analysis-job",
};

assert.deepEqual(buildCoachSurfaceFromAnalysis(analysisState), {
  source: "analysis",
  scope: "training_block",
  primary_label: "Block Focus",
  primary_text: "Protect recovery today.",
  secondary_text: "Your load is stable, but sleep still needs protecting before the next push.",
  updated_at: "2026-03-15T08:00:00+00:00",
});

const dailyRunResponse: DailyRunResponse = {
  status: "success",
  run_id: "daily-1",
  sources_used: ["strava", "whoop"],
  proposal_id: null,
  thread_id: null,
  preview_weekly_plan: null,
  narrative: {
    dashboard_kpis: [],
    today_focus_blocks: [
      {
        content_html: "<p><strong>Protect today.</strong> Keep the set controlled.</p>",
      },
    ],
    optional_proposal_ops: [],
  },
  today_override: null,
};

assert.deepEqual(buildCoachSurfaceFromDailySyncResult(dailyRunResponse, "2026-03-15T09:00:00+00:00"), {
  source: "daily_sync",
  scope: "today",
  primary_label: "Today's Action",
  primary_text: "Protect today.",
  secondary_text: "Keep the set controlled.",
  updated_at: "2026-03-15T09:00:00+00:00",
});

assert.deepEqual(
  buildCoachSurfaceFromWeeklyRecap({
    run_id: "recap-1",
    user_id: "user-1",
    week_anchor_utc: "2026-03-15T23:00:00+00:00",
    status: "completed",
    trigger_source: "manual",
    created_at: "2026-03-15T18:00:00+00:00",
    updated_at: "2026-03-15T18:01:00+00:00",
    narrative: {
      this_week_blocks: [
        {
          type: "html",
          key: "load-summary",
          variant: "callout",
          title: "High compliance, but load rose faster than ideal",
          content_html: "<p><strong>This week:</strong> strong compliance, but load rose fast.</p>",
        },
      ],
      looking_ahead_blocks: [
        {
          type: "html",
          key: "next-week",
          variant: "callout",
          title: "Absorb the work before pushing again",
          content_html: "<p>Keep Tuesday controlled and do not chase extra volume.</p>",
        },
      ],
    },
  }),
  {
    source: "weekly_recap",
    scope: "this_week",
    primary_label: "This Week's Priority",
    primary_text: "High compliance, but load rose faster than ideal",
    secondary_text: "Absorb the work before pushing again",
    updated_at: "2026-03-15T18:01:00+00:00",
  },
);

console.log("Daily sync preview resolution checks passed.");
