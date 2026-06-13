import type { DemoPersonaId } from "@/lib/demo/personas";
import type { UiAnalysis } from "@/lib/types/ui-blocks";

export const DEMO_ANALYSIS_BY_PERSONA: Record<DemoPersonaId, UiAnalysis> = {
  "hybrid-operator": {
  "analysis_id": "demo_analysis_hybrid_operator",
  "athlete_name": "Demo Athlete",
  "created_at": "2026-03-05T21:38:05.591301",
  "dashboard_kpis": [
    {
      "domain": "load",
      "kpi_id": "acwr-7d-28d",
      "label": "ACWR (7d/28d)",
      "status": "good",
      "trend": "↑ from 0.48 (Feb 28) — conservative relative to baseline (good rebuild signal)",
      "trend_points": null,
      "value": "0.76"
    },
    {
      "domain": "recovery",
      "kpi_id": "tsb",
      "label": "TSB",
      "status": "neutral",
      "trend": "From +33.6 (Feb 28) — freshness normalized to near-neutral readiness",
      "trend_points": null,
      "value": "-3.3"
    },
    {
      "domain": "recovery",
      "kpi_id": "hrv-overnight",
      "label": "HRV (overnight)",
      "status": "good",
      "trend": "Within baseline (101–155); rebound after Feb 22–26 suppression",
      "trend_points": [
        83.0,
        70.0,
        55.0,
        114.0,
        120.0,
        128.0,
        122.0,
        108.0
      ],
      "value": "108"
    },
    {
      "domain": "recovery",
      "kpi_id": "recovery-score",
      "label": "Recovery score",
      "status": "warning",
      "trend": "↓ from 89–95% (Mar 01–04) — likely sleep fragmentation (awake time)",
      "trend_points": [
        28.0,
        22.0,
        18.0,
        89.0,
        92.0,
        95.0,
        56.0
      ],
      "value": "56%"
    },
    {
      "domain": "sleep",
      "kpi_id": "sleep-rhr",
      "label": "Sleep RHR (overnight)",
      "status": "warning",
      "trend": "Mildly elevated vs best (42–44); not a multi-day red flag",
      "trend_points": [
        51.0,
        50.0,
        49.0,
        45.0,
        43.0,
        44.0,
        47.0
      ],
      "value": "47 bpm"
    },
    {
      "domain": "performance",
      "kpi_id": "vo2max-run",
      "label": "VO₂max (run)",
      "status": "good",
      "trend": "Stable since Feb 11 (improved early, then held through late-Feb downshift)",
      "trend_points": [
        49.0,
        50.0,
        51.0,
        52.0,
        52.0,
        52.0,
        52.0,
        52.0
      ],
      "value": "52.0"
    }
  ],
  "headline_brief": "You’re rebuilding load from a late-Feb reset: acute 88.5 and chronic 85.2 with conservative ACWR 0.76 and near-neutral TSB -3.3. VO₂max and your 1 km threshold reps stayed stable through the downshift, so fitness looks intact—your main limiter is sleep consistency after the Feb 22–26 crash and today’s recovery-score dip (56%) with mildly elevated sleep RHR. Keep ramps smooth and protect sleep; spikes + fragmented sleep is your clearest risk signature.",
  "coach_action": "Prioritize 8 hours sleep through Thursday — your HRV dipped and sleep RHR is elevated. No intensity until recovery normalizes.",
  "kpis": [
    {
      "domain": "load",
      "kpi_id": "acute-load-ewma",
      "label": "Acute load (EWMA)",
      "status": "neutral",
      "trend": "Rebuilding from 47.6 (Feb 28)",
      "trend_points": null,
      "value": "88.5 (Mar 05)"
    },
    {
      "domain": "load",
      "kpi_id": "chronic-load-ewma",
      "label": "Chronic load (EWMA)",
      "status": "neutral",
      "trend": "Rebuilding from 76.4 (Mar 03)",
      "trend_points": null,
      "value": "85.2 (Mar 05)"
    },
    {
      "domain": "load",
      "kpi_id": "acwr-7d-28d",
      "label": "ACWR (7d/28d)",
      "status": "good",
      "trend": "Up from 0.48 (Feb 28) — conservative for rebuild",
      "trend_points": null,
      "value": "0.76 (Mar 05)"
    },
    {
      "domain": "recovery",
      "kpi_id": "tsb",
      "label": "TSB",
      "status": "neutral",
      "trend": "From +33.6 (Feb 28) — reset → near-neutral readiness",
      "trend_points": null,
      "value": "-3.3 (Mar 05)"
    },
    {
      "domain": "load",
      "kpi_id": "monotony-7d",
      "label": "Monotony (7d)",
      "status": "good",
      "trend": "Improved vs peak 3.53 (Jan 08)",
      "trend_points": null,
      "value": "1.02 (Mar 05)"
    },
    {
      "domain": "load",
      "kpi_id": "strain-7d",
      "label": "Strain (7d)",
      "status": "good",
      "trend": "Down vs 2832.5 (Jan 08)",
      "trend_points": null,
      "value": "341.7 (by Mar 03; low recently)"
    },
    {
      "domain": "performance",
      "kpi_id": "vo2max-run",
      "label": "VO₂max (run)",
      "status": "good",
      "trend": "Improved early, then stable",
      "trend_points": [
        49.0,
        50.0,
        51.0,
        52.0,
        52.0,
        52.0,
        52.0,
        52.0
      ],
      "value": "52.0 (stable since Feb 11)"
    },
    {
      "domain": "performance",
      "kpi_id": "vo2max-bike",
      "label": "VO₂max (bike)",
      "status": "good",
      "trend": "Oscillating; peak maintained",
      "trend_points": null,
      "value": "53–54 (54 on Mar 02)"
    },
    {
      "domain": "recovery",
      "kpi_id": "hrv-overnight",
      "label": "HRV (overnight)",
      "status": "good",
      "trend": "Within baseline (101–155)",
      "trend_points": [
        83.0,
        70.0,
        55.0,
        114.0,
        120.0,
        128.0,
        122.0,
        108.0
      ],
      "value": "108"
    },
    {
      "domain": "sleep",
      "kpi_id": "sleep-rhr",
      "label": "Sleep RHR (overnight)",
      "status": "warning",
      "trend": "Mildly elevated vs best (42–44)",
      "trend_points": [
        51.0,
        50.0,
        49.0,
        45.0,
        43.0,
        44.0,
        47.0
      ],
      "value": "47 bpm"
    },
    {
      "domain": "recovery",
      "kpi_id": "recovery-score",
      "label": "Recovery score",
      "status": "warning",
      "trend": "Down from 89–95% (Mar 01–04)",
      "trend_points": [
        28.0,
        22.0,
        18.0,
        89.0,
        92.0,
        95.0,
        56.0
      ],
      "value": "56% (Mar 05)"
    }
  ],
  "schema_version": 1,
  "sections": [
    {
      "blocks": [],
      "nodes": [
        {
          "blocks": [
            {
              "content_html": "<div class=\"grid grid--2\">\n  <div class=\"card\">\n    <div><strong>Athlete</strong>: Demo Athlete</div>\n    <div><strong>Report date</strong>: 2026-03-05 (Thu)</div>\n  </div>\n  <div class=\"card\">\n    <div><strong>Goal context</strong> (time to key races)</div>\n    <table class=\"table\">\n      <thead><tr><th>Race</th><th>Priority</th><th>~Days</th><th>Notes</th></tr></thead>\n      <tbody>\n        <tr><td><strong>Ridge Trail 38 km</strong></td><td><span class=\"tag tag--a\">A</span></td><td>~59</td><td>Trail durability + climbs</td></tr>\n        <tr><td><strong>5k</strong></td><td><span class=\"tag tag--b\">B</span></td><td>~105</td><td>Speed marker</td></tr>\n        <tr><td><strong>10k</strong></td><td><span class=\"tag tag--a\">A</span></td><td>~106</td><td>Target referenced: 44:00 (~4:24/km)</td></tr>\n        <tr><td><strong>Olympic Tri</strong></td><td><span class=\"tag tag--a\">A</span></td><td>~157</td><td>Run-bike balance</td></tr>\n        <tr><td><strong>Half Marathon</strong></td><td><span class=\"tag tag--a\">A</span></td><td>~234</td><td>Durability + density over time</td></tr>\n      </tbody>\n    </table>\n  </div>\n</div>",
              "key": "context-header",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "notes"
            }
          ],
          "children": [],
          "default_open": null,
          "disclosure_mode": "inline",
          "node_id": "report-context",
          "summary": "Athlete: Demo Athlete • Report date: 2026-03-05 • Key-race countdowns + priorities.",
          "title": "Report context",
          "tone": "neutral"
        },
        {
          "blocks": [
            {
              "content_html": "<div class=\"callout-accent\">\n  <strong>Headline:</strong> You’re coming out of a late‑February “freshening” phase (load + TSB swing) with <strong>good physiological resilience</strong> (fast HRV/RHR rebound) and <strong>stable VO₂max estimates</strong>. The main risk pattern in this block is <strong>sharp load spiking</strong> (Jan 24) and a separate <strong>sleep/stress crash</strong> (Feb 22–26) that looks transient but meaningful.\n</div>",
              "key": "headline-callout",
              "title": "Headline",
              "tone": "neutral",
              "type": "html",
              "variant": "callout"
            },
            {
              "content_html": "<div class=\"grid grid--3\">\n  <div class=\"kpi-card\">\n    <div class=\"kpi-value\">88.5</div>\n    <div class=\"kpi-label\">Acute load (EWMA)</div>\n    <div class=\"kpi-note\">Rebuilding from 47.6 (Feb 28)</div>\n  </div>\n  <div class=\"kpi-card\">\n    <div class=\"kpi-value\">85.2</div>\n    <div class=\"kpi-label\">Chronic load (EWMA)</div>\n    <div class=\"kpi-note\">Rebuilding from 76.4 (Mar 03)</div>\n  </div>\n  <div class=\"kpi-card\">\n    <div class=\"kpi-value\">0.76</div>\n    <div class=\"kpi-label\">ACWR (7d/28d)</div>\n    <div class=\"kpi-note\">Up from 0.48 (Feb 28) — conservative</div>\n  </div>\n</div>\n<div class=\"grid grid--3\">\n  <div class=\"kpi-card\">\n    <div class=\"kpi-value\">-3.3</div>\n    <div class=\"kpi-label\">TSB</div>\n    <div class=\"kpi-note\">From +33.6 (Feb 28) — near-neutral readiness</div>\n  </div>\n  <div class=\"kpi-card\">\n    <div class=\"kpi-value\">1.02</div>\n    <div class=\"kpi-label\">Monotony (7d)</div>\n    <div class=\"kpi-note\">Improved vs peak 3.53 (Jan 08)</div>\n  </div>\n  <div class=\"kpi-card\">\n    <div class=\"kpi-value\">56%</div>\n    <div class=\"kpi-label\">Recovery score</div>\n    <div class=\"kpi-note\">Down from 89–95% (Mar 01–04)</div>\n  </div>\n</div>",
              "key": "kpi-cards",
              "title": "Front-row KPIs (Mar 05)",
              "tone": null,
              "type": "html",
              "variant": "generic"
            },
            {
              "content_html": "<table class=\"table\">\n  <thead>\n    <tr>\n      <th>Domain + KPI</th>\n      <th>Current / Latest</th>\n      <th>Recent direction</th>\n      <th>What it means (in context)</th>\n    </tr>\n  </thead>\n  <tbody>\n    <tr>\n      <td><span class=\"domain-chip domain-load\">Load</span> <strong>Acute load (EWMA)</strong></td>\n      <td><strong>88.5</strong> (Mar 05)</td>\n      <td>Rebuilding from 47.6 (Feb 28)</td>\n      <td><span class=\"badge badge-info\">Stimulus returned</span> Acute stimulus has returned after a short deload/break window.</td>\n    </tr>\n    <tr>\n      <td><span class=\"domain-chip domain-load\">Load</span> <strong>Chronic load (EWMA)</strong></td>\n      <td><strong>85.2</strong> (Mar 05)</td>\n      <td>Rebuilding from 76.4 (Mar 03)</td>\n      <td><span class=\"badge badge-info\">Base turning up</span> Fitness “base” dipped gradually and is now turning upward.</td>\n    </tr>\n    <tr>\n      <td><span class=\"domain-chip domain-load\">Load</span> <strong>ACWR (7d/28d)</strong></td>\n      <td><strong>0.76</strong> (Mar 05)</td>\n      <td>Up from 0.48 (Feb 28)</td>\n      <td><span class=\"badge badge-good\">Conservative</span> Current loading is <em>conservative</em> relative to your recent baseline—appropriate for rebuilding consistency.</td>\n    </tr>\n    <tr>\n      <td><span class=\"domain-chip domain-recovery\">Recovery</span> <strong>TSB</strong></td>\n      <td><strong>-3.3</strong> (Mar 05)</td>\n      <td>From +33.6 (Feb 28)</td>\n      <td><span class=\"badge badge-info\">Near-neutral</span> Freshness has normalized from a strong “reset” into near-neutral readiness.</td>\n    </tr>\n    <tr>\n      <td><span class=\"domain-chip domain-load\">Load</span> <strong>Monotony (7d)</strong></td>\n      <td><strong>1.02</strong> (Mar 05)</td>\n      <td>Improved vs peak 3.53 (Jan 08)</td>\n      <td><span class=\"badge badge-good\">Healthy variation</span> Day-to-day variation is currently <em>healthy</em> (lower risk signature than early Jan).</td>\n    </tr>\n    <tr>\n      <td><span class=\"domain-chip domain-load\">Load</span> <strong>Strain (7d)</strong></td>\n      <td>(Low recently) <strong>341.7</strong> by Mar 03</td>\n      <td>Down vs 2832.5 (Jan 08)</td>\n      <td><span class=\"badge badge-good\">Capacity available</span> Less cumulative stress than early block; capacity available to build.</td>\n    </tr>\n    <tr>\n      <td><span class=\"domain-chip domain-performance\">Performance</span> <strong>VO₂max (run)</strong></td>\n      <td><strong>52.0</strong> (stable since Feb 11)</td>\n      <td>Improved early, then stable</td>\n      <td><span class=\"badge badge-good\">Maintained</span> The late-Feb load downshift has <strong>not</strong> (yet) reduced estimated aerobic capacity.</td>\n    </tr>\n    <tr>\n      <td><span class=\"domain-chip domain-performance\">Performance</span> <strong>VO₂max (bike)</strong></td>\n      <td><strong>53–54</strong> (54 on Mar 02)</td>\n      <td>Oscillating, peak maintained</td>\n      <td><span class=\"badge badge-good\">Steady</span> Cycling aerobic marker remains steady at a strong level.</td>\n    </tr>\n    <tr>\n      <td><span class=\"domain-chip domain-recovery\">Recovery</span> <strong>HRV (overnight)</strong></td>\n      <td><strong>108</strong></td>\n      <td>Within baseline (101–155)</td>\n      <td><span class=\"badge badge-good\">Balanced</span> Autonomic state is broadly “balanced.”</td>\n    </tr>\n    <tr>\n      <td><span class=\"domain-chip domain-sleep\">Sleep</span> <strong>Sleep RHR (overnight)</strong></td>\n      <td><strong>47 bpm</strong></td>\n      <td>Mildly elevated vs best (42–44)</td>\n      <td><span class=\"badge badge-warn\">Watch</span> Consistent with slightly disrupted sleep, not a multi-day red flag.</td>\n    </tr>\n    <tr>\n      <td><span class=\"domain-chip domain-recovery\">Recovery</span> <strong>Recovery score</strong></td>\n      <td><strong>56%</strong> (Mar 05)</td>\n      <td>Down from 89–95% (Mar 01–04)</td>\n      <td><span class=\"badge badge-warn\">Small dip</span> A small dip likely driven by sleep fragmentation (awake time).</td>\n    </tr>\n  </tbody>\n</table>",
              "key": "kpi-summary-table",
              "title": "Full KPI table (with context)",
              "tone": null,
              "type": "html",
              "variant": "generic"
            },
            {
              "content_html": "<div class=\"quote\">\n  Main watch-outs in this block: <strong>sharp load spiking</strong> (Jan 24) and a separate <strong>sleep/stress crash</strong> (Feb 22–26). When either pattern reappears, treat the next 48–72h as a risk window.\n</div>",
              "key": "risk-signature-quote",
              "title": "Key risk patterns (from this block)",
              "tone": null,
              "type": "html",
              "variant": "generic"
            }
          ],
          "children": [],
          "default_open": true,
          "disclosure_mode": "collapsible",
          "node_id": "kpi-snapshot-mar05",
          "summary": "Mar 05: acute 88.5, chronic 85.2, ACWR 0.76, TSB -3.3, monotony 1.02; VO₂max stable; recovery score dipped.",
          "title": "KPI Summary (current state + recent direction)",
          "tone": "neutral"
        }
      ],
      "section_id": "overview-kpis",
      "summary": "Reload underway after a late-Feb reset: conservative ACWR, near-neutral TSB, stable VO₂max; main watch-out is sleep disruption.",
      "title": "Overview — context + KPI snapshot",
      "tone": "good"
    },
    {
      "blocks": [],
      "nodes": [
        {
          "blocks": [
            {
              "content_html": "<div class=\"card big-stat\">\n  <div class=\"big-stat-value\">352.7</div>\n  <div class=\"big-stat-label\">Daily load peak (2026-01-24)</div>\n</div>",
              "key": "phase-a-bigstat",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "generic"
            },
            {
              "content_html": "<table class=\"table\">\n  <thead><tr><th>Metric</th><th>Value</th><th>Domain</th><th>Status</th></tr></thead>\n  <tbody>\n    <tr><td><strong>Acute EWMA (peak)</strong></td><td>160.2</td><td><span class=\"domain-chip domain-load\">Load</span></td><td><span class=\"badge badge-bad\">Spike</span></td></tr>\n    <tr><td><strong>Chronic EWMA (peak)</strong></td><td>118.5</td><td><span class=\"domain-chip domain-load\">Load</span></td><td><span class=\"badge badge-warn\">High</span></td></tr>\n    <tr><td><strong>ACWR (peak)</strong></td><td>1.60</td><td><span class=\"domain-chip domain-load\">Load</span></td><td><span class=\"badge badge-bad\">High risk signature</span></td></tr>\n    <tr><td><strong>TSB (minimum)</strong></td><td>-41.7</td><td><span class=\"domain-chip domain-recovery\">Recovery</span></td><td><span class=\"badge badge-bad\">Very negative</span></td></tr>\n  </tbody>\n</table>\n<div class=\"callout-info\">\n  <strong>Related (earlier) volatility marker:</strong> monotony/strain peaked on <strong>Jan 08</strong> — monotony <strong>3.53</strong>, strain <strong>2832.5</strong>, indicating <strong>repeated similar days</strong> (less variation) and higher accumulation.\n</div>",
              "key": "phase-a-peaks",
              "title": "Jan 24 peak stack (coinciding signals)",
              "tone": null,
              "type": "html",
              "variant": "generic"
            },
            {
              "content_html": "<div class=\"callout-danger\">\n  <strong>Classic “too much, too soon” signature:</strong> high acute load relative to baseline + very negative TSB. It doesn’t prove injury/overreaching, but it flags the <em>pattern</em> most likely to create problems if repeated.\n</div>",
              "key": "phase-a-interpretation",
              "title": "Interpretation",
              "tone": "danger",
              "type": "html",
              "variant": "callout"
            }
          ],
          "children": [],
          "default_open": null,
          "disclosure_mode": "collapsible",
          "node_id": "phase-a-early-jan",
          "summary": "Jan 24 peak: daily load 352.7 with acute 160.2, chronic 118.5, ACWR 1.60, TSB -41.7; monotony/strain peak earlier on Jan 08.",
          "title": "Phase A — Early January: high stimulus + volatility (clearest risk signature)",
          "tone": "warning"
        },
        {
          "blocks": [
            {
              "content_html": "<div class=\"grid grid--3\">\n  <div class=\"card big-stat\">\n    <div class=\"big-stat-value\">47.6</div>\n    <div class=\"big-stat-label\">Acute EWMA (Feb 28)</div>\n  </div>\n  <div class=\"card big-stat\">\n    <div class=\"big-stat-value\">0.48</div>\n    <div class=\"big-stat-label\">ACWR (Feb 28)</div>\n  </div>\n  <div class=\"card big-stat\">\n    <div class=\"big-stat-value\">+33.6</div>\n    <div class=\"big-stat-label\">TSB (Feb 28) — very fresh</div>\n  </div>\n</div>\n<ul>\n  <li><strong>Acute load</strong> fell steadily into late February and then <strong>collapsed</strong> during a short break/deload window with several <strong>0-load days</strong>.</li>\n  <li><strong>Chronic load</strong> declined more gradually and bottomed slightly later: <strong>76.4 on Mar 03</strong> (fitness decays slower than fatigue).</li>\n</ul>",
              "key": "phase-b-reset-metrics",
              "title": "Feb 28 “reset” snapshot",
              "tone": null,
              "type": "html",
              "variant": "generic"
            },
            {
              "content_html": "<div class=\"callout-info\">\n  This downshift created a meaningful freshness rebound. For an athlete with multiple spring/summer targets, this reads more like a <strong>controlled reset</strong> (intentional or forced) than a loss of form—especially because <strong>VO₂max estimates stayed stable</strong>.\n</div>",
              "key": "phase-b-interpretation",
              "title": "Interpretation",
              "tone": "neutral",
              "type": "html",
              "variant": "callout"
            }
          ],
          "children": [],
          "default_open": null,
          "disclosure_mode": "collapsible",
          "node_id": "phase-b-feb-reset",
          "summary": "Acute load fell steadily then collapsed with several 0-load days; Feb 28 looked like a reset (acute 47.6, ACWR 0.48, TSB +33.6). Chronic bottomed later (76.4 on Mar 03).",
          "title": "Phase B — February: load trends down, then a short break/deload window",
          "tone": "neutral"
        },
        {
          "blocks": [
            {
              "content_html": "<div class=\"grid grid--2\">\n  <div class=\"card\">\n    <div><strong>Window:</strong> <span class=\"badge badge-bad\">Feb 22–26</span></div>\n    <table class=\"table\">\n      <thead><tr><th>Signal</th><th>Details</th></tr></thead>\n      <tbody>\n        <tr><td><strong>Sleep / stress</strong></td><td><strong>Very poor sleep</strong> (e.g., <strong>1.77h</strong> on Feb 22), high stress (avg ~<strong>54–55</strong>, max <strong>99</strong>)</td></tr>\n        <tr><td><strong>HRV / RHR</strong></td><td>HRV suppressed (watch <strong>83 → 55</strong>), RHR elevated (watch <strong>51</strong>, wearable RHR <strong>60–63</strong>)</td></tr>\n        <tr><td><strong>Supporting markers</strong></td><td>Recovery score <strong>28% → 18%</strong>; skin temp elevated (~<strong>33.6–33.7°C</strong> vs ~<strong>32.4–32.8</strong>)</td></tr>\n        <tr><td><strong>Likely interpretation</strong></td><td><span class=\"badge badge-warn\">Acute stressor</span> Severe sleep disruption and/or short illness/inflammatory spike</td></tr>\n      </tbody>\n    </table>\n  </div>\n\n  <div class=\"card\">\n    <div><strong>Window:</strong> <span class=\"badge badge-good\">Feb 27–Mar 04</span></div>\n    <table class=\"table\">\n      <thead><tr><th>Signal</th><th>Details</th></tr></thead>\n      <tbody>\n        <tr><td><strong>Sleep / stress</strong></td><td>Sleep improves</td></tr>\n        <tr><td><strong>HRV / RHR</strong></td><td>HRV restores (watch <strong>114–128</strong>, wearable HRV <strong>138–146</strong>), RHR normalizes (<strong>43–47</strong>)</td></tr>\n        <tr><td><strong>Supporting markers</strong></td><td>Recovery score <strong>89–95%</strong></td></tr>\n        <tr><td><strong>Likely interpretation</strong></td><td><span class=\"badge badge-good\">Rapid rebound</span> Good resilience, low evidence of chronic maladaptation</td></tr>\n      </tbody>\n    </table>\n  </div>\n</div>",
              "key": "phase-c-two-window-cards",
              "title": "Crash window vs rebound window (table-form, same fields)",
              "tone": null,
              "type": "html",
              "variant": "generic"
            },
            {
              "content_html": "<div class=\"callout-warning\">\n  Wearable strain data shows a <strong>concentrated high-strain stretch Feb 21–25</strong>, overlapping with this crash window and with <strong>long-duration activity (notably ski)</strong>. Even if part of the strain is “life stress,” this period clearly <strong>compounded training stress with poor recovery conditions</strong>.\n</div>",
              "key": "phase-c-integration",
              "title": "Key integration point",
              "tone": "warning",
              "type": "html",
              "variant": "callout"
            }
          ],
          "children": [],
          "default_open": null,
          "disclosure_mode": "collapsible",
          "node_id": "phase-c-crash",
          "summary": "Feb 22–26: very poor sleep + high stress + HRV suppression (83→55) + RHR elevation (watch 51; wearable 60–63) + low recovery score (28→18) + elevated skin temp.",
          "title": "Phase C — Feb 22–26: acute physiology “crash” overlays the training picture",
          "tone": "warning"
        },
        {
          "blocks": [
            {
              "content_html": "<table class=\"table\">\n  <thead><tr><th>Metric</th><th>Value</th><th>Domain</th><th>Status</th></tr></thead>\n  <tbody>\n    <tr><td><strong>Acute EWMA</strong></td><td>88.5 (Mar 05)</td><td><span class=\"domain-chip domain-load\">Load</span></td><td><span class=\"badge badge-info\">Rebuild</span></td></tr>\n    <tr><td><strong>Chronic EWMA</strong></td><td>85.2 (Mar 05)</td><td><span class=\"domain-chip domain-load\">Load</span></td><td><span class=\"badge badge-info\">Rebuild</span></td></tr>\n    <tr><td><strong>TSB</strong></td><td>-3.3 (Mar 05)</td><td><span class=\"domain-chip domain-recovery\">Recovery</span></td><td><span class=\"badge badge-info\">Near-neutral</span></td></tr>\n    <tr><td><strong>Monotony (7d)</strong></td><td>1.02 (Mar 05)</td><td><span class=\"domain-chip domain-load\">Load</span></td><td><span class=\"badge badge-good\">Protective</span></td></tr>\n  </tbody>\n</table>",
              "key": "phase-d-metrics",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "generic"
            },
            {
              "content_html": "<div class=\"callout-good\">\n  You’re no longer “super fresh,” but also not deeply fatigued (<strong>TSB -3.3</strong>). A key positive is <strong>monotony 1.02</strong>: the reload is happening with <strong>good variability</strong> (a key difference vs early January).\n</div>",
              "key": "phase-d-interpretation",
              "title": "Interpretation",
              "tone": "good",
              "type": "html",
              "variant": "callout"
            }
          ],
          "children": [],
          "default_open": null,
          "disclosure_mode": "collapsible",
          "node_id": "phase-d-early-mar-reload",
          "summary": "By Mar 05: acute 88.5, chronic 85.2, TSB -3.3; monotony 1.02 indicates good variability during reload.",
          "title": "Phase D — Early March: reload begins, readiness near neutral",
          "tone": "good"
        }
      ],
      "section_id": "block-narrative",
      "summary": "Early Jan: high stimulus + volatility (risk signature). Feb: downshift + reset. Feb 22–26: sleep/stress physiology crash. Early Mar: reload with healthier variability.",
      "title": "Block narrative (Jan → early Mar): what happened + response",
      "tone": "warning"
    },
    {
      "blocks": [],
      "nodes": [
        {
          "blocks": [
            {
              "content_html": "<table class=\"table\">\n  <thead>\n    <tr>\n      <th>Metric</th>\n      <th>Jan 24 (peak stress)</th>\n      <th>Feb 28 (deep deload)</th>\n      <th>Mar 05 (current)</th>\n    </tr>\n  </thead>\n  <tbody>\n    <tr>\n      <td><strong>Daily load</strong></td>\n      <td><strong>352.7</strong></td>\n      <td>(multiple 0 days around this period)</td>\n      <td>—</td>\n    </tr>\n    <tr>\n      <td><strong>Acute EWMA</strong></td>\n      <td><strong>160.2</strong></td>\n      <td><strong>47.6</strong></td>\n      <td><strong>88.5</strong></td>\n    </tr>\n    <tr>\n      <td><strong>Chronic EWMA</strong></td>\n      <td><strong>118.5</strong></td>\n      <td>~80s (declining)</td>\n      <td><strong>85.2</strong></td>\n    </tr>\n    <tr>\n      <td><strong>ACWR</strong></td>\n      <td><strong>1.60</strong></td>\n      <td><strong>0.48</strong></td>\n      <td><strong>0.76</strong></td>\n    </tr>\n    <tr>\n      <td><strong>TSB</strong></td>\n      <td><strong>-41.7</strong></td>\n      <td><strong>+33.6</strong></td>\n      <td><strong>-3.3</strong></td>\n    </tr>\n    <tr>\n      <td><strong>Monotony (7d)</strong></td>\n      <td>—</td>\n      <td>—</td>\n      <td><strong>1.02</strong></td>\n    </tr>\n  </tbody>\n</table>",
              "key": "anchor-dates",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "generic"
            }
          ],
          "children": [],
          "default_open": null,
          "disclosure_mode": "inline",
          "node_id": "anchor-dates-table",
          "summary": "Jan 24 peak stress vs Feb 28 deep deload vs Mar 05 current (acute/chronic/ACWR/TSB/monotony).",
          "title": "Load trend summary (key anchor dates)",
          "tone": "neutral"
        },
        {
          "blocks": [
            {
              "content_html": "<ul>\n  <li><strong>Your system tolerates meaningful training load</strong>, but the risk is not “high load” per se—it’s <strong>rapid change</strong> (spikes).</li>\n  <li>The current <strong>ACWR (~0.76)</strong> + near-neutral <strong>TSB</strong> suggests a <strong>stable platform to rebuild</strong> chronic load without needing dramatic changes.</li>\n  <li><strong>Variability has improved</strong> (low monotony). This is one of the strongest protective signals in your current pattern.</li>\n</ul>",
              "key": "implications-bullets",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "generic"
            },
            {
              "content_html": "<div class=\"callout-accent\">\n  The data suggests your best lever is <strong>how you distribute load</strong> (variation and avoiding abrupt ramps), not necessarily lowering ambition. You have evidence of strong adaptation when the week-to-week changes are controlled.\n</div>",
              "key": "coaching-insight-callout",
              "title": "Coaching insight (non-prescriptive)",
              "tone": "neutral",
              "type": "html",
              "variant": "callout"
            }
          ],
          "children": [],
          "default_open": null,
          "disclosure_mode": "inline",
          "node_id": "load-dynamics-implications",
          "summary": "Tolerance is good; hazard is abrupt ramps/spikes. Current ACWR + near-neutral TSB = stable rebuild platform; variability (low monotony) is protective.",
          "title": "What the load dynamics imply",
          "tone": "good"
        },
        {
          "blocks": [
            {
              "content_html": "<div class=\"callout-warning\">\n  The primary load feed shows <strong>8 dates with 0.0 daily load</strong> through <strong>2026‑03‑03</strong> while other derived fields remain non-zero. This likely mixes true rest with <strong>missing capture / device logic</strong>. Interpret the <em>exact depth</em> of the deload cautiously; the <strong>direction</strong> (clear downshift) is still reliable.\n</div>",
              "key": "data-quality-callout",
              "title": null,
              "tone": "warning",
              "type": "html",
              "variant": "callout"
            }
          ],
          "children": [],
          "default_open": null,
          "disclosure_mode": "inline",
          "node_id": "data-quality-note",
          "summary": "The primary load feed shows 8 dates with 0.0 daily load through 2026-03-03 while derived fields remain non-zero; some “rest” may be missing capture.",
          "title": "Data quality note (important)",
          "tone": "warning"
        }
      ],
      "section_id": "load-risk-analysis",
      "summary": "Main risk driver is rate-of-change (spikes), not high load per se; current ACWR ~0.76 + low monotony supports controlled rebuild; interpret 0-load days cautiously.",
      "title": "Load, consistency & risk pattern analysis",
      "tone": "good"
    },
    {
      "blocks": [],
      "nodes": [
        {
          "blocks": [
            {
              "content_html": "<div class=\"callout-info\">\n  You’re showing a clear <strong>“easy volume + occasional quality”</strong> pattern.\n</div>",
              "key": "running-overview",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "notes"
            },
            {
              "content_html": "<table class=\"table\">\n  <thead><tr><th>Date</th><th>Distance</th><th>Pace</th><th>HR / Power</th></tr></thead>\n  <tbody>\n    <tr>\n      <td><strong>Feb 07</strong></td>\n      <td>15.8 km</td>\n      <td>@ 6:22/km</td>\n      <td>avg HR <strong>138</strong>, avg power <strong>305 W</strong></td>\n    </tr>\n    <tr>\n      <td><strong>Feb 21</strong></td>\n      <td>16.33 km</td>\n      <td>@ 6:23/km</td>\n      <td>avg HR <strong>139</strong>, avg power <strong>301 W</strong> (wearable: <strong>85.6 min Z2</strong> of <strong>104.1 min</strong>)</td>\n    </tr>\n  </tbody>\n</table>\n<div class=\"callout-good\">\n  <strong>Interpretation:</strong> These are genuinely easy/steady (HR ~high Z1/low Z2), which supports (a) recovery between harder days and (b) long-course durability relevant for trail + triathlon.\n</div>",
              "key": "running-easy-runs",
              "title": "Easy aerobic runs (durability/base)",
              "tone": null,
              "type": "html",
              "variant": "generic"
            },
            {
              "content_html": "<div class=\"grid grid--2\">\n  <div class=\"card\">\n    <div class=\"workout\">\n      <div class=\"workout-title\">Run — 5 × 1 km (fasted)</div>\n      <div class=\"workout-meta\">2026-02-04 · <span class=\"focus focus--threshold\">Threshold density</span></div>\n    </div>\n    <ul>\n      <li><strong>Pace:</strong> ~4:36–4:48/km</li>\n      <li><strong>Rep HR:</strong> 171–176 (max 184)</li>\n      <li><strong>Rep power:</strong> ~397–411 W</li>\n    </ul>\n  </div>\n\n  <div class=\"card\">\n    <div class=\"workout\">\n      <div class=\"workout-title\">Run — 4 × 1 km</div>\n      <div class=\"workout-meta\">2026-03-04 · <span class=\"focus focus--threshold\">Threshold / aerobic power</span></div>\n    </div>\n    <ul>\n      <li><strong>Rep splits:</strong> <strong>4:46 / 4:38 / 4:54 / 4:47</strong></li>\n      <li><strong>Rep avg HR:</strong> 170–174 (max 180)</li>\n      <li><strong>Rep power:</strong> <strong>372–415 W</strong></li>\n    </ul>\n  </div>\n</div>\n<div class=\"callout-accent\">\n  <strong>Interpretation:</strong>\n  <ul>\n    <li>Execution is <strong>consistent over a month</strong>: 1 km reps cluster ~4:35–4:55/km with HR rising around/above LTHR (profile LTHR ~<strong>175</strong>). That consistency is a strong marker of stable fitness despite February load fluctuations.</li>\n    <li>Recoveries show <strong>incomplete HR drop</strong> (often still ~160s), which makes these sessions <strong>metabolically dense</strong>. That’s not “bad,” but it means the workout can drift toward VO₂/anaerobic stress if overall fatigue/sleep is compromised.</li>\n  </ul>\n</div>",
              "key": "running-threshold-intervals",
              "title": "Threshold/“density” intervals (lactate clearance / strong aerobic power)",
              "tone": null,
              "type": "html",
              "variant": "generic"
            },
            {
              "content_html": "<div class=\"workout\">\n  <div class=\"workout-title\">Run — easy + strides/surges</div>\n  <div class=\"workout-meta\">2026-03-05 · <span class=\"focus focus--easy\">Easy</span> + <span class=\"focus focus--neuromuscular\">Neuromuscular</span></div>\n</div>\n<ul>\n  <li><strong>Easy running:</strong> ~6:00–6:11/km (298–317 W)</li>\n  <li><strong>Short surges:</strong> 0.11–0.14 km at <strong>~3:00–3:44/km</strong> with <strong>~480–493 W</strong></li>\n  <li><strong>Max HR:</strong> 169</li>\n</ul>\n<div class=\"callout-good\">\n  <strong>Interpretation:</strong> A low-cost way to keep leg speed and stiffness “online” while keeping total high-HR time modest—often a good fit when rebuilding load and protecting readiness.\n</div>",
              "key": "running-strides",
              "title": "Neuromuscular add-on (strides) with low systemic stress",
              "tone": null,
              "type": "html",
              "variant": "generic"
            }
          ],
          "children": [],
          "default_open": null,
          "disclosure_mode": "collapsible",
          "node_id": "running-execution",
          "summary": "Easy aerobic runs are genuinely easy; 1 km reps are consistent across a month (around/above LTHR ~175) with dense recoveries; strides add low-cost speed.",
          "title": "A) Running: polarized structure + repeatable threshold execution",
          "tone": "neutral"
        },
        {
          "blocks": [
            {
              "content_html": "<div class=\"workout\">\n  <div class=\"workout-title\">Bike — sweet spot (65 min)</div>\n  <div class=\"workout-meta\">2026-03-02 · <span class=\"focus focus--tempo\">Tempo / sub-threshold</span></div>\n</div>\n<table class=\"table\">\n  <thead><tr><th>Metric</th><th>Value</th><th>Domain</th><th>Status</th></tr></thead>\n  <tbody>\n    <tr><td><strong>Avg power</strong></td><td>172 W</td><td><span class=\"domain-chip domain-performance\">Performance</span></td><td><span class=\"badge badge-info\">Steady</span></td></tr>\n    <tr><td><strong>NP</strong></td><td>181 W</td><td><span class=\"domain-chip domain-performance\">Performance</span></td><td><span class=\"badge badge-info\">Controlled</span></td></tr>\n    <tr><td><strong>IF</strong></td><td>0.762</td><td><span class=\"domain-chip domain-load\">Load</span></td><td><span class=\"badge badge-good\">Compatible</span></td></tr>\n    <tr><td><strong>Main set</strong></td><td>2 × ~12 min @ ~212–213 W</td><td><span class=\"domain-chip domain-performance\">Performance</span></td><td><span class=\"badge badge-info\">Sweet spot</span></td></tr>\n    <tr><td><strong>HR (main set)</strong></td><td>~148–150 (max ~156–157)</td><td><span class=\"domain-chip domain-recovery\">Recovery</span></td><td><span class=\"badge badge-info\">Modest drift</span></td></tr>\n  </tbody>\n</table>\n<div class=\"callout-good\">\n  <strong>Interpretation:</strong> Controlled sub-threshold/tempo work with modest drift—good aerobic support for Olympic triathlon demands, and generally compatible with run quality if recovery is stable.\n</div>",
              "key": "cycling-session",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "workout"
            }
          ],
          "children": [],
          "default_open": null,
          "disclosure_mode": "inline",
          "node_id": "cycling-execution",
          "summary": "Mar 02: 65 min sweet spot, NP 181 W, IF 0.762; main set 2×~12 min @ ~212–213 W with HR ~148–150.",
          "title": "B) Cycling: steady sweet-spot work (tempo durability)",
          "tone": "neutral"
        },
        {
          "blocks": [
            {
              "content_html": "<div class=\"workout\">\n  <div class=\"workout-title\">Ski — long duration</div>\n  <div class=\"workout-meta\">2026-02-25 · 5:52:29 · <span class=\"focus focus--endurance\">Endurance</span></div>\n</div>\n<ul>\n  <li><strong>Avg HR:</strong> 113 (wearable avg 109)</li>\n  <li><strong>Max HR:</strong> 162</li>\n  <li><strong>Zone time:</strong> mostly Z0–Z2</li>\n</ul>\n<div class=\"callout-warning\">\n  <strong>Interpretation:</strong> Cardiovascularly it reads “easy,” but musculoskeletally skiing often creates <strong>eccentric quad fatigue and joint/tendon load</strong>. This can reduce run interval pop for <strong>24–72h</strong> even when HRV looks fine—i.e., legs can be locally fatigued while autonomic markers have recovered.\n</div>",
              "key": "ski-session",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "workout"
            }
          ],
          "children": [],
          "default_open": null,
          "disclosure_mode": "inline",
          "node_id": "skiing-execution",
          "summary": "Feb 25 ski: 5:52:29, avg HR ~113 (wearable 109), max 162; mostly Z0–Z2 — but likely high eccentric/joint/tendon load.",
          "title": "C) Skiing: long duration with low average HR but high “leg cost”",
          "tone": "warning"
        }
      ],
      "section_id": "execution-quality",
      "summary": "Running is polarized (true easy + repeatable threshold density); bike sweet spot looks controlled; long ski adds hidden leg cost despite low HR.",
      "title": "Execution quality — what you actually did (run, bike, ski)",
      "tone": "good"
    },
    {
      "blocks": [],
      "nodes": [
        {
          "blocks": [
            {
              "content_html": "<div class=\"callout-good\">\n  <strong>Outside the Feb 22–26 event, your baseline profile is excellent:</strong>\n  <ul>\n    <li>Sleep RHR frequently <strong>37–44 bpm</strong></li>\n    <li>HRV largely <strong>within baseline</strong> and rebounds quickly after perturbation</li>\n    <li>The rebound (Feb 27–Mar 04) is a major positive: it argues against sustained overreaching and suggests <strong>high recovery capacity</strong> when sleep is stable.</li>\n  </ul>\n</div>",
              "key": "strong-callout",
              "title": null,
              "tone": "good",
              "type": "html",
              "variant": "callout"
            }
          ],
          "children": [],
          "default_open": null,
          "disclosure_mode": "inline",
          "node_id": "recovery-strong",
          "summary": "Excellent baseline outside Feb 22–26; sleep RHR often 37–44 bpm; HRV within baseline and rebounds quickly; Feb 27–Mar 04 rebound argues against sustained overreaching.",
          "title": "What’s strong",
          "tone": "good"
        },
        {
          "blocks": [
            {
              "content_html": "<div class=\"callout-warning\">\n  <strong>The clearest limiter in this dataset is sleep disruption:</strong>\n  <ul>\n    <li><strong>Feb 22:</strong> extremely short sleep + very high stress + HRV suppression + RHR elevation</li>\n    <li><strong>Mar 05:</strong> mild recurrence pattern (more awake time, efficiency <strong>84.9%</strong>, recovery score down to <strong>56%</strong>)—consistent with your note (<strong>late chocolate</strong>)</li>\n  </ul>\n</div>",
              "key": "vulnerable-callout",
              "title": null,
              "tone": "warning",
              "type": "html",
              "variant": "callout"
            }
          ],
          "children": [],
          "default_open": null,
          "disclosure_mode": "inline",
          "node_id": "recovery-vulnerable",
          "summary": "Sleep disruption is the clearest limiter; Feb 22 shows extreme sleep + high stress + HRV suppression + RHR elevation; Mar 05 shows mild recurrence (awake time, efficiency 84.9%, recovery score 56%) consistent with late chocolate note.",
          "title": "What’s vulnerable",
          "tone": "warning"
        },
        {
          "blocks": [
            {
              "content_html": "<div class=\"callout-info\">\n  The Feb 22–26 cluster includes <strong>elevated skin temperature</strong> plus <strong>HRV suppression</strong> and <strong>RHR elevation</strong>. That combination can reflect an inflammatory/illness-like stressor <em>or</em> extreme sleep debt.\n</div>\n<div class=\"quote\">\n  You don’t need to label it definitively for it to be useful: it’s a recognizable “do not over-interpret performance” signature if it appears again.\n</div>",
              "key": "illness-vs-stress",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "generic"
            }
          ],
          "children": [],
          "default_open": null,
          "disclosure_mode": "collapsible",
          "node_id": "illness-like-vs-life-stress",
          "summary": "Feb 22–26 includes elevated skin temperature + HRV suppression + RHR elevation; label not required—treat as “don’t over-interpret performance” signature if it returns.",
          "title": "“Illness-like” vs “life-stress” signal (how to use it)",
          "tone": "neutral"
        }
      ],
      "section_id": "recovery-physiology",
      "summary": "Strong baseline + rapid rebound after Feb 22–26 supports high recovery capacity; sleep disruption is the clearest vulnerability and can make performance signals noisy.",
      "title": "Physiological response & recovery",
      "tone": "warning"
    },
    {
      "blocks": [],
      "nodes": [
        {
          "blocks": [
            {
              "content_html": "<div class=\"grid grid--2\">\n  <div class=\"card\">\n    <div class=\"card big-stat\">\n      <div class=\"big-stat-value\">49.0 → 52.0</div>\n      <div class=\"big-stat-label\">Run VO₂max (Jan 04 → Feb 11), then stable through Mar 05</div>\n    </div>\n  </div>\n  <div class=\"card\">\n    <div class=\"card big-stat\">\n      <div class=\"big-stat-value\">53–54</div>\n      <div class=\"big-stat-label\">Bike VO₂max oscillation; 54 on Jan 29 and again Mar 02</div>\n    </div>\n  </div>\n</div>\n<div class=\"callout-good\">\n  <strong>Interpretation:</strong> The late-Feb load drop has not degraded these markers. That usually means your aerobic base is intact; the next gains are more likely to come from <strong>consistent training density over time</strong> than from chasing short-term intensity spikes.\n</div>",
              "key": "vo2max-table",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "generic"
            }
          ],
          "children": [],
          "default_open": null,
          "disclosure_mode": "inline",
          "node_id": "vo2max-trends",
          "summary": "Run VO₂max 49.0 (Jan 04) → 52.0 (first on Feb 11) then stable; Bike VO₂max oscillates 53–54 with 54 on Jan 29 and Mar 02.",
          "title": "VO₂max estimates: improved early, then held steady",
          "tone": "good"
        },
        {
          "blocks": [
            {
              "content_html": "<ul>\n  <li>Your repeatable 1 km reps (~<strong>4:35–4:55/km</strong>) suggest threshold/aerobic power is in a <strong>solid build state</strong>.</li>\n  <li>For the <strong>10k 44:00 target</strong> (~<strong>4:24/km</strong>), the current rep paces indicate you’re working in the right neighborhood, but there’s still a gap between controlled repeats and sustained race execution—especially relevant as you balance trail demands (strength/endurance) with road speed.</li>\n  <li>For <strong>Ridge Trail (38 km, rolling climbs)</strong>, the combination of:\n    <ul>\n      <li>true easy aerobic runs,</li>\n      <li>long ski durability stimulus,</li>\n      <li>and preserved VO₂max</li>\n    </ul>\n    suggests a good foundation—while highlighting that <strong>musculoskeletal resilience</strong> (eccentric load tolerance, connective tissue robustness) is likely the decisive factor, not raw cardio.\n  </li>\n</ul>",
              "key": "run-targets-bullets",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "generic"
            }
          ],
          "children": [],
          "default_open": null,
          "disclosure_mode": "collapsible",
          "node_id": "run-quality-vs-targets",
          "summary": "1 km reps ~4:35–4:55/km indicate solid build; 10k 44:00 needs ~4:24/km sustained; Ridge Trail likely decided by eccentric/load tolerance more than cardio.",
          "title": "Run quality vs race targets (directional)",
          "tone": "neutral"
        },
        {
          "blocks": [
            {
              "content_html": "<ul>\n  <li><strong>Resilience is a defining strength:</strong> you demonstrated a rapid return to baseline after a sharp stress event.</li>\n  <li><strong>Current load metrics support a controlled rebuild:</strong> ACWR &lt; 1 and TSB near neutral with low monotony is a favorable risk profile for increasing consistency.</li>\n  <li><strong>Execution quality is repeatable:</strong> threshold reps are clustered and stable; easy days are truly easy.</li>\n</ul>",
              "key": "positives",
              "title": "Primary positive implications",
              "tone": null,
              "type": "html",
              "variant": "generic"
            },
            {
              "content_html": "<ol>\n  <li>\n    <strong>Load spikes (main historical risk pattern)</strong>\n    <ul>\n      <li>Jan 24 shows the highest combined risk signature (high acute, high ACWR, very negative TSB).</li>\n      <li>Risk is driven by <em>rate of change</em>, not simply “training hard.”</li>\n    </ul>\n  </li>\n  <li>\n    <strong>Sleep-driven stress cascades</strong>\n    <ul>\n      <li>The Feb 22–26 event shows how quickly sleep disruption can suppress HRV and raise RHR.</li>\n      <li>When that happens, performance and recovery signals become noisy, and perceived exertion often rises at the same external workload.</li>\n    </ul>\n  </li>\n  <li>\n    <strong>Hidden leg fatigue from long skiing</strong>\n    <ul>\n      <li>Low HR does not equal low cost; skiing can add “durability stress” that isn’t well captured by HR-based load.</li>\n      <li>This can blunt run quality and increase tissue-level injury risk if layered onto dense running without adequate recovery conditions.</li>\n    </ul>\n  </li>\n  <li>\n    <strong>Data gaps (0-load days)</strong>\n    <ul>\n      <li>Some “rest” may be missing data. This can make ramp-rate and monotony look artificially better/worse depending on where the gaps sit.</li>\n    </ul>\n  </li>\n</ol>",
              "key": "risks",
              "title": "Key risks to monitor",
              "tone": null,
              "type": "html",
              "variant": "generic"
            },
            {
              "content_html": "<div class=\"quote\">\n  The most actionable theme is not intensity vs endurance—it’s <strong>matching training stress to recovery conditions</strong>, where <strong>sleep consistency</strong> is the highest-leverage variable and spikes are the clearest hazard.\n</div>",
              "key": "practical-takeaway",
              "title": "Practical takeaway",
              "tone": null,
              "type": "html",
              "variant": "generic"
            }
          ],
          "children": [],
          "default_open": null,
          "disclosure_mode": "collapsible",
          "node_id": "implications-risks-non-prescriptive",
          "summary": "Primary positives: resilience, controlled rebuild profile, repeatable execution. Risks: load spikes, sleep cascades, hidden ski leg fatigue, data gaps; practical takeaway centers on matching stress to recovery conditions.",
          "title": "Implications & risks (non-prescriptive)",
          "tone": "warning"
        },
        {
          "blocks": [
            {
              "content_html": "<table class=\"table\">\n  <thead><tr><th>Date</th><th>Session</th><th>Target</th><th>What the data says</th></tr></thead>\n  <tbody>\n    <tr>\n      <td><strong>2026-02-04</strong></td>\n      <td>Run: 5×1 km (fasted)</td>\n      <td>Threshold density</td>\n      <td>Strong, repeatable power (~397–411 W) with high HR; density high (HR stays elevated in recoveries).</td>\n    </tr>\n    <tr>\n      <td><strong>2026-02-07</strong></td>\n      <td>Run: 15.8 km easy</td>\n      <td>Aerobic base</td>\n      <td>Appropriately easy (HR 138) and steady power (305 W).</td>\n    </tr>\n    <tr>\n      <td><strong>2026-02-21</strong></td>\n      <td>Run: 16.33 km easy</td>\n      <td>Aerobic durability</td>\n      <td>Mostly aerobic time in wearable zones; aligns with polarized distribution.</td>\n    </tr>\n    <tr>\n      <td><strong>2026-02-25</strong></td>\n      <td>Ski: 5:52</td>\n      <td>Musculoskeletal endurance</td>\n      <td>Low average HR but likely high leg cost; overlaps with the high-strain window.</td>\n    </tr>\n    <tr>\n      <td><strong>2026-03-02</strong></td>\n      <td>Bike: sweet spot</td>\n      <td>Tempo aerobic support</td>\n      <td>Controlled intensity (IF 0.762), modest HR drift—good durability marker.</td>\n    </tr>\n    <tr>\n      <td><strong>2026-03-04</strong></td>\n      <td>Run: 4×1 km</td>\n      <td>Threshold / aerobic power</td>\n      <td>Consistent rep pace range; power anchor ~400 W remains valid.</td>\n    </tr>\n    <tr>\n      <td><strong>2026-03-05</strong></td>\n      <td>Run: easy + strides</td>\n      <td>Neuromuscular speed</td>\n      <td>High-power surges (~480–493 W) with limited high HR—low systemic cost.</td>\n    </tr>\n  </tbody>\n</table>",
              "key": "key-session-table",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "generic"
            }
          ],
          "children": [],
          "default_open": null,
          "disclosure_mode": "collapsible",
          "node_id": "key-sessions-signal-table",
          "summary": "Compact recap of the highlighted run/bike/ski sessions and what the data suggests.",
          "title": "Key session & signal table (quick reference)",
          "tone": "neutral"
        },
        {
          "blocks": [
            {
              "content_html": "<div class=\"callout-accent\">\n  Across January to early March, your data tells a coherent story: <strong>high capacity</strong> and <strong>good recovery resilience</strong>, tempered by two “watch-outs”—<strong>abrupt load spikes</strong> and <strong>sleep-disruption crashes</strong>. The late-February period functioned as a meaningful reset (TSB strongly positive), and your early-March return to training shows <strong>healthier variability</strong> (low monotony) and <strong>preserved performance proxies</strong> (stable VO₂max, consistent threshold rep execution). The main performance opportunity now is not a single breakthrough workout—it’s maintaining the current <strong>consistency + variability</strong> pattern while respecting the strong link between <strong>sleep quality</strong> and your next-day physiology.\n</div>",
              "key": "closing-paragraph",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "notes"
            }
          ],
          "children": [],
          "default_open": null,
          "disclosure_mode": "inline",
          "node_id": "closing-synthesis",
          "summary": "High capacity + good resilience; watch abrupt spikes and sleep crashes; late-Feb reset preserved fitness; early-Mar reload shows healthier variability.",
          "title": "Closing synthesis",
          "tone": "good"
        }
      ],
      "section_id": "goals-readiness",
      "summary": "VO₂max improved early then held steady through late-Feb downshift; threshold rep consistency supports 10k/5k build; trail/tri outcomes likely hinge on musculoskeletal resilience + controlled load distribution.",
      "title": "Performance trends & readiness relative to goals",
      "tone": "neutral"
    }
  ],
  "type": "analysis",
  "version": 9
},
};
