import assert from "node:assert/strict";

import { renderToStaticMarkup } from "react-dom/server";

import { RecapMessage } from "@/components/coach-chat/coach-inbox-parts";
import type { CoachThreadMessage } from "@/lib/types/coach";
import { resolveRecapGuidancePreview, resolveRecapSummaryPreview } from "@/lib/types/dashboard";
import type { WeeklyRecapResponse } from "@/lib/types/recap";

const recap: WeeklyRecapResponse = {
  run_id: "legacy-recap",
  user_id: "local-owner",
  week_anchor_utc: "2026-07-27T00:00:00Z",
  status: "completed",
  trigger_source: "historical",
  created_at: "2026-08-01T00:00:00Z",
  updated_at: "2026-08-01T00:00:00Z",
  narrative: {
    this_week_blocks: [
      {
        type: "html",
        key: "legacy-summary",
        variant: "callout",
        title: "Consistency won the week",
        content_html: '<script>alert("xss")</script><p>Three calm sessions built momentum.</p>',
      },
    ],
    looking_ahead_blocks: [
      {
        type: "html",
        key: "legacy-guidance",
        variant: "workout",
        content_html: '<p>Keep Tuesday deliberately easy before Thursday strength.</p><img src="x" onerror="alert(1)">',
      },
    ],
  },
};

assert.equal(resolveRecapSummaryPreview(recap), "Consistency won the week");
assert.equal(
  resolveRecapGuidancePreview(recap),
  "Keep Tuesday deliberately easy before Thursday strength.",
);

const message: Extract<CoachThreadMessage, { kind: "recap" }> = {
  id: "legacy-recap-message",
  kind: "recap",
  role: "coach",
  created_at: recap.created_at,
  recap,
};
const rendered = renderToStaticMarkup(
  <RecapMessage
    message={message}
    quotaBlocked={false}
    busyAction={null}
    onAcceptProposal={() => undefined}
    onRejectProposal={() => undefined}
    proposalStatus="completed"
    rejectReason=""
    onRejectReasonChange={() => undefined}
  />,
);

assert.match(rendered, /Weekly recap/);
assert.match(rendered, /Consistency won the week/);
assert.doesNotMatch(rendered, /<script|onerror=/i);
assert.doesNotMatch(rendered, /Three calm sessions built momentum/);

console.log("Historical weekly recap blocks remain readable and SSR-safe in the real recap renderer.");
