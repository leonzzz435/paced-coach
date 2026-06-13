import assert from "node:assert/strict";

import {
  formatCompetitionsBadge,
  formatProfileCompletenessBadge,
  formatTrainingProviderBadge,
  type IntegrationsStatus,
} from "@/lib/types/athlete-context";

assert.equal(
  formatProfileCompletenessBadge(
    {
      physiology: { ftp: 250 },
      preferences: { sports: ["run", "bike"] },
      availability: { days_per_week: 6, time_windows: "weekday mornings" },
      goals: { primary_goal: "Half marathon" },
    },
    { available: true },
  ),
  "Profile 100% complete",
);

assert.equal(
  formatProfileCompletenessBadge(null, { available: false }),
  "Profile status unavailable",
);

assert.equal(
  formatCompetitionsBadge(5, { available: true }),
  "5 competitions saved",
);

assert.equal(
  formatCompetitionsBadge(null, { available: false }),
  "Competitions unavailable",
);

const connectedIntegrations: IntegrationsStatus = {
  strava: {
    linked: true,
    ever_connected: true,
    connected: true,
    operational: true,
    state: "connected",
    connection_state: "connected_usable",
    configured: true,
    oauth_enabled: true,
  },
  whoop: {
    linked: true,
    ever_connected: true,
    connected: true,
    operational: true,
    state: "connected",
    connection_state: "connected_usable",
    configured: true,
    oauth_enabled: true,
  },
};

assert.equal(
  formatTrainingProviderBadge(connectedIntegrations),
  "Strava + WHOOP active",
);

console.log("Dashboard header badges format durable and explicit fallback labels.");
