import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";

import { renderToStaticMarkup } from "react-dom/server";

import { ProposalCard } from "@/components/coach-chat/coach-inbox-parts";
import type { WeeklyPlanV3 } from "@/components/plan-viewer/types";
import SeasonPlanViewV3 from "@/components/plan-viewer/versioned/season-plan-view-v3";
import WeeklyPlanViewV3 from "@/components/plan-viewer/versioned/weekly-plan-view-v3";
import TodayMission from "@/components/dashboard/today-mission";
import { DEMO_SEASON_PLAN_BY_PERSONA as SEASON_V3 } from "@/lib/demo/fixtures/v3/season";
import { DEMO_WEEKLY_PLAN_BY_PERSONA as WEEKLY_V3 } from "@/lib/demo/fixtures/v3/weekly";
import { athleteLocalYYYYMMDD } from "@/lib/date-utils";
import { resolveSchemaVersion } from "@/lib/plan-version";

const seasonV3Html = renderToStaticMarkup(<SeasonPlanViewV3 seasonPlan={SEASON_V3["hybrid-operator"]} />);
assert.match(seasonV3Html, /Season strategy · v3/);
assert.match(seasonV3Html, /Season progression/);
assert.match(seasonV3Html, /href="https:\/\/example.com\/effort"/);
assert.match(seasonV3Html, /<ul/);

const weeklyV3Html = renderToStaticMarkup(<WeeklyPlanViewV3 weeklyPlan={WEEKLY_V3["hybrid-operator"]} theme="dark" />);
assert.match(weeklyV3Html, /28-day execution · v3/);
assert.match(weeklyV3Html, /Your next 28 days/);
assert.match(weeklyV3Html, /Select a day for details/);
assert.match(weeklyV3Html, /Coach rationale/);
assert.match(weeklyV3Html, /Controlled progression/);
assert.match(weeklyV3Html, /Fuel the longer days/);
assert.doesNotMatch(weeklyV3Html, /content_html|<script/i);

const firstWeek = WEEKLY_V3["hybrid-operator"].weeks[0];
const athleteNowIso = `${firstWeek.days[1].date}T00:30:00+14:00`;
const athleteLocalHtml = renderToStaticMarkup(
  <WeeklyPlanViewV3 weeklyPlan={WEEKLY_V3["hybrid-operator"]} theme="dark" nowIso={athleteNowIso} />,
);
assert.equal(athleteLocalYYYYMMDD(athleteNowIso), firstWeek.days[1].date);
assert.match(
  athleteLocalHtml,
  new RegExp(`aria-pressed="true"[^>]*>[\\s\\S]*?${firstWeek.days[1].sessions[0]?.title ?? "Recovery day"}`),
  "the athlete-local date selects today's calendar card without UTC conversion",
);

const todayMissionHtml = renderToStaticMarkup(
  <TodayMission weeklyPlan={WEEKLY_V3["hybrid-operator"]} nowIso={`${firstWeek.days[0].date}T08:00:00-07:00`} />,
);
assert.match(todayMissionHtml, /Show prescription/);
assert.match(todayMissionHtml, /Open full 28-day plan/);
assert.doesNotMatch(todayMissionHtml, /No specific structured workflow/);

const planViewerSource = readFileSync(
  path.join(process.cwd(), "src/components/plan-viewer/plan-viewer.tsx"),
  "utf8",
);
assert.match(
  planViewerSource,
  /artifact != null && artifact\.schema_version !== 1/,
  "PlanViewer must route unknown non-v1 artifacts through strict versioned dispatch",
);
const planRendererSource = readFileSync(
  path.join(process.cwd(), "src/components/plan-viewer/versioned/plan-renderer.tsx"),
  "utf8",
);
assert.match(planRendererSource, /<UnsupportedSchema kind="analysis"/);
assert.match(planRendererSource, /<UnsupportedSchema kind="season"/);
assert.match(planRendererSource, /<UnsupportedSchema kind="weekly"/);

const proposalBefore = WEEKLY_V3["hybrid-operator"];
const proposalAfter = structuredClone(proposalBefore) as WeeklyPlanV3;
proposalAfter.weeks[0].days[0].focus_type = "recovery";
proposalAfter.weeks[0].days[0].intensity = "low";
const proposalHtml = renderToStaticMarkup(
  <ProposalCard
    proposalId="proposal-v3"
    ops={[{ op: "update_day_fields_v3", day_id: proposalAfter.weeks[0].days[0].day_id, focus_type: "recovery", intensity: "low" }]}
    status="pending"
    beforePlan={proposalBefore}
    afterPlan={proposalAfter}
    busyAction={null}
    disabled={false}
    rejectReason=""
    onRejectReasonChange={() => undefined}
    onAccept={() => undefined}
    onReject={() => undefined}
  />,
);
assert.match(proposalHtml, /Visual before vs after/);
assert.match(proposalHtml, /Update day fields/);
assert.match(proposalHtml, /Before/);
assert.match(proposalHtml, /After/);
assert.doesNotMatch(proposalHtml, /Apply custom adjustment/);

assert.equal(resolveSchemaVersion("analysis", 1), 1);
assert.equal(resolveSchemaVersion("analysis", 3), null);
assert.equal(resolveSchemaVersion("season", 3), 3);
assert.equal(resolveSchemaVersion("weekly", 3), 3);
assert.equal(resolveSchemaVersion("weekly", 99), null);

console.log("Schema v3 plans render rich semantic components with strict version dispatch.");
