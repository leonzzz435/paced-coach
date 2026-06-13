import type { DemoPersonaId } from "@/lib/demo/personas";
import type { UiSeasonPlan } from "@/lib/types/ui-blocks";

export const DEMO_SEASON_PLAN_BY_PERSONA: Record<DemoPersonaId, UiSeasonPlan> = {
  "hybrid-operator": {
  "athlete_name": "Demo Athlete",
  "end_date": "2026-10-25",
  "global_blocks": [],
  "global_nodes": [
    {
      "blocks": [
        {
          "content_html": "<div class=\"grid grid--2\">\n  <div class=\"card\">\n    <table class=\"table\">\n      <thead>\n        <tr>\n          <th>Event</th>\n          <th>Date</th>\n          <th>Priority</th>\n          <th>Goal</th>\n        </tr>\n      </thead>\n      <tbody>\n        <tr>\n          <td><strong>Ridge Trail</strong><br><small>trail 38 km</small></td>\n          <td>2026-05-03</td>\n          <td><span class=\"tag tag--a\">A</span></td>\n          <td><strong>sub 4h</strong></td>\n        </tr>\n        <tr>\n          <td><strong>City Road Race</strong><br><small>road 10k</small></td>\n          <td>2026-06-19</td>\n          <td><span class=\"tag tag--a\">A</span></td>\n          <td><strong>44:00</strong></td>\n        </tr>\n        <tr>\n          <td><strong>Summer Triathlon</strong><br><small>Olympic</small></td>\n          <td>2026-08-09</td>\n          <td><span class=\"tag tag--a\">A</span></td>\n          <td><strong>2:25</strong></td>\n        </tr>\n        <tr>\n          <td><strong>Lakeside Half Marathon</strong><br><small>Half Marathon</small></td>\n          <td>2026-10-25</td>\n          <td><span class=\"tag tag--a\">A</span></td>\n          <td><strong>1:40</strong></td>\n        </tr>\n        <tr>\n          <td><strong>Parkrun Corporate Cup</strong><br><small>road 5k</small></td>\n          <td>2026-06-18</td>\n          <td><span class=\"tag tag--b\">B</span></td>\n          <td><strong>21:00</strong></td>\n        </tr>\n      </tbody>\n    </table>\n    <div class=\"callout-info\">\n      <strong>Primary domain:</strong> <span class=\"domain-chip domain-performance\">Performance</span>\n    </div>\n  </div>\n\n  <div class=\"card\">\n    <h3>Season objectives (A-priority peaks)</h3>\n    <ul>\n      <li><strong>Ridge Trail 38 km (A)</strong> — 2026-05-03 (<strong>sub 4h</strong>)</li>\n      <li><strong>City Road Race 10k (A)</strong> — 2026-06-19 (<strong>44:00</strong>)</li>\n      <li><strong>Summer Triathlon (Olympic) (A)</strong> — 2026-08-09 (<strong>2:25</strong>)</li>\n      <li><strong>Lakeside Half Marathon (A)</strong> — 2026-10-25 (<strong>1:40</strong>)</li>\n    </ul>\n    <h3>B-priority tune-up</h3>\n    <p><strong>Parkrun Corporate Cup 5k (B)</strong> — 2026-06-18 (<strong>21:00</strong>)</p>\n  </div>\n</div>",
          "key": "objectives-events-table",
          "title": "A/B events + goal targets",
          "tone": null,
          "type": "html",
          "variant": "generic"
        },
        {
          "content_html": "<div class=\"card\">\n  <table class=\"table\">\n    <thead>\n      <tr>\n        <th>Date</th>\n        <th>Event</th>\n        <th>Priority</th>\n        <th>Strategic role</th>\n      </tr>\n    </thead>\n    <tbody>\n      <tr>\n        <td>2026-05-03</td>\n        <td><strong>Ridge Trail 38 km</strong></td>\n        <td><span class=\"tag tag--a\">A</span></td>\n        <td>Durability + climbing economy benchmark; major fatigue event → structured recovery</td>\n      </tr>\n      <tr>\n        <td>2026-06-18</td>\n        <td><strong>Parkrun Corporate Cup 5k</strong></td>\n        <td><span class=\"tag tag--b\">B</span></td>\n        <td>Sharpening/confidence; <strong>must not</strong> compromise next-day 10k</td>\n      </tr>\n      <tr>\n        <td>2026-06-19</td>\n        <td><strong>City Road Race 10k</strong></td>\n        <td><span class=\"tag tag--a\">A</span></td>\n        <td>Speed endurance + pacing discipline peak</td>\n      </tr>\n      <tr>\n        <td>2026-08-09</td>\n        <td><strong>Summer Triathlon (Olympic)</strong></td>\n        <td><span class=\"tag tag--a\">A</span></td>\n        <td>Multi-sport peak; execution + pacing + fueling</td>\n      </tr>\n      <tr>\n        <td>2026-10-25</td>\n        <td><strong>Lakeside Half Marathon</strong></td>\n        <td><span class=\"tag tag--a\">A</span></td>\n        <td>Late-season run peak; build from tri aerobic base into HM specificity</td>\n      </tr>\n    </tbody>\n  </table>\n</div>",
          "key": "competition-integration-summary-table",
          "title": "Competition integration summary",
          "tone": null,
          "type": "html",
          "variant": "generic"
        }
      ],
      "children": [],
      "default_open": true,
      "disclosure_mode": "collapsible",
      "node_id": "global-objectives",
      "summary": "4× A-priority peaks + 1× B tune-up (2026-03-04 → 2026-10-25)",
      "title": "Season objectives & race calendar",
      "tone": "neutral"
    },
    {
      "blocks": [
        {
          "content_html": "<div class=\"callout-warning\">\n  <strong>Boom–bust load volatility</strong> is the main risk (spikes then abrupt unloading).\n  <ul>\n    <li>Season built around <strong>consistent density</strong> + <strong>controlled ramps</strong>.</li>\n  </ul>\n</div>",
          "key": "nn-1-smooth-load",
          "title": "1) Smooth load > hero days (primary risk)",
          "tone": "warning",
          "type": "html",
          "variant": "callout"
        },
        {
          "content_html": "<div class=\"callout-warning\">\n  <strong>1 bad night</strong> can create <strong>3–5 days</strong> of suppressed recovery.\n  <ul>\n    <li>Plan includes a built-in <strong>“shock absorber”</strong> rule (see Guardrails → Recovery Shock Absorber).</li>\n  </ul>\n</div>",
          "key": "nn-2-sleep-sensitivity",
          "title": "2) Sleep-disruption sensitivity",
          "tone": "warning",
          "type": "html",
          "variant": "callout"
        },
        {
          "content_html": "<div class=\"grid grid--2\">\n  <div class=\"card\">\n    <h3>Keep (proven blocks)</h3>\n    <ul>\n      <li>Long easy aerobic run (~<strong>100 min</strong>)</li>\n      <li>Steady aerobic runs</li>\n      <li>Sweet-spot bike</li>\n      <li>Strides</li>\n    </ul>\n  </div>\n  <div class=\"card\">\n    <h3>Treat as key sessions (high cost)</h3>\n    <ul>\n      <li>Hard <strong>1 km reps</strong></li>\n      <li>Very hard continuous efforts</li>\n    </ul>\n    <div class=\"callout-accent\">\n      <strong>Rule:</strong> these are <em>key sessions</em> — not “medium days.”\n    </div>\n  </div>\n</div>",
          "key": "nn-3-proven-blocks",
          "title": "3) Use proven building blocks; deploy “high-cost” sessions deliberately",
          "tone": null,
          "type": "html",
          "variant": "generic"
        },
        {
          "content_html": "<div class=\"callout-info\">\n  <strong>Device mismatch across sources</strong> can distort load calculations.\n  <ul>\n    <li>Use <strong>consistency + trend</strong> as the primary governor.</li>\n  </ul>\n</div>",
          "key": "nn-4-numbers-directional",
          "title": "4) Numbers are directionally useful, not absolute",
          "tone": "neutral",
          "type": "html",
          "variant": "callout"
        }
      ],
      "children": [],
      "default_open": false,
      "disclosure_mode": "collapsible",
      "node_id": "global-nonnegotiables",
      "summary": "Volatility control, sleep sensitivity, deliberate key sessions, trends > absolutes",
      "title": "Non‑Negotiables (expert signals)",
      "tone": "neutral"
    },
    {
      "blocks": [
        {
          "content_html": "<div class=\"grid grid--2\">\n  <div class=\"card\">\n    <table class=\"table\">\n      <thead>\n        <tr>\n          <th>Intent</th>\n          <th>Target / guardrail</th>\n          <th>Domain</th>\n          <th>Status</th>\n        </tr>\n      </thead>\n      <tbody>\n        <tr>\n          <td><strong>Primary target</strong></td>\n          <td>Rebuild a <strong>sustainable baseline</strong> (recent chronic EWMA ~<strong>85–100</strong>) toward a <strong>stable</strong> higher band; avoid repeating past spike patterns (ACWR uncoupled up to ~<strong>1.6</strong>)</td>\n          <td><span class=\"domain-chip domain-load\">Load</span></td>\n          <td><span class=\"badge badge-accent\">Season driver</span></td>\n        </tr>\n        <tr>\n          <td><strong>Ramp guardrail</strong></td>\n          <td>Build phases: aim ~<strong>+5–8%</strong> week-to-week (rarely up to ~<strong>10%</strong> if sleep/recovery clearly strong); avoid abrupt <strong>±18–21</strong> type swings</td>\n          <td><span class=\"domain-chip domain-load\">Load</span></td>\n          <td><span class=\"badge badge-warn\">Strict</span></td>\n        </tr>\n        <tr>\n          <td><strong>Intensity distribution</strong></td>\n          <td>Mostly aerobic; “quality” is controlled <strong>LT/threshold</strong> (run) + <strong>sweet spot</strong> (bike); short <strong>strides</strong> for neuromuscular sharpness</td>\n          <td><span class=\"domain-chip domain-performance\">Performance</span></td>\n          <td><span class=\"badge badge-info\">Controlled</span></td>\n        </tr>\n      </tbody>\n    </table>\n  </div>\n\n  <div class=\"card\">\n    <h3>Intensity cues</h3>\n    <p>\n      <span class=\"focus focus--endurance\">Aerobic</span>\n      <span class=\"focus focus--threshold\">LT/Threshold</span>\n      <span class=\"focus focus--sweet-spot\">Sweet Spot</span>\n      <span class=\"focus focus--strides\">Strides</span>\n    </p>\n    <div class=\"quote\">Consistency + trend beats chasing single-session hero metrics.</div>\n  </div>\n</div>",
          "key": "macro-load-intensity-intent",
          "title": "Load & intensity intent",
          "tone": null,
          "type": "html",
          "variant": "generic"
        },
        {
          "content_html": "<div class=\"card\">\n  <ul>\n    <li><strong>May 3 trail</strong> drives <strong>durability</strong> + <strong>climbing economy</strong>.</li>\n    <li><strong>June 18–19 race cluster</strong> is <strong>sharpening + peak</strong> for 10k (<strong>protect the A-race</strong>).</li>\n    <li><strong>Aug 9 triathlon</strong> becomes the <strong>mid-season multi-sport peak</strong>.</li>\n    <li><strong>Oct 25 half marathon</strong> is the <strong>late-season run peak</strong>, built off the aerobic base + tri bike fitness.</li>\n  </ul>\n</div>",
          "key": "macro-competition-strategy",
          "title": "Competition strategy (what each peak drives)",
          "tone": null,
          "type": "html",
          "variant": "generic"
        }
      ],
      "children": [],
      "default_open": false,
      "disclosure_mode": "collapsible",
      "node_id": "global-season-architecture",
      "summary": "Sustainable baseline → controlled quality → 4 planned peaks",
      "title": "Season architecture (macro view)",
      "tone": "neutral"
    },
    {
      "blocks": [],
      "children": [
        {
          "blocks": [
            {
              "content_html": "<div class=\"callout-warning\">\n  <p><span class=\"domain-chip domain-load\">Load</span> <strong>Smoothness first</strong></p>\n  <ul>\n    <li>If you miss a day, <strong>do not “pay it back”</strong> with an outsized session.</li>\n    <li>Prefer consistent medium days over alternating huge and zero days.</li>\n    <li>Build phases: generally <strong>+5–8% weekly ramp</strong>; avoid abrupt swings.</li>\n    <li>Use monotony/strain as checks: avoid overly repetitive weeks <em>and</em> extremely erratic ones.</li>\n  </ul>\n</div>",
              "key": "gr-load-bullets",
              "title": null,
              "tone": "warning",
              "type": "html",
              "variant": "callout"
            }
          ],
          "children": [],
          "default_open": true,
          "disclosure_mode": "collapsible",
          "node_id": "guardrails-load-smoothness",
          "summary": "No payback spikes; build +5–8%; avoid erratic and overly monotonous weeks",
          "title": "1) Load Smoothness (primary risk control)",
          "tone": "neutral"
        },
        {
          "blocks": [
            {
              "content_html": "<div class=\"grid grid--2\">\n  <div class=\"card\">\n    <h3>Repeatable threshold rule</h3>\n    <ul>\n      <li>“Threshold/LT” must be <strong>repeatable</strong>; do not turn it into 10k/VO₂ work by default.</li>\n      <li>Practical cap until formally tested: <strong>minimize time above ~175 bpm</strong> (given observed peaks ~<strong>180–182</strong>).</li>\n    </ul>\n  </div>\n  <div class=\"card\">\n    <div class=\"callout-accent\">\n      <strong>Success definition</strong>\n      <ul>\n        <li>Even pacing + more total quality volume over time</li>\n        <li><em>Not</em> the hardest single workout</li>\n      </ul>\n    </div>\n    <p>\n      <span class=\"domain-chip domain-performance\">Performance</span>\n      <span class=\"badge badge-info\">Controlled LT</span>\n    </p>\n  </div>\n</div>",
              "key": "gr-intensity-bullets",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "generic"
            }
          ],
          "children": [],
          "default_open": false,
          "disclosure_mode": "collapsible",
          "node_id": "guardrails-intensity-control",
          "summary": "LT must be repeatable; cap time above ~175 bpm until tested",
          "title": "2) Intensity Control (prevent “threshold drift”)",
          "tone": "neutral"
        },
        {
          "blocks": [
            {
              "content_html": "<div class=\"card\">\n  <p><span class=\"domain-chip domain-recovery\">Recovery</span> <span class=\"domain-chip domain-sleep\">Sleep</span></p>\n  <p><strong>If any occur:</strong></p>\n  <ul>\n    <li>Severe sleep disruption</li>\n    <li>Clear HRV suppression + RHR jump</li>\n    <li>Illness-like signs (elevated respiration/skin temp + fatigue)</li>\n  </ul>\n</div>",
              "key": "gr-shock-absorber-triggers",
              "title": "Trigger conditions",
              "tone": null,
              "type": "html",
              "variant": "generic"
            },
            {
              "content_html": "<div class=\"callout-warning\">\n  <p><strong>For 24–72h:</strong></p>\n  <ul class=\"checklist\">\n    <li>Drop intensity first (easy only or rest)</li>\n    <li>Keep frequency with low cost (walk/spin/swim technique)</li>\n    <li>Resume quality only after metrics + perceived freshness normalize</li>\n  </ul>\n</div>",
              "key": "gr-shock-absorber-24-72h",
              "title": "24–72h protocol",
              "tone": "warning",
              "type": "html",
              "variant": "callout"
            }
          ],
          "children": [],
          "default_open": false,
          "disclosure_mode": "collapsible",
          "node_id": "guardrails-recovery-shock-absorber",
          "summary": "If sleep/HRV/RHR/illness flags: 24–72h intensity drop + low-cost frequency",
          "title": "3) Recovery Shock Absorber (sleep/HRV governor)",
          "tone": "neutral"
        },
        {
          "blocks": [
            {
              "content_html": "<div class=\"callout-warning\">\n  <ul>\n    <li>Trail descents and long vertical (or similar eccentric stress) count as <strong>high muscular cost</strong> even if HR/load underestimates it.</li>\n    <li><strong>Following day:</strong> reduce run impact (swap to bike/swim or easy only).</li>\n  </ul>\n</div>",
              "key": "gr-trail-eccentric",
              "title": null,
              "tone": "warning",
              "type": "html",
              "variant": "callout"
            }
          ],
          "children": [],
          "default_open": false,
          "disclosure_mode": "collapsible",
          "node_id": "guardrails-trail-eccentric",
          "summary": "Descents/vertical = high muscular cost even when HR underestimates",
          "title": "4) Trail & “Hidden Eccentric” fatigue rule",
          "tone": "neutral"
        }
      ],
      "default_open": true,
      "disclosure_mode": "collapsible",
      "node_id": "global-guardrails",
      "summary": "Load smoothness, intensity control, sleep/HRV shock absorber, trail eccentric rule",
      "title": "Global guardrails (apply all season)",
      "tone": "neutral"
    },
    {
      "blocks": [
        {
          "content_html": "<div class=\"card\">\n  <table class=\"table\">\n    <thead>\n      <tr>\n        <th>Checkpoint</th>\n        <th>Expected signal</th>\n        <th>Domain</th>\n        <th>Status</th>\n      </tr>\n    </thead>\n    <tbody>\n      <tr>\n        <td><strong>Late March</strong></td>\n        <td>Routine restored; fewer blank days; baseline trending up</td>\n        <td><span class=\"domain-chip domain-load\">Load</span></td>\n        <td><span class=\"badge badge-info\">Check-in</span></td>\n      </tr>\n      <tr>\n        <td><strong>Mid April</strong></td>\n        <td>Hills + long run feel sustainable; fueling rehearsed</td>\n        <td><span class=\"domain-chip domain-performance\">Performance</span></td>\n        <td><span class=\"badge badge-info\">Check-in</span></td>\n      </tr>\n      <tr>\n        <td><strong>Mid June</strong></td>\n        <td>Workouts controlled; strong 10k pacing discipline</td>\n        <td><span class=\"domain-chip domain-performance\">Performance</span></td>\n        <td><span class=\"badge badge-info\">Check-in</span></td>\n      </tr>\n      <tr>\n        <td><strong>Late July</strong></td>\n        <td>Swim/bike confidence rising; bricks coordinated</td>\n        <td><span class=\"domain-chip domain-performance\">Performance</span></td>\n        <td><span class=\"badge badge-info\">Check-in</span></td>\n      </tr>\n      <tr>\n        <td><strong>Race week Aug 9</strong></td>\n        <td>Freshness obvious; no last-minute load spikes</td>\n        <td><span class=\"domain-chip domain-recovery\">Recovery</span></td>\n        <td><span class=\"badge badge-warn\">Protect</span></td>\n      </tr>\n      <tr>\n        <td><strong>Late Sept</strong></td>\n        <td>Long-run durability + controlled threshold stable</td>\n        <td><span class=\"domain-chip domain-performance\">Performance</span></td>\n        <td><span class=\"badge badge-info\">Check-in</span></td>\n      </tr>\n      <tr>\n        <td><strong>Race week Oct 25</strong></td>\n        <td>Taper protects sleep; HM pacing plan is clear and trusted</td>\n        <td><span class=\"domain-chip domain-sleep\">Sleep</span></td>\n        <td><span class=\"badge badge-warn\">Protect</span></td>\n      </tr>\n    </tbody>\n  </table>\n</div>",
          "key": "simple-checks-table",
          "title": null,
          "tone": null,
          "type": "html",
          "variant": "generic"
        }
      ],
      "children": [],
      "default_open": false,
      "disclosure_mode": "collapsible",
      "node_id": "global-phase-simple-checks",
      "summary": "Late Mar → Mid Apr → Mid Jun → Late Jul → Aug race week → Late Sept → Oct race week",
      "title": "Phase-specific “simple checks” (milestones)",
      "tone": "neutral"
    }
  ],
  "phases": [
    {
      "blocks": [],
      "end_date": "2026-03-29",
      "nodes": [
        {
          "blocks": [
            {
              "content_html": "<div class=\"grid grid--2\">\n  <div class=\"card\">\n    <p><strong>Restore training rhythm</strong>; rebuild baseline with minimal volatility; re-establish <em>easy means easy</em>.</p>\n    <p>\n      <span class=\"focus focus--easy\">Easy</span>\n      <span class=\"focus focus--aerobic\">Aerobic base</span>\n      <span class=\"focus focus--threshold\">Controlled LT/threshold</span>\n      <span class=\"focus focus--sweet-spot\">Sweet spot (bike)</span>\n      <span class=\"focus focus--strength\">Strength</span>\n    </p>\n  </div>\n  <div class=\"card\">\n    <div class=\"callout-accent\">\n      <strong>Key constraint</strong>\n      <ul>\n        <li><strong>2 key stimuli/week max</strong> (e.g., 1 controlled LT/threshold run + 1 sweet-spot bike)</li>\n      </ul>\n    </div>\n  </div>\n</div>",
              "key": "p1-focus",
              "title": "Focus",
              "tone": null,
              "type": "html",
              "variant": "generic"
            },
            {
              "content_html": "<div class=\"card\">\n  <ul>\n    <li>Stable weekly training density (reduce “zeros”).</li>\n    <li>Reintroduce <strong>2 key stimuli/week max</strong> (e.g., 1 controlled LT/threshold run + 1 sweet-spot bike).</li>\n    <li>Strength/tissue capacity <strong>2×/week</strong> (feet/calves, posterior chain, eccentric tolerance).</li>\n  </ul>\n</div>",
              "key": "p1-key-goals",
              "title": "Key goals",
              "tone": null,
              "type": "html",
              "variant": "generic"
            },
            {
              "content_html": "<div class=\"card\">\n  <ul>\n    <li>Weekly load trends upward smoothly (<strong>no single-day “load bombs”</strong>).</li>\n    <li>Long easy run feels repeatable with minimal next-day soreness.</li>\n    <li>Threshold work stays controlled (<strong>little time above your cap</strong>).</li>\n  </ul>\n</div>",
              "key": "p1-success-markers",
              "title": "Success markers",
              "tone": null,
              "type": "html",
              "variant": "generic"
            }
          ],
          "children": [],
          "default_open": true,
          "disclosure_mode": "collapsible",
          "node_id": "p1-overview",
          "summary": "Reduce volatility; 2 key stimuli/week max; strength/tissue capacity 2×/week",
          "title": "Overview",
          "tone": "neutral"
        }
      ],
      "phase_id": "phase-rebuild-1",
      "start_date": "2026-03-04",
      "summary": "Restore rhythm, rebuild baseline smoothly, and re-establish “easy means easy.”",
      "title": "Phase 1 — Rebuild Consistency + Aerobic Foundation"
    },
    {
      "blocks": [],
      "end_date": "2026-04-19",
      "nodes": [
        {
          "blocks": [
            {
              "content_html": "<div class=\"grid grid--2\">\n  <div class=\"card\">\n    <p><strong>Rolling climbs</strong>, repeated ascents, downhill tolerance, late-race fatigue resistance for Ridge Trail.</p>\n    <p>\n      <span class=\"focus focus--trail\">Trail</span>\n      <span class=\"focus focus--hills\">Hills</span>\n      <span class=\"focus focus--endurance\">Endurance</span>\n      <span class=\"focus focus--fueling\">Fueling practice</span>\n    </p>\n  </div>\n  <div class=\"card\">\n    <div class=\"callout-warning\">\n      <strong>Eccentric cost awareness</strong>\n      <p>Downhills/uneven terrain can be high muscular cost even if HR/load looks modest.</p>\n    </div>\n  </div>\n</div>",
              "key": "p2-focus",
              "title": "Focus",
              "tone": null,
              "type": "html",
              "variant": "generic"
            },
            {
              "content_html": "<div class=\"card\">\n  <ul>\n    <li>Long run becomes trail-specific (rolling elevation, hike-run strategy).</li>\n    <li>1 weekly “trail-strength” stimulus (hill reps or sustained uphill tempo at controlled effort).</li>\n    <li>Begin <strong>fueling practice</strong> (carbs/fluids/sodium) on longer sessions.</li>\n  </ul>\n</div>",
              "key": "p2-key-goals",
              "title": "Key goals",
              "tone": null,
              "type": "html",
              "variant": "generic"
            },
            {
              "content_html": "<div class=\"card\">\n  <ul>\n    <li>Better control on climbs (less HR “ceiling hits”).</li>\n    <li>Downhill/uneven terrain soreness is manageable and clears quickly.</li>\n    <li>Fueling plan tested multiple times.</li>\n  </ul>\n</div>",
              "key": "p2-success-markers",
              "title": "Success markers",
              "tone": null,
              "type": "html",
              "variant": "generic"
            }
          ],
          "children": [],
          "default_open": true,
          "disclosure_mode": "collapsible",
          "node_id": "p2-overview",
          "summary": "Rolling climbs + repeated ascents; trail-specific long run; fueling practice starts",
          "title": "Overview",
          "tone": "neutral"
        }
      ],
      "phase_id": "phase-trail-build-1",
      "start_date": "2026-03-30",
      "summary": "Build trail durability, climbing economy, downhill tolerance, and begin fueling practice.",
      "title": "Phase 2 — Trail-Specific Build (Durability + Climbing Economy)"
    },
    {
      "blocks": [],
      "end_date": "2026-05-03",
      "nodes": [
        {
          "blocks": [
            {
              "content_html": "<div class=\"grid grid--2\">\n  <div class=\"card\">\n    <p><strong>Arrive fresh with trail legs</strong>; reduce volume while maintaining short controlled intensity.</p>\n    <p>\n      <span class=\"focus focus--taper\">Taper</span>\n      <span class=\"focus focus--trail\">Trail legs</span>\n      <span class=\"focus focus--controlled\">Controlled intensity</span>\n    </p>\n  </div>\n  <div class=\"card\">\n    <div class=\"callout-warning\">\n      <strong>Anti-pattern to avoid</strong>\n      <p>No last-minute spike to “prove fitness.”</p>\n    </div>\n  </div>\n</div>",
              "key": "p3-focus",
              "title": "Focus",
              "tone": null,
              "type": "html",
              "variant": "generic"
            },
            {
              "content_html": "<div class=\"card\">\n  <table class=\"table\">\n    <thead><tr><th>Date</th><th>Event</th><th>Priority</th><th>Goal</th></tr></thead>\n    <tbody>\n      <tr>\n        <td>2026-05-03</td>\n        <td><strong>Ridge Trail</strong><br><small>38 km</small></td>\n        <td><span class=\"tag tag--a\">A</span></td>\n        <td>sub 4h</td>\n      </tr>\n    </tbody>\n  </table>\n</div>",
              "key": "p3-race",
              "title": "Competition integration (A)",
              "tone": null,
              "type": "html",
              "variant": "generic"
            },
            {
              "content_html": "<div class=\"card\">\n  <ul>\n    <li>Sleep stable in the final <strong>10 days</strong>.</li>\n    <li>Legs feel springy; no last-minute spike to “prove fitness.”</li>\n  </ul>\n</div>",
              "key": "p3-success-markers",
              "title": "Success markers",
              "tone": null,
              "type": "html",
              "variant": "generic"
            }
          ],
          "children": [],
          "default_open": true,
          "disclosure_mode": "collapsible",
          "node_id": "p3-overview",
          "summary": "Fresh trail legs; volume down, intensity short/controlled",
          "title": "Overview",
          "tone": "neutral"
        }
      ],
      "phase_id": "phase-trail-peak-1",
      "start_date": "2026-04-20",
      "summary": "Reduce volume, keep short controlled intensity, and arrive fresh for Ridge Trail.",
      "title": "Phase 3 — Trail Peak + Taper"
    },
    {
      "blocks": [],
      "end_date": "2026-05-24",
      "nodes": [
        {
          "blocks": [
            {
              "content_html": "<div class=\"card\">\n  <p><strong>Absorb trail fatigue</strong>, then pivot toward <strong>10k performance</strong> while preserving durability.</p>\n  <p>\n    <span class=\"focus focus--recovery\">Reset</span>\n    <span class=\"focus focus--10k\">10k rebuild</span>\n    <span class=\"focus focus--aerobic\">Aerobic support</span>\n    <span class=\"focus focus--swim-drills\">Swim technique-first</span>\n  </p>\n</div>",
              "key": "p4-focus",
              "title": "Focus",
              "tone": null,
              "type": "html",
              "variant": "generic"
            },
            {
              "content_html": "<div class=\"card\">\n  <ul>\n    <li><strong>Week 1:</strong> restore (low intensity; re-establish normal sleep, low-cost movement).</li>\n    <li><strong>Weeks 2–3:</strong> reintroduce run quality gradually (10k-oriented, controlled), keep long run steady.</li>\n    <li>Start/raise swim frequency if it has been inconsistent (<strong>technique-first</strong>).</li>\n  </ul>\n</div>",
              "key": "p4-key-goals",
              "title": "Key goals (by week)",
              "tone": null,
              "type": "html",
              "variant": "generic"
            },
            {
              "content_html": "<div class=\"card\">\n  <ul>\n    <li>You rebound within ~<strong>7–10 days</strong> (no multi-week slump).</li>\n    <li>Reps can be executed evenly (no early overcooking).</li>\n  </ul>\n</div>",
              "key": "p4-success-markers",
              "title": "Success markers",
              "tone": null,
              "type": "html",
              "variant": "generic"
            }
          ],
          "children": [],
          "default_open": true,
          "disclosure_mode": "collapsible",
          "node_id": "p4-overview",
          "summary": "Week 1 restore; weeks 2–3 gradual 10k quality; steady long run; swim frequency up if needed",
          "title": "Overview",
          "tone": "neutral"
        }
      ],
      "phase_id": "phase-reset-10k-1",
      "start_date": "2026-05-04",
      "summary": "Absorb trail fatigue, then pivot into controlled 10k-oriented quality while keeping durability.",
      "title": "Phase 4 — Post‑Trail Reset → 10k Rebuild"
    },
    {
      "blocks": [],
      "end_date": "2026-06-21",
      "nodes": [
        {
          "blocks": [
            {
              "content_html": "<div class=\"grid grid--2\">\n  <div class=\"card\">\n    <p><strong>Sharpen speed endurance</strong> and <strong>pacing discipline</strong>; use 5k as tune-up without compromising the 10k.</p>\n    <p>\n      <span class=\"focus focus--10k\">10k specificity</span>\n      <span class=\"focus focus--threshold\">LT support</span>\n      <span class=\"focus focus--speed-endurance\">Speed endurance</span>\n      <span class=\"focus focus--aerobic\">Aerobic</span>\n    </p>\n  </div>\n  <div class=\"card\">\n    <div class=\"callout-warning\">\n      <strong>Protection window</strong>\n      <p>Bike stays supportive but doesn’t compromise run sharpness in the last <strong>10–12 days</strong>.</p>\n    </div>\n  </div>\n</div>",
              "key": "p5-focus",
              "title": "Focus",
              "tone": null,
              "type": "html",
              "variant": "generic"
            },
            {
              "content_html": "<div class=\"card\">\n  <table class=\"table\">\n    <thead><tr><th>Date</th><th>Event</th><th>Priority</th><th>Role</th></tr></thead>\n    <tbody>\n      <tr>\n        <td>2026-06-18</td>\n        <td><strong>Parkrun Corporate Cup</strong><br><small>5k</small></td>\n        <td><span class=\"tag tag--b\">B</span></td>\n        <td>Sharpening effort; <strong>protect recovery</strong></td>\n      </tr>\n      <tr>\n        <td>2026-06-19</td>\n        <td><strong>City Road Race</strong><br><small>10k</small></td>\n        <td><span class=\"tag tag--a\">A</span></td>\n        <td>Season run-peak #1</td>\n      </tr>\n    </tbody>\n  </table>\n</div>",
              "key": "p5-competition-integration",
              "title": "Competition integration (race cluster)",
              "tone": null,
              "type": "html",
              "variant": "generic"
            },
            {
              "content_html": "<div class=\"card\">\n  <ul>\n    <li><strong>1–2 run-quality sessions/week</strong> (10k pace tolerance + LT support), everything else aerobic.</li>\n    <li>Bike stays supportive but doesn’t compromise run sharpness in the last <strong>10–12 days</strong>.</li>\n  </ul>\n</div>",
              "key": "p5-key-goals",
              "title": "Key goals",
              "tone": null,
              "type": "html",
              "variant": "generic"
            },
            {
              "content_html": "<div class=\"card\">\n  <ul>\n    <li>5k feels like <strong>“priming”</strong>, not a teardown.</li>\n    <li>10k: controlled early pacing; strong last third.</li>\n  </ul>\n</div>",
              "key": "p5-success-markers",
              "title": "Success markers",
              "tone": null,
              "type": "html",
              "variant": "generic"
            }
          ],
          "children": [],
          "default_open": true,
          "disclosure_mode": "collapsible",
          "node_id": "p5-overview",
          "summary": "1–2 run-quality/week; everything else aerobic; bike supports but doesn’t compromise last 10–12 days",
          "title": "Overview",
          "tone": "neutral"
        }
      ],
      "phase_id": "phase-10k-peak-1",
      "start_date": "2026-05-25",
      "summary": "Sharpen speed endurance and pacing discipline; use 5k as priming for the 10k A-race.",
      "title": "Phase 5 — 10k Peak + Race Cluster"
    },
    {
      "blocks": [],
      "end_date": "2026-07-19",
      "nodes": [
        {
          "blocks": [
            {
              "content_html": "<div class=\"card\">\n  <p><strong>Shift from run peak to tri-specific fitness</strong>; bike + swim become co-equal drivers.</p>\n  <p>\n    <span class=\"focus focus--swim\">Swim</span>\n    <span class=\"focus focus--bike-endurance\">Bike endurance</span>\n    <span class=\"focus focus--sweet-spot\">Sweet spot</span>\n    <span class=\"focus focus--brick\">Bricks (light)</span>\n    <span class=\"focus focus--run-maintenance\">Run maintenance</span>\n  </p>\n</div>",
              "key": "p6-focus",
              "title": "Focus",
              "tone": null,
              "type": "html",
              "variant": "generic"
            },
            {
              "content_html": "<div class=\"grid grid--2\">\n  <div class=\"card\">\n    <h3>Swim</h3>\n    <ul>\n      <li>Consistent frequency; technique + aerobic endurance.</li>\n      <li>Introduce open-water skills when possible.</li>\n    </ul>\n  </div>\n  <div class=\"card\">\n    <h3>Bike</h3>\n    <ul>\n      <li>Build durable aerobic power (sweet spot + longer steady endurance).</li>\n    </ul>\n    <h3>Run</h3>\n    <ul>\n      <li>Maintain with <strong>1 quality touch/week</strong> + <strong>1 longer aerobic run</strong>; add light bricks.</li>\n    </ul>\n  </div>\n</div>",
              "key": "p6-key-goals",
              "title": "Key goals",
              "tone": null,
              "type": "html",
              "variant": "generic"
            },
            {
              "content_html": "<div class=\"card\">\n  <ul>\n    <li>Swim stops feeling like “restarting” each week.</li>\n    <li>Bike pacing steadier (less surging); bricks feel coordinated.</li>\n    <li>Fatigue stable; no return to spike/zero pattern.</li>\n  </ul>\n</div>",
              "key": "p6-success-markers",
              "title": "Success markers",
              "tone": null,
              "type": "html",
              "variant": "generic"
            }
          ],
          "children": [],
          "default_open": true,
          "disclosure_mode": "collapsible",
          "node_id": "p6-overview",
          "summary": "Swim frequency + technique; bike aerobic power (sweet spot + endurance); run 1 quality touch + long run; light bricks",
          "title": "Overview",
          "tone": "neutral"
        }
      ],
      "phase_id": "phase-tri-base-1",
      "start_date": "2026-06-22",
      "summary": "Shift from run peak to tri fitness: swim and bike become co-equal drivers while run maintains.",
      "title": "Phase 6 — Triathlon Base/Build 1 (Rebalance to Swim/Bike)"
    },
    {
      "blocks": [],
      "end_date": "2026-08-09",
      "nodes": [
        {
          "blocks": [
            {
              "content_html": "<div class=\"grid grid--2\">\n  <div class=\"card\">\n    <p><strong>Race-specific execution</strong>, pacing discipline, transitions; arrive fresh.</p>\n    <p>\n      <span class=\"focus focus--race-specific\">Race-specific</span>\n      <span class=\"focus focus--brick\">Bricks (controlled)</span>\n      <span class=\"focus focus--open-water\">Open-water</span>\n      <span class=\"focus focus--taper\">Taper</span>\n      <span class=\"focus focus--fueling\">Nutrition/hydration rehearsal</span>\n    </p>\n  </div>\n  <div class=\"card\">\n    <div class=\"callout-warning\">\n      <strong>Taper window</strong>\n      <p>Taper ~<strong>7–10 days</strong> depending on fatigue/sleep stability.</p>\n    </div>\n  </div>\n</div>",
              "key": "p7-focus",
              "title": "Focus",
              "tone": null,
              "type": "html",
              "variant": "generic"
            },
            {
              "content_html": "<div class=\"card\">\n  <table class=\"table\">\n    <thead><tr><th>Date</th><th>Event</th><th>Priority</th><th>Goal</th></tr></thead>\n    <tbody>\n      <tr>\n        <td>2026-08-09</td>\n        <td><strong>Summer Triathlon</strong><br><small>Olympic</small></td>\n        <td><span class=\"tag tag--a\">A</span></td>\n        <td>2:25</td>\n      </tr>\n    </tbody>\n  </table>\n</div>",
              "key": "p7-race",
              "title": "Competition integration (A)",
              "tone": null,
              "type": "html",
              "variant": "generic"
            },
            {
              "content_html": "<div class=\"card\">\n  <ul>\n    <li>Race-specific bricks (controlled), pacing rehearsals, nutrition/hydration rehearsal.</li>\n    <li>Open-water practice (sighting, starts, pack comfort).</li>\n    <li>Taper ~<strong>7–10 days</strong> depending on fatigue/sleep stability.</li>\n  </ul>\n</div>",
              "key": "p7-key-goals",
              "title": "Key goals",
              "tone": null,
              "type": "html",
              "variant": "generic"
            },
            {
              "content_html": "<div class=\"card\">\n  <ul>\n    <li>Clear pacing plan: disciplined bike to enable a strong 10k.</li>\n    <li>Sleep + HRV/RHR stabilize race week; no “panic training.”</li>\n  </ul>\n</div>",
              "key": "p7-success-markers",
              "title": "Success markers",
              "tone": null,
              "type": "html",
              "variant": "generic"
            }
          ],
          "children": [],
          "default_open": true,
          "disclosure_mode": "collapsible",
          "node_id": "p7-overview",
          "summary": "Race-specific bricks + rehearsals; open-water practice; taper guided by fatigue/sleep",
          "title": "Overview",
          "tone": "neutral"
        }
      ],
      "phase_id": "phase-tri-peak-1",
      "start_date": "2026-07-20",
      "summary": "Race-specific execution, transitions, and pacing; taper ~7–10 days to arrive fresh for the Olympic triathlon.",
      "title": "Phase 7 — Triathlon Build 2 + Peak/Taper"
    },
    {
      "blocks": [],
      "end_date": "2026-08-23",
      "nodes": [
        {
          "blocks": [
            {
              "content_html": "<div class=\"card\">\n  <p><strong>Absorb tri peak</strong>; maintain movement while letting freshness return; gently re-prioritize running.</p>\n  <p>\n    <span class=\"focus focus--recovery\">Recovery</span>\n    <span class=\"focus focus--low-impact\">Low impact</span>\n    <span class=\"focus focus--run-reentry\">Run re-entry</span>\n  </p>\n</div>",
              "key": "p8-focus",
              "title": "Focus",
              "tone": null,
              "type": "html",
              "variant": "generic"
            },
            {
              "content_html": "<div class=\"card\">\n  <ul>\n    <li>Reduce intensity and impact; keep frequency with low-cost sessions.</li>\n    <li>Short reintroduction of strides / light uptempo only if recovery is clearly good.</li>\n    <li>Identify any niggles from tri block (calf/foot/hip) before HM build.</li>\n  </ul>\n</div>",
              "key": "p8-key-goals",
              "title": "Key goals",
              "tone": null,
              "type": "html",
              "variant": "generic"
            },
            {
              "content_html": "<div class=\"card\">\n  <ul>\n    <li>Appetite, mood, and sleep normalize.</li>\n    <li>Running feels mechanically smooth again.</li>\n  </ul>\n</div>",
              "key": "p8-success-markers",
              "title": "Success markers",
              "tone": null,
              "type": "html",
              "variant": "generic"
            }
          ],
          "children": [],
          "default_open": true,
          "disclosure_mode": "collapsible",
          "node_id": "p8-overview",
          "summary": "Reduce intensity/impact; strides only if clearly recovered; identify niggles before HM build",
          "title": "Overview",
          "tone": "neutral"
        }
      ],
      "phase_id": "phase-post-tri-1",
      "start_date": "2026-08-10",
      "summary": "Absorb the tri peak, keep low-cost movement, and gently re-prioritize running for the HM build.",
      "title": "Phase 8 — Post‑Tri Transition + Reset (Absorb + Reorient)"
    },
    {
      "blocks": [],
      "end_date": "2026-09-27",
      "nodes": [
        {
          "blocks": [
            {
              "content_html": "<div class=\"grid grid--2\">\n  <div class=\"card\">\n    <p><strong>Convert tri aerobic fitness into HM-specific durability</strong>; build long-run robustness + controlled threshold.</p>\n    <p>\n      <span class=\"focus focus--half-marathon\">HM build</span>\n      <span class=\"focus focus--long-run\">Long run progression</span>\n      <span class=\"focus focus--tempo\">Tempo</span>\n      <span class=\"focus focus--threshold\">Controlled LT</span>\n      <span class=\"focus focus--strides\">Strides</span>\n    </p>\n  </div>\n  <div class=\"card\">\n    <div class=\"callout-info\">\n      <strong>Supportive cross-training rule</strong>\n      <p>Keep bike/swim as <strong>supportive aerobic volume</strong> + recovery tools (low impact), not as fatigue multipliers.</p>\n    </div>\n  </div>\n</div>",
              "key": "p9-focus",
              "title": "Focus",
              "tone": null,
              "type": "html",
              "variant": "generic"
            },
            {
              "content_html": "<div class=\"card\">\n  <ul>\n    <li>Progress long run (duration and/or steady-state quality) without big spikes.</li>\n    <li>Weekly LT/tempo stimulus (controlled, repeatable), plus strides.</li>\n    <li>Keep bike/swim as <strong>supportive aerobic volume</strong> and recovery tools (low impact), not as fatigue multipliers.</li>\n  </ul>\n</div>",
              "key": "p9-key-goals",
              "title": "Key goals",
              "tone": null,
              "type": "html",
              "variant": "generic"
            },
            {
              "content_html": "<div class=\"card\">\n  <ul>\n    <li>Long run recovery is predictable (ready to train well again within <strong>24–48h</strong>).</li>\n    <li>Threshold sessions stay controlled (no drift into “race every week”).</li>\n  </ul>\n</div>",
              "key": "p9-success-markers",
              "title": "Success markers",
              "tone": null,
              "type": "html",
              "variant": "generic"
            }
          ],
          "children": [],
          "default_open": true,
          "disclosure_mode": "collapsible",
          "node_id": "p9-overview",
          "summary": "Long run progression without spikes; weekly LT/tempo + strides; bike/swim supportive (not fatigue multipliers)",
          "title": "Overview",
          "tone": "neutral"
        }
      ],
      "phase_id": "phase-hm-build-1",
      "start_date": "2026-08-24",
      "summary": "Convert tri aerobic fitness into HM durability: progress the long run and repeatable controlled threshold.",
      "title": "Phase 9 — Half Marathon Base/Build (Aerobic Power + Long Run Progression)"
    },
    {
      "blocks": [],
      "end_date": "2026-10-11",
      "nodes": [
        {
          "blocks": [
            {
              "content_html": "<div class=\"grid grid--2\">\n  <div class=\"card\">\n    <p><strong>Sharpen HM pace economy</strong> and pacing execution while maintaining durability.</p>\n    <p>\n      <span class=\"focus focus--race-pace\">HM pace</span>\n      <span class=\"focus focus--economy\">Economy</span>\n      <span class=\"focus focus--durability\">Durability</span>\n      <span class=\"focus focus--stable-load\">Stable stress</span>\n    </p>\n  </div>\n  <div class=\"card\">\n    <div class=\"callout-warning\">\n      <strong>Key warning</strong>\n      <p>Avoid late build panic (no “last-minute build” spikes).</p>\n    </div>\n  </div>\n</div>",
              "key": "p10-focus",
              "title": "Focus",
              "tone": null,
              "type": "html",
              "variant": "generic"
            },
            {
              "content_html": "<div class=\"card\">\n  <ul>\n    <li>Specificity: HM-paced work integrated in a fatigue-managed way.</li>\n    <li>Keep overall weekly stress stable (avoid late build panic).</li>\n  </ul>\n</div>",
              "key": "p10-key-goals",
              "title": "Key goals",
              "tone": null,
              "type": "html",
              "variant": "generic"
            },
            {
              "content_html": "<div class=\"card\">\n  <ul>\n    <li>HM-pace efforts feel smooth and rhythm-based.</li>\n    <li>No deterioration in sleep/recovery trends.</li>\n  </ul>\n</div>",
              "key": "p10-success-markers",
              "title": "Success markers",
              "tone": null,
              "type": "html",
              "variant": "generic"
            }
          ],
          "children": [],
          "default_open": true,
          "disclosure_mode": "collapsible",
          "node_id": "p10-overview",
          "summary": "HM-paced work in fatigue-managed doses; keep weekly stress stable",
          "title": "Overview",
          "tone": "neutral"
        }
      ],
      "phase_id": "phase-hm-sharpen-1",
      "start_date": "2026-09-28",
      "summary": "Integrate HM-pace work with stable weekly stress; sharpen economy and execution without late-build panic.",
      "title": "Phase 10 — Half Marathon Specific Sharpen (Race Pace Economy)"
    },
    {
      "blocks": [],
      "end_date": "2026-10-25",
      "nodes": [
        {
          "blocks": [
            {
              "content_html": "<div class=\"grid grid--2\">\n  <div class=\"card\">\n    <p><strong>Reduce volume</strong>, keep short intensity touches; arrive fresh and confident.</p>\n    <p>\n      <span class=\"focus focus--taper\">Taper</span>\n      <span class=\"focus focus--freshness\">Freshness</span>\n      <span class=\"focus focus--sleep-protection\">Sleep protection</span>\n      <span class=\"focus focus--race-execution\">Execution</span>\n    </p>\n  </div>\n  <div class=\"card\">\n    <div class=\"callout-accent\">\n      <strong>Execution cue</strong>\n      <p>Pacing plan is conservative early, assertive late (supports <strong>1:40</strong> goal).</p>\n    </div>\n  </div>\n</div>",
              "key": "p11-focus",
              "title": "Focus",
              "tone": null,
              "type": "html",
              "variant": "generic"
            },
            {
              "content_html": "<div class=\"card\">\n  <table class=\"table\">\n    <thead><tr><th>Date</th><th>Event</th><th>Priority</th><th>Goal</th></tr></thead>\n    <tbody>\n      <tr>\n        <td>2026-10-25</td>\n        <td><strong>Lakeside Half Marathon</strong><br><small>Half Marathon</small></td>\n        <td><span class=\"tag tag--a\">A</span></td>\n        <td>1:40</td>\n      </tr>\n    </tbody>\n  </table>\n</div>",
              "key": "p11-race",
              "title": "Competition integration (A)",
              "tone": null,
              "type": "html",
              "variant": "generic"
            },
            {
              "content_html": "<div class=\"card\">\n  <ul>\n    <li>Fresh legs + stable sleep in final week.</li>\n    <li>Pacing plan is conservative early, assertive late (supports 1:40 goal).</li>\n  </ul>\n</div>",
              "key": "p11-success-markers",
              "title": "Success markers",
              "tone": null,
              "type": "html",
              "variant": "generic"
            }
          ],
          "children": [],
          "default_open": true,
          "disclosure_mode": "collapsible",
          "node_id": "p11-overview",
          "summary": "Volume down; short intensity touches; freshness + sleep protected",
          "title": "Overview",
          "tone": "neutral"
        }
      ],
      "phase_id": "phase-hm-taper-1",
      "start_date": "2026-10-12",
      "summary": "Reduce volume, keep short intensity touches, and arrive fresh with a trusted pacing plan for the HM A-race.",
      "title": "Phase 11 — Half Marathon Taper + Peak"
    }
  ],
  "plan_id": "demo_season_plan_hybrid_operator",
  "schema_version": 1,
  "season_summary_line": "Mar–Oct 2026 · 4×A peaks (Trail/10k/Oly Tri/HM) · smooth ramps",
  "start_date": "2026-03-04",
  "type": "season_plan",
  "version": 8
},
};
