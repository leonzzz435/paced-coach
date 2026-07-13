import json
import logging
import uuid
from datetime import datetime

from services.ai.ai_settings import AgentRole
from services.ai.langgraph.schemas.ui_block_sanitizer import sanitize_analysis
from services.ai.langgraph.schemas.ui_blocks import LlmAnalysis, UiAnalysis
from services.ai.langgraph.state.training_analysis_state import TrainingAnalysisState
from services.ai.model_config import ModelSelector
from services.ai.utils.retry_handler import AI_ANALYSIS_CONFIG, retry_with_backoff

from .node_base import create_cost_entry, execute_node_with_error_handling, log_node_completion
from .plan_formatter_node import _DESIGN_SYSTEM_BASE
from .prompt_components import PROVIDER_OPTIONAL_COACHING_POLICY

logger = logging.getLogger(__name__)

ANALYSIS_FORMATTER_SYSTEM_PROMPT = (
    _DESIGN_SYSTEM_BASE
    + PROVIDER_OPTIONAL_COACHING_POLICY
    + """

## Analysis Report — Specific Rules

### Content Routing
- `dashboard_kpis`: Curate the above-the-fold dashboard strip. This is the small set of metrics the athlete should see first.
  Order them by coaching salience, not by domain. Include only the strongest signals.
- `kpis`: Extract key metrics. Each KPI: `kpi_id`, `label`, `value`, `trend`, `status`, `domain`.
  Status values: "good", "warning", "danger", "neutral".
- Set KPI `domain` using canonical groups: `load`, `recovery`, `performance`, `body`, `sleep`.
  If a source concept is different (e.g. nutrition, distribution), map to the nearest canonical domain and keep nuance in text.
- `sections`: Group insights logically. Each section: `section_id`, `title`, `tone`, `summary`, `nodes`.
  Use `nodes` for hierarchical disclosure (N levels). Each node may contain child nodes and leaf `blocks`.
  Use `blocks` on a section only as fallback when hierarchy is unnecessary.
  Use node `disclosure_mode` + `default_open` to control how much Hide/Show UI appears.
  Use `inline` for lightweight containers; reserve `collapsible` for dense content.
  Keep nesting shallow (max depth 2) unless deeper drill-down is truly needed.
  Avoid wrapper nodes that contain only one short block and no children.
  Set `tone` to reflect the overall health signal of the section:
  "good" (on track, positive trend), "warning" (monitor, mild concern), "danger" (action needed, elevated risk), "neutral" (informational, no clear signal).
  Schema `tone` values are exactly good/warning/danger/neutral; never use "info" or "accent" as a tone.
  This drives the color of the section header in the UI — use it meaningfully.
- Set `summary` to one short sentence for collapsed display.

### Volume Targets
- Prefer 3-4 top-level sections when the source has distinct themes; use more or fewer if that better preserves important context.
- Prefer 1-2 focused blocks per section, but include extra blocks or light nesting when needed to retain meaningful evidence, guardrails, or rationale.
- Flat structure preferred — avoid nested disclosure trees unless genuinely needed.
- The athlete's default view shows ONLY `headline_brief` + `coach_action` + `dashboard_kpis`.
  Sections are agent context and drill-down — keep them scannable, but information-complete.

### Block Design
- Prefer multiple small, focused blocks over one monolithic block per section.
- Use `.callout-good / .callout-warning / .callout-danger / .callout-info / .callout-accent` for CSS highlights inside `content_html`.
  These CSS classes are independent of schema `tone`; `tone` still only accepts good/warning/danger/neutral.
- Use `.table` with `.domain-chip` and `.badge-*` for metric comparisons (max 4 columns).
- Use `.kpi-card` inside `.grid .grid--3` for dense metric displays.
- Use `.grid .grid--2` for side-by-side insights.
- Use `.card` and `.metric-card` for standalone metrics.
- Use `.big-stat` inside `.card` for hero numbers.
- Use `.quote` for risk signatures or key risk patterns.
- Use `<ul>`, `<ol>`, `<strong>`, `<em>` for text structure.

### Gold Standard Example — metric table with domain chips
```html
<table class="table">
  <thead><tr><th>Metric</th><th>Value</th><th>Domain</th><th>Status</th></tr></thead>
  <tbody>
    <tr>
      <td><strong>CTL</strong></td>
      <td>72</td>
      <td><span class="domain-chip domain-load">Load</span></td>
      <td><span class="badge badge-good">Good</span></td>
    </tr>
    <tr>
      <td><strong>HRV Trend</strong></td>
      <td>down -8%</td>
      <td><span class="domain-chip domain-recovery">Recovery</span></td>
      <td><span class="badge badge-warn">Watch</span></td>
    </tr>
    <tr>
      <td><strong>Sleep Score</strong></td>
      <td>71%</td>
      <td><span class="domain-chip domain-body">Body</span></td>
      <td><span class="badge badge-warn">Watch</span></td>
    </tr>
  </tbody>
</table>
```

### Gold Standard Example — risk signature
```html
<div class="quote">
  High ATL + declining HRV + poor sleep = elevated injury risk window. \
Protect the next 48-72h.
</div>
```

### Gold Standard Example — insight callout
```html
<div class="callout-accent">
  <strong>Key insight:</strong> aerobic base is solid but recovery capacity is the \
limiting factor right now. Prioritize sleep and Z1 before any intensity.
</div>
```

### Stable IDs
- Section IDs: descriptive kebab-case (e.g., "chronic-load", "recovery-status").
- Block keys: unique within section, kebab-case (e.g., "load-table", "sleep-insight")."""
)

