import type { DemoPersonaId } from "@/lib/demo/personas";
import type { UiWeeklyPlan } from "@/lib/types/ui-blocks";

export const DEMO_WEEKLY_PLAN_BY_PERSONA: Record<DemoPersonaId, UiWeeklyPlan> = {
  "hybrid-operator": {
  "athlete_name": "Demo Athlete",
  "created_at": "2026-03-05T21:42:44.555591",
  "plan_brief": "Steady rebuild phase. Two quality sessions per week — one LT run and one sweet-spot bike. Keep everything else easy and protect your sleep.",
  "global_blocks": [],
  "global_nodes": [
    {
      "blocks": [
        {
          "content_html": "<div class=\"grid grid--2\"><div class=\"card\"><div class=\"big-stat-value\">28 days</div><div class=\"big-stat-label\">Plan window</div><div class=\"big-stat-label\">2026-03-06 → 2026-04-02</div></div><div class=\"card\"><div class=\"big-stat-value\">~2</div><div class=\"big-stat-label\">Key stimuli / week (max)</div><div class=\"big-stat-label\">LT run + sweet-spot bike</div></div></div>",
          "key": "global-snapshot-meta",
          "title": null,
          "tone": null,
          "type": "html",
          "variant": "support"
        },
        {
          "content_html": "<div class=\"manifest-card\"><strong>Weekly structure</strong><ul><li><strong>Key sessions:</strong> ~2/wk max (1 controlled LT run + 1 sweet-spot bike)</li><li><strong>Long run:</strong> 1x long easy run (repeatable)</li><li><strong>Strength (tissue capacity):</strong> 2x micro-dose (calves/feet + posterior chain)</li></ul></div>",
          "key": "global-structure",
          "title": null,
          "tone": null,
          "type": "html",
          "variant": "support"
        }
      ],
      "children": [],
      "default_open": null,
      "disclosure_mode": "inline",
      "node_id": "global-plan-snapshot",
      "summary": "Phase 1 rebuild consistency; Phase 2 begins Mon 2026-03-30 (trail durability + climbing economy)",
      "title": "Plan snapshot (2026-03-06→2026-04-02)",
      "tone": "neutral"
    },
    {
      "blocks": [
        {
          "content_html": "<div class=\"callout-warning\"><strong>Rule:</strong> if sleep was poor <em>or</em> RHR is elevated, <strong>drop intensity for 24–72h</strong> (Z1–Z2 only). Resume quality only when you feel “springy” again.</div>",
          "key": "global-readiness-callout",
          "title": null,
          "tone": "warning",
          "type": "html",
          "variant": "callout"
        },
        {
          "content_html": "<div class=\"quote\">Protect consistency: keep frequency, reduce stress. No “payback” workouts.</div>",
          "key": "global-readiness-principle",
          "title": null,
          "tone": null,
          "type": "html",
          "variant": "support"
        }
      ],
      "children": [],
      "default_open": true,
      "disclosure_mode": "collapsible",
      "node_id": "global-readiness",
      "summary": "Poor sleep or elevated RHR → drop intensity 24–72h (Z1–Z2 only)",
      "title": "Shock absorber rule (sleep/HRV “yellow/red”)",
      "tone": "warning"
    },
    {
      "blocks": [
        {
          "content_html": "<table class=\"table\"><thead><tr><th>Session</th><th>Target</th><th>Domain</th><th>Cue</th></tr></thead><tbody><tr><td><strong>Run Z2 (easy)</strong></td><td>~295–310 W</td><td><span class=\"domain-chip domain-performance\">Performance</span></td><td>HR typically <strong>&lt;145</strong> on flat</td></tr><tr><td><strong>Run LT / Threshold (controlled)</strong></td><td>~390–415 W</td><td><span class=\"domain-chip domain-performance\">Performance</span></td><td>Keep most work <strong>≤175 bpm</strong>; avoid drifting <strong>&gt;180</strong> early</td></tr><tr><td><strong>Bike sweet spot</strong></td><td>~210–218 W</td><td><span class=\"domain-chip domain-performance\">Performance</span></td><td>≈88–92% FTP 237; “comfortably hard”</td></tr><tr><td><strong>Strides</strong></td><td>10–20s fast</td><td><span class=\"domain-chip domain-performance\">Performance</span></td><td>Full control; stop if form degrades</td></tr></tbody></table>",
          "key": "global-zones-table",
          "title": null,
          "tone": null,
          "type": "html",
          "variant": "support"
        }
      ],
      "children": [],
      "default_open": null,
      "disclosure_mode": "collapsible",
      "node_id": "global-zones",
      "summary": "Run Z2 295–310W (HR <145 flat); LT 390–415W (≤175 bpm); Bike SS 210–218W; Strides 10–20s",
      "title": "Zone / cue quick guide",
      "tone": "neutral"
    },
    {
      "blocks": [
        {
          "content_html": "<ul class=\"checklist\"><li><strong>Easy days truly easy:</strong> run easy power ~<strong>295–310 W</strong>; if HR drifts high at same power, <strong>back off</strong>.</li><li><strong>Quality stays controlled:</strong> don’t turn LT into VO₂—keep recoveries easy; prevent early HR spikes.</li><li><strong>No “payback” workouts:</strong> missed day → resume plan; don’t stack extra volume.</li></ul>",
          "key": "global-checks",
          "title": null,
          "tone": null,
          "type": "html",
          "variant": "support"
        }
      ],
      "children": [],
      "default_open": null,
      "disclosure_mode": "collapsible",
      "node_id": "global-ongoing-checks",
      "summary": "Easy days truly easy; quality stays controlled; no stacking missed volume",
      "title": "Ongoing checks (fast scan)",
      "tone": "neutral"
    }
  ],
  "plan_id": "demo_weekly_plan_hybrid_operator",
  "schema_version": 1,
  "type": "weekly_plan",
  "version": 11,
  "weeks": [
    {
      "days": [
        {
          "blocks": [
            {
              "content_html": "<div class=\"workout\"><div class=\"workout-title\">Controlled aerobic ride + tiny tempo taste <span class=\"focus focus--endurance\">Endurance</span></div><div class=\"workout-meta\">bike . 60–70min . Z2 with 2×8min upper Z3</div></div>",
              "key": "2026-03-06-workout",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "workout"
            },
            {
              "content_html": "<ul class=\"checklist task--bike\"><li>10–15min easy warm-up (Z1–low Z2)</li><li>2 × 8min @ <strong>upper Z3 / tempo</strong> (RPE ~6/10; should feel like you could do a 3rd)</li><li>5min very easy between reps</li><li>Easy cool-down to 60–70min total</li><li><strong>Cap:</strong> if HR is stubbornly high, legs feel hollow, or you feel any illness “heaviness” → skip tempo and ride steady Z2</li></ul><ul class=\"checklist task--mobility\"><li>Optional: 8–10min mobility (hips + ankles + T-spine)</li></ul>",
              "key": "2026-03-06-checklist",
              "title": "Execution",
              "tone": null,
              "type": "html",
              "variant": "checklist"
            },
            {
              "content_html": "<div class=\"callout-warning\"><strong>Keep it controlled:</strong> this is a \"taste\" of tempo, not sweet spot. Finish fresher than you started so Saturday’s long run stays on track.</div>",
              "key": "2026-03-06-callout-1",
              "title": null,
              "tone": "warning",
              "type": "html",
              "variant": "callout"
            }
          ],
          "date": "2026-03-06",
          "day_id": "2026-03-06",
          "day_label": "Aerobic ride + tempo taste",
          "estimated_duration_min": 70,
          "estimated_intensity": "moderate",
          "focus_color": "#1565c0",
          "focus_type": "endurance",
          "icon": "🚴",
          "is_completed": true,
          "nodes": [],
          "primary_distance_km": null,
          "readiness_note": "Keep the tempo strictly controlled (upper Z3 feel). If HR is unusually high, legs feel hollow, or any illness heaviness shows up, skip tempo and ride steady Z2.",
          "workout_title": "Aerobic ride + tempo taste"
        },
        {
          "blocks": [
            {
              "content_html": "<div class=\"workout\"><div class=\"workout-title\">Long easy run <span class=\"focus focus--endurance\">Endurance</span></div><div class=\"workout-meta\">run . 95–100min . Z1→Z2→Z1</div></div>",
              "key": "2026-03-07-workout",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "workout"
            },
            {
              "content_html": "<ul class=\"checklist task--run\"><li>10min Z1 easy</li><li>80–85min Z2 steady (repeatable effort)</li><li>5min Z1 cool-down</li></ul>",
              "key": "2026-03-07-checklist",
              "title": "Execution",
              "tone": null,
              "type": "html",
              "variant": "checklist"
            },
            {
              "content_html": "<div class=\"callout-warning\"><strong>Keep it boring-easy:</strong> <strong>no fast finish</strong>. If conditions/legs push HR up, back off.</div>",
              "key": "2026-03-07-callout-1",
              "title": null,
              "tone": "warning",
              "type": "html",
              "variant": "callout"
            }
          ],
          "date": "2026-03-07",
          "day_id": "2026-03-07",
          "day_label": "Long easy run",
          "estimated_duration_min": 100,
          "estimated_intensity": "moderate",
          "focus_color": "#00897b",
          "focus_type": "endurance",
          "icon": "🏃‍♂️",
          "is_completed": false,
          "nodes": [],
          "primary_distance_km": null,
          "readiness_note": "Keep this strictly aerobic—if you’re not feeling springy, shorten slightly but keep it easy and steady.",
          "workout_title": "Long easy Z2"
        },
        {
          "blocks": [
            {
              "content_html": "<div class=\"grid grid--2\"><div class=\"workout\"><div class=\"workout-title\">Friends upper-body calisthenics <span class=\"focus focus--strength-aerobic\">Strength</span></div><div class=\"workout-meta\">cali . 40min . as usual</div></div><div class=\"workout\"><div class=\"workout-title\">Easy jog shakeout <span class=\"focus focus--easy\">Easy</span></div><div class=\"workout-meta\">run . 20–30min . Z1–Z2</div></div></div>",
              "key": "2026-03-08-workout",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "workout"
            },
            {
              "content_html": "<ul class=\"checklist task--cali\"><li>40min upper-body calisthenics (as usual)</li></ul><ul class=\"checklist task--run\"><li>20–30min easy run Z1–Z2 (shakeout pace)</li></ul>",
              "key": "2026-03-08-checklist",
              "title": "Execution",
              "tone": null,
              "type": "html",
              "variant": "checklist"
            },
            {
              "content_html": "<div class=\"callout-warning\"><strong>If sore from Saturday:</strong> keep the run <strong>short + very easy</strong> (or skip and walk).</div>",
              "key": "2026-03-08-callout-1",
              "title": null,
              "tone": "warning",
              "type": "html",
              "variant": "callout"
            }
          ],
          "date": "2026-03-08",
          "day_id": "2026-03-08",
          "day_label": "Cali + easy jog",
          "estimated_duration_min": 75,
          "estimated_intensity": "moderate",
          "focus_color": "#6a1b9a",
          "focus_type": "strength-aerobic",
          "icon": "🏋️",
          "is_completed": false,
          "nodes": [],
          "primary_distance_km": null,
          "readiness_note": "Use this as a recovery-support day; if legs are heavy from the long run, make the jog minimal and keep calisthenics controlled.",
          "workout_title": "Calisthenics + shakeout"
        },
        {
          "blocks": [
            {
              "content_html": "<div class=\"workout\"><div class=\"workout-title\">Endurance bike (smooth) <span class=\"focus focus--aerobic\">Aerobic</span></div><div class=\"workout-meta\">bike . 60–75min + 8–10min care . Z2</div></div>",
              "key": "2026-03-09-workout",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "workout"
            },
            {
              "content_html": "<ul class=\"checklist task--bike\"><li>10min easy spin</li><li>45–60min Z2 steady (smooth cadence, no surges)</li><li>5min easy</li></ul><ul class=\"checklist task--strength\"><li>8–10min foot/calf care: eccentric calf lowers <strong>2–3×8/side</strong></li></ul>",
              "key": "2026-03-09-checklist",
              "title": "Execution",
              "tone": null,
              "type": "html",
              "variant": "checklist"
            },
            {
              "content_html": "<div class=\"callout-good\"><strong>Goal:</strong> low-cost volume—finish feeling fresh enough to hit Tuesday’s controlled quality.</div>",
              "key": "2026-03-09-callout-1",
              "title": null,
              "tone": "good",
              "type": "html",
              "variant": "callout"
            }
          ],
          "date": "2026-03-09",
          "day_id": "2026-03-09",
          "day_label": "Z2 bike + calf care",
          "estimated_duration_min": 80,
          "estimated_intensity": "low",
          "focus_color": "#0288d1",
          "focus_type": "aerobic",
          "icon": "🚴",
          "is_completed": false,
          "nodes": [],
          "primary_distance_km": null,
          "readiness_note": "Keep cadence smooth and effort steady; if you’re carrying fatigue, shorten the Z2 block and do the calf care anyway.",
          "workout_title": "Z2 endurance ride"
        },
        {
          "blocks": [
            {
              "content_html": "<div class=\"workout\"><div class=\"workout-title\">Key run: Controlled LT intervals <span class=\"focus focus--threshold\">Threshold</span></div><div class=\"workout-meta\">run . 60min . Z2 warm-up + Z4 (controlled)</div></div>",
              "key": "2026-03-10-workout",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "workout"
            },
            {
              "content_html": "<table class=\"table\"><thead><tr><th>Rep</th><th>Work</th><th>Target</th><th>Recovery</th></tr></thead><tbody><tr><td>1–3</td><td>8min</td><td>LT ~<strong>390–410 W</strong> <span class=\"badge badge-accent\">controlled</span></td><td>3min easy jog</td></tr></tbody></table>",
              "key": "2026-03-10-support-1",
              "title": "Main set targets",
              "tone": null,
              "type": "html",
              "variant": "support"
            },
            {
              "content_html": "<ul class=\"checklist task--run\"><li>15min easy Z2</li><li>3×(8min LT @ ~390–410 W, 3min easy jog)</li><li><strong>Recoveries truly easy</strong> so HR drops (don’t “float” mid-160s)</li><li>10min cool-down easy</li></ul>",
              "key": "2026-03-10-checklist",
              "title": "Execution",
              "tone": null,
              "type": "html",
              "variant": "checklist"
            },
            {
              "content_html": "<div class=\"callout-warning\"><strong>If yellow day:</strong> switch to <strong>2×8min</strong> only, or replace with <strong>45min Z2</strong>.</div>",
              "key": "2026-03-10-callout-1",
              "title": null,
              "tone": "warning",
              "type": "html",
              "variant": "callout"
            }
          ],
          "date": "2026-03-10",
          "day_id": "2026-03-10",
          "day_label": "Key: LT intervals",
          "estimated_duration_min": 60,
          "estimated_intensity": "high",
          "focus_color": "#ef6c00",
          "focus_type": "threshold",
          "icon": "🏃‍♂️",
          "is_completed": false,
          "nodes": [],
          "primary_distance_km": null,
          "readiness_note": "If you feel springy, execute as written with easy recoveries; if sleep/RHR flags show up, cap it at 2 reps or go pure Z2.",
          "workout_title": "3x8' LT"
        },
        {
          "blocks": [
            {
              "content_html": "<div class=\"workout\"><div class=\"workout-title\">Easy run + strides + posterior chain <span class=\"focus focus--strides\">Strides</span></div><div class=\"workout-meta\">run . 55–65min total . Z2 + short strides + strength</div></div>",
              "key": "2026-03-11-workout",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "workout"
            },
            {
              "content_html": "<ul class=\"checklist task--run\"><li>40–45min Z2 easy</li><li>6×20s strides (walk-back / 60–90s very easy)</li></ul><ul class=\"checklist task--strength\"><li>15–20min posterior chain (2 rounds, controlled):</li><li>Single-leg RDL <strong>6–8/side</strong></li><li>Step-downs <strong>6–8/side</strong></li><li>Glute bridge <strong>10–12</strong></li><li>Side plank <strong>30–45s/side</strong></li></ul>",
              "key": "2026-03-11-checklist",
              "title": "Execution",
              "tone": null,
              "type": "html",
              "variant": "checklist"
            },
            {
              "content_html": "<div class=\"callout-good\"><strong>Strides cue:</strong> fast but relaxed—stop if form degrades. Strength stays controlled (no grinding).</div>",
              "key": "2026-03-11-callout-1",
              "title": null,
              "tone": "good",
              "type": "html",
              "variant": "callout"
            }
          ],
          "date": "2026-03-11",
          "day_id": "2026-03-11",
          "day_label": "Easy + strides + strength",
          "estimated_duration_min": 60,
          "estimated_intensity": "moderate",
          "focus_color": "#5e35b1",
          "focus_type": "strides",
          "icon": "🏃‍♂️",
          "is_completed": false,
          "nodes": [],
          "primary_distance_km": null,
          "readiness_note": "If Tuesday left you flat, keep today as pure easy and skip strides; otherwise keep strides crisp and short with perfect form.",
          "workout_title": "Easy + 6 strides + strength"
        },
        {
          "blocks": [
            {
              "content_html": "<div class=\"workout\"><div class=\"workout-title\">Key bike: Sweet spot <span class=\"focus focus--sweet-spot\">Sweet spot</span></div><div class=\"workout-meta\">bike . 65min . Z2 + SS @ 210–218W</div></div>",
              "key": "2026-03-12-workout",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "workout"
            },
            {
              "content_html": "<table class=\"table\"><thead><tr><th>Set</th><th>Work</th><th>Target</th><th>Easy</th></tr></thead><tbody><tr><td>1–2</td><td>12min</td><td><strong>210–218 W</strong></td><td>5min</td></tr></tbody></table>",
              "key": "2026-03-12-support-1",
              "title": "Main set targets",
              "tone": null,
              "type": "html",
              "variant": "support"
            },
            {
              "content_html": "<ul class=\"checklist task--bike\"><li>10min easy</li><li>2×12min @ 210–218 W, 5min easy between</li><li>10–15min Z2 easy cool-down</li></ul>",
              "key": "2026-03-12-checklist",
              "title": "Execution",
              "tone": null,
              "type": "html",
              "variant": "checklist"
            },
            {
              "content_html": "<div class=\"callout-good\"><strong>Rule:</strong> should feel “strong but sustainable,” <strong>not</strong> like a test.</div>",
              "key": "2026-03-12-callout-1",
              "title": null,
              "tone": "good",
              "type": "html",
              "variant": "callout"
            }
          ],
          "date": "2026-03-12",
          "day_id": "2026-03-12",
          "day_label": "Key: sweet spot bike",
          "estimated_duration_min": 65,
          "estimated_intensity": "high",
          "focus_color": "#f9a825",
          "focus_type": "sweet-spot",
          "icon": "🚴",
          "is_completed": false,
          "nodes": [],
          "primary_distance_km": null,
          "readiness_note": "Aim for repeatable sweet spot—if fatigue is lingering, shorten to 1 interval or stay Z2 and save the win for consistency.",
          "workout_title": "2x12' sweet spot"
        }
      ],
      "end_date": "2026-03-12",
      "notes_blocks": [],
      "notes_nodes": [
        {
          "blocks": [
            {
              "content_html": "<div class=\"grid grid--3\"><div class=\"card\"><strong>Key sessions</strong><div><span class=\"badge badge-accent\">Tue</span> Controlled LT run</div><div><span class=\"badge badge-accent\">Thu</span> Sweet-spot bike</div></div><div class=\"card\"><strong>Long run</strong><div><span class=\"badge badge-info\">Sat</span> Easy (repeatable)</div><div><span class=\"badge badge-info\">Sun</span> Cali + easy jog</div></div><div class=\"card\"><strong>Strength</strong><div>2× micro-dose</div><div>Calves/feet + posterior chain</div></div></div>",
              "key": "wk-2026-03-06-meta",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "meta"
            }
          ],
          "children": [],
          "default_open": null,
          "disclosure_mode": "inline",
          "node_id": "wk-2026-03-06-overview",
          "summary": "Key: Tue LT run • Thu sweet-spot | Long: Sat easy | Sun cali + easy run | Strength: 2x micro-dose",
          "title": "Week overview",
          "tone": "neutral"
        }
      ],
      "start_date": "2026-03-06",
      "week_id": "wk-2026-03-06",
      "week_theme": "Reload Week",
      "week_label": "Week 1 (Phase 1: reload)"
    },
    {
      "days": [
        {
          "blocks": [
            {
              "content_html": "<div class=\"workout\"><div class=\"workout-title\">Recovery run + mobility <span class=\"focus focus--recovery\">Recovery</span></div><div class=\"workout-meta\">run . 40–45min + 10min mobility . Z1–Z2</div></div>",
              "key": "2026-03-13-workout",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "workout"
            },
            {
              "content_html": "<ul class=\"checklist task--run\"><li>40–45min easy (keep HR calm; flat route)</li></ul><ul class=\"checklist task--mobility\"><li>10min mobility</li></ul>",
              "key": "2026-03-13-checklist",
              "title": "Execution",
              "tone": null,
              "type": "html",
              "variant": "checklist"
            },
            {
              "content_html": "<div class=\"callout-good\"><strong>Win the day:</strong> easy enough that tomorrow’s long run feels normal.</div>",
              "key": "2026-03-13-callout-1",
              "title": null,
              "tone": "good",
              "type": "html",
              "variant": "callout"
            }
          ],
          "date": "2026-03-13",
          "day_id": "2026-03-13",
          "day_label": "Recovery run + mobility",
          "estimated_duration_min": 55,
          "estimated_intensity": "low",
          "focus_color": "#43a047",
          "focus_type": "recovery",
          "icon": "🏃‍♂️",
          "is_completed": false,
          "nodes": [],
          "primary_distance_km": null,
          "readiness_note": "Keep it truly easy and flat; if you’re carrying fatigue, lean into Z1 and prioritize mobility.",
          "workout_title": "Recovery run + mobility"
        },
        {
          "blocks": [
            {
              "content_html": "<div class=\"workout\"><div class=\"workout-title\">Long easy run + fueling practice <span class=\"focus focus--endurance\">Endurance</span></div><div class=\"workout-meta\">run . 105–110min . Z1→Z2→Z1</div></div>",
              "key": "2026-03-14-workout",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "workout"
            },
            {
              "content_html": "<div class=\"card\"><strong>Start simple</strong><div><span class=\"domain-chip domain-body\">Body</span> ~<strong>30–40 g carbs/hr</strong> + fluids</div></div>",
              "key": "2026-03-14-fueling",
              "title": "Fueling practice",
              "tone": null,
              "type": "html",
              "variant": "fueling"
            },
            {
              "content_html": "<ul class=\"checklist task--run\"><li>10min Z1</li><li>90–95min Z2 steady</li><li>5min Z1 cool-down</li><li>Practice fueling early and consistently (don’t wait until you’re depleted)</li></ul>",
              "key": "2026-03-14-checklist",
              "title": "Execution",
              "tone": null,
              "type": "html",
              "variant": "checklist"
            },
            {
              "content_html": "<div class=\"callout-warning\"><strong>Control:</strong> keep this “could do this again tomorrow” easy. If HR drifts, reduce power/pace.</div>",
              "key": "2026-03-14-callout-1",
              "title": null,
              "tone": "warning",
              "type": "html",
              "variant": "callout"
            }
          ],
          "date": "2026-03-14",
          "day_id": "2026-03-14",
          "day_label": "Long run + fueling",
          "estimated_duration_min": 110,
          "estimated_intensity": "moderate",
          "focus_color": "#00897b",
          "focus_type": "endurance",
          "icon": "🏃‍♂️",
          "is_completed": false,
          "nodes": [],
          "primary_distance_km": null,
          "readiness_note": "Treat fueling as the main skill today; keep the run easy and steady so digestion and rhythm are predictable.",
          "workout_title": "Long run + fueling"
        },
        {
          "blocks": [
            {
              "content_html": "<div class=\"grid grid--2\"><div class=\"workout\"><div class=\"workout-title\">Friends calisthenics <span class=\"focus focus--strength-aerobic\">Strength</span></div><div class=\"workout-meta\">cali . 40min</div></div><div class=\"workout\"><div class=\"workout-title\">Easy jog (pure shakeout) <span class=\"focus focus--easy\">Easy</span></div><div class=\"workout-meta\">run . 20–30min . Z1–Z2</div></div></div>",
              "key": "2026-03-15-workout",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "workout"
            },
            {
              "content_html": "<ul class=\"checklist task--cali\"><li>40min calisthenics</li></ul><ul class=\"checklist task--run\"><li>20–30min easy run (pure shakeout)</li></ul>",
              "key": "2026-03-15-checklist",
              "title": "Execution",
              "tone": null,
              "type": "html",
              "variant": "checklist"
            }
          ],
          "date": "2026-03-15",
          "day_id": "2026-03-15",
          "day_label": "Cali + easy jog",
          "estimated_duration_min": 75,
          "estimated_intensity": "moderate",
          "focus_color": "#6a1b9a",
          "focus_type": "strength-aerobic",
          "icon": "🏋️",
          "is_completed": false,
          "nodes": [],
          "primary_distance_km": null,
          "readiness_note": "Keep the run purely restorative—tomorrow’s bike should feel smooth, not forced.",
          "workout_title": "Calisthenics + shakeout"
        },
        {
          "blocks": [
            {
              "content_html": "<div class=\"workout\"><div class=\"workout-title\">Endurance bike + calf/foot care <span class=\"focus focus--aerobic\">Aerobic</span></div><div class=\"workout-meta\">bike . 70–85min + 8–10min care . Z2</div></div>",
              "key": "2026-03-16-workout",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "workout"
            },
            {
              "content_html": "<ul class=\"checklist task--bike\"><li>10min easy</li><li>55–70min Z2 steady</li><li>5min easy</li></ul><ul class=\"checklist task--strength\"><li>8–10min calves/feet: eccentrics + toe yoga</li></ul>",
              "key": "2026-03-16-checklist",
              "title": "Execution",
              "tone": null,
              "type": "html",
              "variant": "checklist"
            }
          ],
          "date": "2026-03-16",
          "day_id": "2026-03-16",
          "day_label": "Z2 bike + calves/feet",
          "estimated_duration_min": 90,
          "estimated_intensity": "low",
          "focus_color": "#0288d1",
          "focus_type": "aerobic",
          "icon": "🚴",
          "is_completed": false,
          "nodes": [],
          "primary_distance_km": null,
          "readiness_note": "Steady aerobic ride only—no surges. If legs are heavy, shorten the main Z2 and keep the calf/foot work.",
          "workout_title": "Z2 ride + calf/foot"
        },
        {
          "blocks": [
            {
              "content_html": "<div class=\"workout\"><div class=\"workout-title\">Key run: 1k repeats (controlled) <span class=\"focus focus--threshold\">Threshold</span></div><div class=\"workout-meta\">run . 65min . Z2 + Z4 reps (not VO₂)</div></div>",
              "key": "2026-03-17-workout",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "workout"
            },
            {
              "content_html": "<table class=\"table\"><thead><tr><th>Reps</th><th>Work</th><th>Target</th><th>Recovery</th></tr></thead><tbody><tr><td>1–5</td><td>1 km</td><td>~<strong>390–415 W</strong> <span class=\"badge badge-accent\">even</span></td><td>2min easy jog</td></tr></tbody></table>",
              "key": "2026-03-17-support-1",
              "title": "Main set targets",
              "tone": null,
              "type": "html",
              "variant": "support"
            },
            {
              "content_html": "<ul class=\"checklist task--run\"><li>15min Z2 warm-up</li><li>4×20s relaxed strides</li><li>5×1 km @ ~390–415 W, 2min easy jog</li><li>Aim: even reps; HR rises gradually (avoid <strong>&gt;180</strong> early)</li><li>10–15min cool-down</li></ul>",
              "key": "2026-03-17-checklist",
              "title": "Execution",
              "tone": null,
              "type": "html",
              "variant": "checklist"
            },
            {
              "content_html": "<div class=\"callout-warning\"><strong>If yellow day:</strong> do <strong>4×1 km</strong> or swap to <strong>45–50min Z2</strong>.</div>",
              "key": "2026-03-17-callout-1",
              "title": null,
              "tone": "warning",
              "type": "html",
              "variant": "callout"
            }
          ],
          "date": "2026-03-17",
          "day_id": "2026-03-17",
          "day_label": "Key: 5x1k reps",
          "estimated_duration_min": 65,
          "estimated_intensity": "high",
          "focus_color": "#ef6c00",
          "focus_type": "threshold",
          "icon": "🏃‍♂️",
          "is_completed": false,
          "nodes": [],
          "primary_distance_km": null,
          "readiness_note": "Run the reps evenly and controlled; if the first rep feels too spicy or HR spikes early, downshift immediately (4 reps or Z2).",
          "workout_title": "5x1k (controlled)"
        },
        {
          "blocks": [
            {
              "content_html": "<div class=\"workout\"><div class=\"workout-title\">Easy run + strength micro-dose <span class=\"focus focus--easy\">Easy</span></div><div class=\"workout-meta\">run . 55–70min total . Z2 + 15min strength</div></div>",
              "key": "2026-03-18-workout",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "workout"
            },
            {
              "content_html": "<ul class=\"checklist task--run\"><li>45–55min Z2 easy</li></ul><ul class=\"checklist task--strength\"><li>15min strength (2 rounds):</li><li>Split squat <strong>6–8/side</strong></li><li>Hamstring slide-curl <strong>8–10</strong></li><li>Calf raises <strong>10–12</strong></li><li>Dead bug <strong>8–10/side</strong></li></ul>",
              "key": "2026-03-18-checklist",
              "title": "Execution",
              "tone": null,
              "type": "html",
              "variant": "checklist"
            }
          ],
          "date": "2026-03-18",
          "day_id": "2026-03-18",
          "day_label": "Easy Z2 + strength",
          "estimated_duration_min": 65,
          "estimated_intensity": "moderate",
          "focus_color": "#2e7d32",
          "focus_type": "easy-strength",
          "icon": "🏃‍♂️",
          "is_completed": false,
          "nodes": [],
          "primary_distance_km": null,
          "readiness_note": "Keep the run relaxed; strength should feel crisp and controlled—leave reps in the tank so Thursday’s bike is solid.",
          "workout_title": "Easy run + strength"
        },
        {
          "blocks": [
            {
              "content_html": "<div class=\"workout\"><div class=\"workout-title\">Key bike: Sweet spot progression <span class=\"focus focus--sweet-spot\">Sweet spot</span></div><div class=\"workout-meta\">bike . 70min . 3×10min @ 210–218W</div></div>",
              "key": "2026-03-19-workout",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "workout"
            },
            {
              "content_html": "<table class=\"table\"><thead><tr><th>Set</th><th>Work</th><th>Target</th><th>Easy</th></tr></thead><tbody><tr><td>1–3</td><td>10min</td><td><strong>210–218 W</strong></td><td>5min</td></tr></tbody></table>",
              "key": "2026-03-19-support-1",
              "title": "Main set targets",
              "tone": null,
              "type": "html",
              "variant": "support"
            },
            {
              "content_html": "<ul class=\"checklist task--bike\"><li>10min easy</li><li>3×10min @ 210–218 W, 5min easy between</li><li>10min easy cool-down</li></ul>",
              "key": "2026-03-19-checklist",
              "title": "Execution",
              "tone": null,
              "type": "html",
              "variant": "checklist"
            }
          ],
          "date": "2026-03-19",
          "day_id": "2026-03-19",
          "day_label": "Key: SS bike 3x10'",
          "estimated_duration_min": 70,
          "estimated_intensity": "high",
          "focus_color": "#f9a825",
          "focus_type": "sweet-spot",
          "icon": "🚴",
          "is_completed": false,
          "nodes": [],
          "primary_distance_km": null,
          "readiness_note": "Hold steady power and keep it comfortably hard; if you’re not recovering well, cut to 2 intervals and keep the cooldown easy.",
          "workout_title": "3x10' sweet spot"
        }
      ],
      "end_date": "2026-03-19",
      "notes_blocks": [],
      "notes_nodes": [
        {
          "blocks": [
            {
              "content_html": "<div class=\"grid grid--3\"><div class=\"card\"><strong>Key sessions</strong><div><span class=\"badge badge-accent\">Tue</span> 1k repeats (controlled)</div><div><span class=\"badge badge-accent\">Thu</span> Sweet-spot progression</div></div><div class=\"card\"><strong>Long run</strong><div><span class=\"badge badge-info\">Sat</span> Slightly longer</div><div><span class=\"badge badge-info\">Fuel</span> 30–40 g carbs/hr</div></div><div class=\"card\"><strong>Strength</strong><div>2× micro-dose</div><div>Calves/feet + posterior chain</div></div></div>",
              "key": "wk-2026-03-13-meta",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "meta"
            }
          ],
          "children": [],
          "default_open": null,
          "disclosure_mode": "inline",
          "node_id": "wk-2026-03-13-overview",
          "summary": "Key: Tue 1k reps (threshold-leaning) • Thu sweet-spot | Long: Sat + fueling practice | Strength: 2x micro-dose",
          "title": "Week overview",
          "tone": "neutral"
        }
      ],
      "start_date": "2026-03-13",
      "week_id": "wk-2026-03-13",
      "week_theme": "Build Week 1 of 2",
      "week_label": "Week 2 (Phase 1: density)"
    },
    {
      "days": [
        {
          "blocks": [
            {
              "content_html": "<div class=\"workout\"><div class=\"workout-title\">Easy run + strides <span class=\"focus focus--strides\">Strides</span></div><div class=\"workout-meta\">run . 45–55min . Z2 + short strides</div></div>",
              "key": "2026-03-20-workout",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "workout"
            },
            {
              "content_html": "<ul class=\"checklist task--run\"><li>40–45min Z2 easy</li><li>6×15s strides (full control; generous easy between)</li></ul>",
              "key": "2026-03-20-checklist",
              "title": "Execution",
              "tone": null,
              "type": "html",
              "variant": "checklist"
            },
            {
              "content_html": "<div class=\"callout-good\"><strong>Strides:</strong> think “quick + smooth,” not sprint. Stop early if mechanics slip.</div>",
              "key": "2026-03-20-callout-1",
              "title": null,
              "tone": "good",
              "type": "html",
              "variant": "callout"
            }
          ],
          "date": "2026-03-20",
          "day_id": "2026-03-20",
          "day_label": "Easy + strides",
          "estimated_duration_min": 50,
          "estimated_intensity": "moderate",
          "focus_color": "#5e35b1",
          "focus_type": "strides",
          "icon": "🏃‍♂️",
          "is_completed": false,
          "nodes": [],
          "primary_distance_km": null,
          "readiness_note": "If you feel snappy, do the strides with full control; if you’re flat or sleep was off, skip strides and keep it easy only.",
          "workout_title": "Easy + 6 strides"
        },
        {
          "blocks": [
            {
              "content_html": "<div class=\"workout\"><div class=\"workout-title\">Long easy run + fueling practice <span class=\"focus focus--endurance\">Endurance</span></div><div class=\"workout-meta\">run . 110–115min . Z1→Z2→Z1</div></div>",
              "key": "2026-03-21-workout",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "workout"
            },
            {
              "content_html": "<div class=\"card\"><strong>Practice what you’ll use later on trail</strong><div><span class=\"domain-chip domain-body\">Body</span> <strong>35–45 g carbs/hr</strong></div></div>",
              "key": "2026-03-21-fueling",
              "title": "Fueling practice",
              "tone": null,
              "type": "html",
              "variant": "fueling"
            },
            {
              "content_html": "<ul class=\"checklist task--run\"><li>10min Z1</li><li>95–100min Z2</li><li>5min Z1</li><li>Fuel consistently (35–45 g carbs/hr)</li></ul>",
              "key": "2026-03-21-checklist",
              "title": "Execution",
              "tone": null,
              "type": "html",
              "variant": "checklist"
            }
          ],
          "date": "2026-03-21",
          "day_id": "2026-03-21",
          "day_label": "Long run + fueling",
          "estimated_duration_min": 115,
          "estimated_intensity": "moderate",
          "focus_color": "#00897b",
          "focus_type": "endurance",
          "icon": "🏃‍♂️",
          "is_completed": false,
          "nodes": [],
          "primary_distance_km": null,
          "readiness_note": "Keep it smooth and repeatable; prioritize fueling timing and gut comfort over any pace target.",
          "workout_title": "Long run + fueling"
        },
        {
          "blocks": [
            {
              "content_html": "<div class=\"grid grid--2\"><div class=\"workout\"><div class=\"workout-title\">Friends calisthenics <span class=\"focus focus--strength-aerobic\">Strength</span></div><div class=\"workout-meta\">cali . 40min</div></div><div class=\"workout\"><div class=\"workout-title\">Very easy jog (or walk) <span class=\"focus focus--recovery\">Recovery</span></div><div class=\"workout-meta\">run/walk . 20–30min . Z1–Z2</div></div></div>",
              "key": "2026-03-22-workout",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "workout"
            },
            {
              "content_html": "<ul class=\"checklist task--cali\"><li>40min calisthenics</li></ul><ul class=\"checklist task--run\"><li>20–30min very easy run <em>or</em> 30min walk if legs feel beaten up</li></ul>",
              "key": "2026-03-22-checklist",
              "title": "Execution",
              "tone": null,
              "type": "html",
              "variant": "checklist"
            }
          ],
          "date": "2026-03-22",
          "day_id": "2026-03-22",
          "day_label": "Cali + easy jog/walk",
          "estimated_duration_min": 75,
          "estimated_intensity": "moderate",
          "focus_color": "#6a1b9a",
          "focus_type": "strength-aerobic",
          "icon": "🏋️",
          "is_completed": false,
          "nodes": [],
          "primary_distance_km": null,
          "readiness_note": "Let recovery lead—choose the option (jog vs walk) that leaves your legs fresher for Tuesday’s LT work.",
          "workout_title": "Calisthenics + easy jog"
        },
        {
          "blocks": [
            {
              "content_html": "<div class=\"workout\"><div class=\"workout-title\">Easy bike + mobility <span class=\"focus focus--recovery-bike\">Recovery</span></div><div class=\"workout-meta\">bike . 50–65min + 10min mobility . Z1–Z2</div></div>",
              "key": "2026-03-23-workout",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "workout"
            },
            {
              "content_html": "<ul class=\"checklist task--bike\"><li>50–65min relaxed spin (keep it light)</li></ul><ul class=\"checklist task--mobility\"><li>10min mobility</li></ul>",
              "key": "2026-03-23-checklist",
              "title": "Execution",
              "tone": null,
              "type": "html",
              "variant": "checklist"
            },
            {
              "content_html": "<div class=\"callout-good\"><strong>Intent:</strong> open the legs without adding stress—tomorrow’s LT should feel controlled, not forced.</div>",
              "key": "2026-03-23-callout-1",
              "title": null,
              "tone": "good",
              "type": "html",
              "variant": "callout"
            }
          ],
          "date": "2026-03-23",
          "day_id": "2026-03-23",
          "day_label": "Easy bike + mobility",
          "estimated_duration_min": 70,
          "estimated_intensity": "low",
          "focus_color": "#4fc3f7",
          "focus_type": "recovery-bike",
          "icon": "🚴",
          "is_completed": false,
          "nodes": [],
          "primary_distance_km": null,
          "readiness_note": "Keep the spin light and conversational; if you’re tired, reduce duration and emphasize mobility.",
          "workout_title": "Easy spin + mobility"
        },
        {
          "blocks": [
            {
              "content_html": "<div class=\"workout\"><div class=\"workout-title\">Key run: LT cruise intervals <span class=\"focus focus--threshold\">Threshold</span></div><div class=\"workout-meta\">run . 65min . Z2 + Z4 (controlled)</div></div>",
              "key": "2026-03-24-workout",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "workout"
            },
            {
              "content_html": "<table class=\"table\"><thead><tr><th>Block</th><th>Work</th><th>Target</th><th>Easy</th></tr></thead><tbody><tr><td>1–2</td><td>15min</td><td>LT ~<strong>390–405 W</strong></td><td>4min</td></tr></tbody></table>",
              "key": "2026-03-24-support-1",
              "title": "Main set targets",
              "tone": null,
              "type": "html",
              "variant": "support"
            },
            {
              "content_html": "<ul class=\"checklist task--run\"><li>15min Z2 warm-up</li><li>2×(15min LT @ ~390–405 W, 4min easy)</li><li>10–12min cool-down</li></ul>",
              "key": "2026-03-24-checklist",
              "title": "Execution",
              "tone": null,
              "type": "html",
              "variant": "checklist"
            },
            {
              "content_html": "<div class=\"callout-warning\"><strong>If yellow day:</strong> make it <strong>2×10min</strong> or <strong>50min Z2</strong>.</div>",
              "key": "2026-03-24-callout-1",
              "title": null,
              "tone": "warning",
              "type": "html",
              "variant": "callout"
            }
          ],
          "date": "2026-03-24",
          "day_id": "2026-03-24",
          "day_label": "Key: LT cruise 2x15'",
          "estimated_duration_min": 65,
          "estimated_intensity": "high",
          "focus_color": "#ef6c00",
          "focus_type": "threshold",
          "icon": "🏃‍♂️",
          "is_completed": false,
          "nodes": [],
          "primary_distance_km": null,
          "readiness_note": "Stay controlled and avoid turning this into a test; if recovery signals are off, shorten the blocks or go pure Z2.",
          "workout_title": "2x15' LT"
        },
        {
          "blocks": [
            {
              "content_html": "<div class=\"workout\"><div class=\"workout-title\">Easy run + downhill-prep basics <span class=\"focus focus--easy\">Easy</span></div><div class=\"workout-meta\">run . 55–70min total . Z2 + eccentric basics</div></div>",
              "key": "2026-03-25-workout",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "workout"
            },
            {
              "content_html": "<ul class=\"checklist task--run\"><li>45–55min Z2 easy (flat, relaxed)</li></ul><ul class=\"checklist task--strength\"><li>15min strength emphasis (downhill-prep basics):</li><li>Step-downs <strong>2×6–8/side</strong></li><li>Eccentric calf lowers <strong>2×8/side</strong></li><li>Hip airplanes <strong>2×5/side</strong></li></ul>",
              "key": "2026-03-25-checklist",
              "title": "Execution",
              "tone": null,
              "type": "html",
              "variant": "checklist"
            }
          ],
          "date": "2026-03-25",
          "day_id": "2026-03-25",
          "day_label": "Easy + downhill-prep",
          "estimated_duration_min": 65,
          "estimated_intensity": "moderate",
          "focus_color": "#2e7d32",
          "focus_type": "easy-strength",
          "icon": "🏃‍♂️",
          "is_completed": false,
          "nodes": [],
          "primary_distance_km": null,
          "readiness_note": "Keep the run easy and flat; eccentric work should be controlled—if you’re sore, reduce volume and focus on form.",
          "workout_title": "Easy run + downhill-prep"
        },
        {
          "blocks": [
            {
              "content_html": "<div class=\"workout\"><div class=\"workout-title\">Key bike: Sweet spot (longer blocks) <span class=\"focus focus--sweet-spot\">Sweet spot</span></div><div class=\"workout-meta\">bike . 75min . 2×20min @ 210–216W</div></div>",
              "key": "2026-03-26-workout",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "workout"
            },
            {
              "content_html": "<table class=\"table\"><thead><tr><th>Set</th><th>Work</th><th>Target</th><th>Easy</th></tr></thead><tbody><tr><td>1–2</td><td>20min</td><td><strong>210–216 W</strong></td><td>6min</td></tr></tbody></table>",
              "key": "2026-03-26-support-1",
              "title": "Main set targets",
              "tone": null,
              "type": "html",
              "variant": "support"
            },
            {
              "content_html": "<ul class=\"checklist task--bike\"><li>10min easy</li><li>2×20min @ 210–216 W, 6min easy between</li><li>10min easy cool-down</li></ul>",
              "key": "2026-03-26-checklist",
              "title": "Execution",
              "tone": null,
              "type": "html",
              "variant": "checklist"
            },
            {
              "content_html": "<div class=\"callout-good\"><strong>Cap the effort:</strong> strong, steady, repeatable. If breathing gets ragged, reduce watts.</div>",
              "key": "2026-03-26-callout-1",
              "title": null,
              "tone": "good",
              "type": "html",
              "variant": "callout"
            }
          ],
          "date": "2026-03-26",
          "day_id": "2026-03-26",
          "day_label": "Key: SS bike 2x20'",
          "estimated_duration_min": 75,
          "estimated_intensity": "high",
          "focus_color": "#f9a825",
          "focus_type": "sweet-spot",
          "icon": "🚴",
          "is_completed": false,
          "nodes": [],
          "primary_distance_km": null,
          "readiness_note": "Prioritize steadiness over hero watts; if fatigue is up, shorten to 1×20' or ride Z2 and keep the habit.",
          "workout_title": "2x20' sweet spot"
        }
      ],
      "end_date": "2026-03-26",
      "notes_blocks": [],
      "notes_nodes": [
        {
          "blocks": [
            {
              "content_html": "<div class=\"grid grid--3\"><div class=\"card\"><strong>Key sessions</strong><div><span class=\"badge badge-accent\">Tue</span> LT cruise intervals</div><div><span class=\"badge badge-accent\">Thu</span> Sweet-spot longer blocks</div></div><div class=\"card\"><strong>Long run</strong><div><span class=\"badge badge-info\">Sat</span> Small step up</div><div><span class=\"badge badge-info\">Fuel</span> 35–45 g carbs/hr</div></div><div class=\"card\"><strong>Quality rule</strong><div><span class=\"badge badge-good\">Repeatable</span></div><div>Keep it controlled</div></div></div>",
              "key": "wk-2026-03-20-meta",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "meta"
            }
          ],
          "children": [],
          "default_open": null,
          "disclosure_mode": "inline",
          "node_id": "wk-2026-03-20-overview",
          "summary": "Key: Tue LT blocks • Thu sweet-spot (longer) | Long: Sat + fueling practice",
          "title": "Week overview",
          "tone": "neutral"
        }
      ],
      "start_date": "2026-03-20",
      "week_id": "wk-2026-03-20",
      "week_theme": "Build Week 2 of 2",
      "week_label": "Week 3 (Phase 1: consolidate)"
    },
    {
      "days": [
        {
          "blocks": [
            {
              "content_html": "<div class=\"workout\"><div class=\"workout-title\">Easy run <span class=\"focus focus--easy\">Easy</span></div><div class=\"workout-meta\">run . 45–50min . Z2</div></div>",
              "key": "2026-03-27-workout",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "workout"
            },
            {
              "content_html": "<ul class=\"checklist task--run\"><li>45–50min Z2 easy</li><li><em>Optional:</em> 4×15s strides only if legs feel fresh</li></ul>",
              "key": "2026-03-27-checklist",
              "title": "Execution",
              "tone": null,
              "type": "html",
              "variant": "checklist"
            },
            {
              "content_html": "<div class=\"callout-warning\"><strong>Gate for strides:</strong> only add them if you feel springy; otherwise keep it purely easy.</div>",
              "key": "2026-03-27-callout-1",
              "title": null,
              "tone": "warning",
              "type": "html",
              "variant": "callout"
            }
          ],
          "date": "2026-03-27",
          "day_id": "2026-03-27",
          "day_label": "Easy Z2 (opt strides)",
          "estimated_duration_min": 50,
          "estimated_intensity": "low",
          "focus_color": "#2e7d32",
          "focus_type": "easy",
          "icon": "🏃‍♂️",
          "is_completed": false,
          "nodes": [],
          "primary_distance_km": null,
          "readiness_note": "Stay easy and relaxed; only add strides if you’re genuinely fresh and coordinated.",
          "workout_title": "Easy Z2 (opt strides)"
        },
        {
          "blocks": [
            {
              "content_html": "<div class=\"workout\"><div class=\"workout-title\">Long easy run (rolling) <span class=\"focus focus--trail-endurance\">Trail endurance</span></div><div class=\"workout-meta\">run . 100–110min . Z2 (rolling route)</div></div>",
              "key": "2026-03-28-workout",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "workout"
            },
            {
              "content_html": "<div class=\"card\"><strong>Fuel target</strong><div><span class=\"domain-chip domain-body\">Body</span> <strong>35–45 g carbs/hr</strong></div></div>",
              "key": "2026-03-28-fueling",
              "title": "Fueling",
              "tone": null,
              "type": "html",
              "variant": "fueling"
            },
            {
              "content_html": "<ul class=\"checklist task--run\"><li>Choose a <strong>rolling route</strong> (no hammering climbs)</li><li>10min easy</li><li>85–95min Z2 steady</li><li>5min easy</li><li>Fuel 35–45 g carbs/hr</li></ul>",
              "key": "2026-03-28-checklist",
              "title": "Execution",
              "tone": null,
              "type": "html",
              "variant": "checklist"
            },
            {
              "content_html": "<div class=\"callout-warning\"><strong>Terrain rule:</strong> keep climbs gentle and controlled—this is durability, not a hill workout.</div>",
              "key": "2026-03-28-callout-1",
              "title": null,
              "tone": "warning",
              "type": "html",
              "variant": "callout"
            }
          ],
          "date": "2026-03-28",
          "day_id": "2026-03-28",
          "day_label": "Rolling long run + fuel",
          "estimated_duration_min": 110,
          "estimated_intensity": "moderate",
          "focus_color": "#00796b",
          "focus_type": "trail-endurance",
          "icon": "🏃‍♂️",
          "is_completed": false,
          "nodes": [],
          "primary_distance_km": null,
          "readiness_note": "Keep climbs controlled and fueling consistent; if you add any descents/trails, plan for low impact tomorrow.",
          "workout_title": "Rolling long run + fuel"
        },
        {
          "blocks": [
            {
              "content_html": "<div class=\"grid grid--2\"><div class=\"workout\"><div class=\"workout-title\">Friends calisthenics <span class=\"focus focus--strength-aerobic\">Strength</span></div><div class=\"workout-meta\">cali . 40min</div></div><div class=\"workout\"><div class=\"workout-title\">Easy jog (light) <span class=\"focus focus--easy\">Easy</span></div><div class=\"workout-meta\">run . 20–30min . Z1–Z2</div></div></div>",
              "key": "2026-03-29-workout",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "workout"
            },
            {
              "content_html": "<ul class=\"checklist task--cali\"><li>40min calisthenics</li></ul><ul class=\"checklist task--run\"><li>20–30min easy run (keep it light)</li></ul>",
              "key": "2026-03-29-checklist",
              "title": "Execution",
              "tone": null,
              "type": "html",
              "variant": "checklist"
            }
          ],
          "date": "2026-03-29",
          "day_id": "2026-03-29",
          "day_label": "Cali + easy jog",
          "estimated_duration_min": 75,
          "estimated_intensity": "moderate",
          "focus_color": "#6a1b9a",
          "focus_type": "strength-aerobic",
          "icon": "🏋️",
          "is_completed": false,
          "nodes": [],
          "primary_distance_km": null,
          "readiness_note": "Keep the jog light, especially if yesterday included any rolling/descents—tomorrow’s bike should be easy on the legs.",
          "workout_title": "Calisthenics + easy jog"
        },
        {
          "blocks": [
            {
              "content_html": "<div class=\"workout\"><div class=\"workout-title\">Easy aerobic spin + mobility <span class=\"focus focus--recovery-bike\">Recovery</span></div><div class=\"workout-meta\">bike . 60–70min + 10min mobility . Z1–Z2 (Phase 2 begins)</div></div>",
              "key": "2026-03-30-workout",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "workout"
            },
            {
              "content_html": "<ul class=\"checklist task--bike\"><li>60–70min easy aerobic spin (smooth cadence)</li></ul><ul class=\"checklist task--mobility\"><li>10min mobility: ankles + calves + hips</li></ul>",
              "key": "2026-03-30-checklist",
              "title": "Execution",
              "tone": null,
              "type": "html",
              "variant": "checklist"
            }
          ],
          "date": "2026-03-30",
          "day_id": "2026-03-30",
          "day_label": "Easy bike + mobility",
          "estimated_duration_min": 75,
          "estimated_intensity": "low",
          "focus_color": "#4fc3f7",
          "focus_type": "recovery-bike",
          "icon": "🚴",
          "is_completed": false,
          "nodes": [],
          "primary_distance_km": null,
          "readiness_note": "Keep it light and smooth to absorb the weekend; if you ran any descents, today should feel especially low-impact.",
          "workout_title": "Easy spin + mobility"
        },
        {
          "blocks": [
            {
              "content_html": "<div class=\"workout\"><div class=\"workout-title\">Key run (trail-strength): Uphill repeats <span class=\"focus focus--hills\">Hills</span></div><div class=\"workout-meta\">run . 60–70min . Z2 + Z3/low Z4 uphill</div></div>",
              "key": "2026-03-31-workout",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "workout"
            },
            {
              "content_html": "<table class=\"table\"><thead><tr><th>Reps</th><th>Work</th><th>Effort</th><th>Down</th></tr></thead><tbody><tr><td>1–6</td><td>3min uphill</td><td>Strong steady <span class=\"badge badge-accent\">controlled</span></td><td>Jog down easy</td></tr></tbody></table>",
              "key": "2026-03-31-support-1",
              "title": "Main set structure",
              "tone": null,
              "type": "html",
              "variant": "support"
            },
            {
              "content_html": "<ul class=\"checklist task--run\"><li>15min easy warm-up (include 2–3 short hill pickups if available)</li><li>6×(3min uphill @ strong steady/controlled, jog down easy)</li><li>Effort cap: finish thinking <strong>“could do 2 more”</strong></li><li>10–15min easy cool-down</li></ul>",
              "key": "2026-03-31-checklist",
              "title": "Execution",
              "tone": null,
              "type": "html",
              "variant": "checklist"
            },
            {
              "content_html": "<div class=\"callout-warning\"><strong>If yellow day:</strong> reduce to <strong>4×3min</strong> or do <strong>50min flat Z2</strong> instead.</div>",
              "key": "2026-03-31-callout-1",
              "title": null,
              "tone": "warning",
              "type": "html",
              "variant": "callout"
            }
          ],
          "date": "2026-03-31",
          "day_id": "2026-03-31",
          "day_label": "Key: uphill repeats",
          "estimated_duration_min": 65,
          "estimated_intensity": "high",
          "focus_color": "#d84315",
          "focus_type": "hills",
          "icon": "🏃‍♂️",
          "is_completed": false,
          "nodes": [],
          "primary_distance_km": null,
          "readiness_note": "Keep the uphill efforts controlled (strong steady, not a grind); if recovery is yellow/red, switch to fewer reps or flat Z2.",
          "workout_title": "6x3' uphill repeats"
        },
        {
          "blocks": [
            {
              "content_html": "<div class=\"workout\"><div class=\"workout-title\">Recovery run + calves/feet <span class=\"focus focus--recovery\">Recovery</span></div><div class=\"workout-meta\">run . 40–55min total . Z1–Z2 + foot/calf care</div></div>",
              "key": "2026-04-01-workout",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "workout"
            },
            {
              "content_html": "<ul class=\"checklist task--run\"><li>40–50min very easy (flat, relaxed)</li></ul><ul class=\"checklist task--strength\"><li>8–12min calves/feet: eccentric lowers + toe strength</li></ul>",
              "key": "2026-04-01-checklist",
              "title": "Execution",
              "tone": null,
              "type": "html",
              "variant": "checklist"
            },
            {
              "content_html": "<div class=\"callout-good\"><strong>Downhill/eccentric rule:</strong> if you ran trails/descents, keep today’s impact low and the run very easy.</div>",
              "key": "2026-04-01-callout-1",
              "title": null,
              "tone": "good",
              "type": "html",
              "variant": "callout"
            }
          ],
          "date": "2026-04-01",
          "day_id": "2026-04-01",
          "day_label": "Recovery run + calves/feet",
          "estimated_duration_min": 55,
          "estimated_intensity": "low",
          "focus_color": "#43a047",
          "focus_type": "recovery",
          "icon": "🏃‍♂️",
          "is_completed": false,
          "nodes": [],
          "primary_distance_km": null,
          "readiness_note": "Make this a true reset after hills—flat route, low intensity, and complete the calf/foot work with perfect control.",
          "workout_title": "Recovery run + calves/feet"
        },
        {
          "blocks": [
            {
              "content_html": "<div class=\"workout\"><div class=\"workout-title\">Key bike: Sweet spot maintenance <span class=\"focus focus--sweet-spot\">Sweet spot</span></div><div class=\"workout-meta\">bike . 70–75min . 3×10–12min @ 210–218W</div></div>",
              "key": "2026-04-02-workout",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "workout"
            },
            {
              "content_html": "<table class=\"table\"><thead><tr><th>Set</th><th>Work</th><th>Target</th><th>Easy</th></tr></thead><tbody><tr><td>1–3</td><td>10–12min</td><td><strong>210–218 W</strong></td><td>4–5min</td></tr></tbody></table>",
              "key": "2026-04-02-support-1",
              "title": "Main set targets",
              "tone": null,
              "type": "html",
              "variant": "support"
            },
            {
              "content_html": "<ul class=\"checklist task--bike\"><li>10min easy</li><li>3×10–12min @ 210–218 W, 4–5min easy between</li><li>10–15min easy cool-down</li></ul>",
              "key": "2026-04-02-checklist",
              "title": "Execution",
              "tone": null,
              "type": "html",
              "variant": "checklist"
            }
          ],
          "date": "2026-04-02",
          "day_id": "2026-04-02",
          "day_label": "Key: SS maintenance",
          "estimated_duration_min": 75,
          "estimated_intensity": "high",
          "focus_color": "#f9a825",
          "focus_type": "sweet-spot",
          "icon": "🚴",
          "is_completed": false,
          "nodes": [],
          "primary_distance_km": null,
          "readiness_note": "Keep the intervals comfortably hard and repeatable; if fatigue is up, shorten interval duration and keep the ride smooth.",
          "workout_title": "Sweet spot maintenance"
        }
      ],
      "end_date": "2026-04-02",
      "notes_blocks": [],
      "notes_nodes": [
        {
          "blocks": [
            {
              "content_html": "<div class=\"grid grid--2\"><div class=\"card\"><strong>Key sessions</strong><div><span class=\"badge badge-accent\">Tue</span> Hill “trail-strength” repeats (Phase 2)</div><div><span class=\"badge badge-accent\">Thu</span> Sweet-spot maintenance</div></div><div class=\"card\"><strong>Long run</strong><div><span class=\"badge badge-info\">Sat</span> Easy rolling terrain + fueling</div><div><span class=\"badge badge-warn\">Rule</span> Descents/trails → next day keep impact low</div></div></div>",
              "key": "wk-2026-03-27-meta",
              "title": null,
              "tone": null,
              "type": "html",
              "variant": "meta"
            }
          ],
          "children": [],
          "default_open": null,
          "disclosure_mode": "inline",
          "node_id": "wk-2026-03-27-overview",
          "summary": "Key: Tue uphill repeats (trail-strength) • Thu sweet-spot | Long: Sat rolling | Rule: descents → next day low impact",
          "title": "Week overview",
          "tone": "neutral"
        }
      ],
      "start_date": "2026-03-27",
      "week_id": "wk-2026-03-27",
      "week_theme": "Transition Week",
      "week_label": "Week 4 (Phase 1 finish → Phase 2 begins)"
    }
  ]
},
};
