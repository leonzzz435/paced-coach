from services.ai.ai_settings import AgentRole

from .data_summarizer_node import create_data_summarizer_node
from .training_data_projection import project_physiology_data

PHYSIOLOGY_SUMMARIZER_SYSTEM_PROMPT = """## Goal
Extract and structure physiological and recovery data with factual precision.
## Principles
- Be objective: Present data without interpretation.
- Be precise: Preserve exact metrics and units.
- Be structured: Present overlapping metrics from different sources side-by-side by date."""

PHYSIOLOGY_SUMMARIZER_USER_PROMPT = """## Task
Objectively describe the athlete's physiological state and recovery patterns.

## Constraints
- STRICTLY NO interpretation or coaching advice.
- Use transparent compression for long sequences.
- When multiple sources provide overlapping metrics (for example, WHOOP sleep plus other profile/body metrics), present them side-by-side by date or source.
- If only activity-derived proxy signals are present, label them explicitly as proxy signals rather than measured biometrics.

## Required Structure
1. **Coverage**: sources present, time windows, gaps, and evidence-profile limits.
2. **Sleep**: duration, stages, quality scores from each source. Side-by-side table when more than one source contributes.
3. **Recovery & Readiness**: measured recovery scores, HRV, resting HR, SpO2, skin temperature, stress, body battery.
4. **Proxy-Only Recovery Signals**: activity-derived stress/load summaries that may inform recovery uncertainty but are not biometrics.
5. **Body Metrics**: height, weight, max heart rate if available.
6. **Data Quality Notes**: gaps, suspicious values, outliers.

## Input Data
```json
{data}
```"""


extract_physiology_data = project_physiology_data


physiology_summarizer_node = create_data_summarizer_node(
    node_name="Physiology Summarizer",
    agent_role=AgentRole.SUMMARIZER,
    data_extractor=extract_physiology_data,
    state_output_key="physiology_summary",
    agent_type="physiology_summarizer",
    system_prompt=PHYSIOLOGY_SUMMARIZER_SYSTEM_PROMPT,
    user_prompt=PHYSIOLOGY_SUMMARIZER_USER_PROMPT,
)