ANALYSIS_FORMATTER_USER_PROMPT = """Convert this performance report into a `UiAnalysis` object.

## Source Markdown
```markdown
{synthesis_result}
```

## Training Evidence
```json
{training_evidence}
```

## Priority 1 — Surface fields (what the athlete reads)
- `headline_brief`: 2-3 sentence coaching synthesis. This is the FIRST thing they read.
  Answer: "what matters most right now?" Direct coaching voice.
- `coach_action`: Single directive — the #1 thing to do TODAY. Commanding voice.
  Example: "Protect sleep through Thursday — HRV is trending down."
- `dashboard_kpis`: 3-6 curated metrics for the top row. Order by salience, not domain.
  Include `trend_points` for sparklines where data supports it.

## Priority 2 — Structured metadata
- `kpis`: Full KPI inventory. Set `domain` (load/recovery/performance/body/sleep) and `status`.
- `sections`: Prefer 3-4 focused sections for drill-down context. Keep blocks concise, but do not drop meaningful evidence or guardrails for the sake of brevity.
  Set `tone` and `summary` for section headers.

## Formatting
- Use `.badge-*`, `.domain-chip`, `.callout-*`, `.table` in blocks.
- Keep blocks concise — one insight per block, not a wall of content.
"""


async def analysis_formatter_node(state: TrainingAnalysisState) -> dict:
    logger.info("Starting analysis formatter node")

    synthesis_result = state.get("synthesis_result") or ""
    if not synthesis_result:
        logger.warning("No synthesis result to format")
        return {}

    agent_start_time = datetime.now()
    analysis_id = f"analysis_{state.get('user_id', 'user')}_{uuid.uuid4().hex[:10]}"

    base_llm = ModelSelector.get_llm(AgentRole.ANALYSIS_FORMATTER)
    llm_with_structure = base_llm.with_structured_output(LlmAnalysis, method="function_calling")

    async def call_formatter():
        return await llm_with_structure.ainvoke(
            [
                {"role": "system", "content": ANALYSIS_FORMATTER_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": ANALYSIS_FORMATTER_USER_PROMPT.format(
                        synthesis_result=synthesis_result,
                        training_evidence=json.dumps(state.get("training_data", {}), indent=2),
                    ),
                },
            ]
        )

    async def node_execution():
        llm_result = await retry_with_backoff(call_formatter, AI_ANALYSIS_CONFIG, "Analysis Formatting")

        analysis_blocks = UiAnalysis(
            **llm_result.model_dump(),
            analysis_id=analysis_id,
            athlete_name=state["athlete_name"],
            created_at=datetime.now().isoformat(),
        )

        execution_time = (datetime.now() - agent_start_time).total_seconds()
        log_node_completion("Analysis formatting", execution_time)

        return {
            "analysis_blocks": sanitize_analysis(analysis_blocks),
            "costs": [create_cost_entry("analysis_formatter", execution_time)],
        }

    return await execute_node_with_error_handling(
        node_name="Analysis formatter",
        node_function=node_execution,
        error_message_prefix="Analysis formatting failed",
    )
