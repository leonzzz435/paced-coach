from services.ai.ai_settings import AgentRole

from .data_summarizer_node import create_data_summarizer_node
from .training_data_projection import project_metrics_data

extract_metrics_data = project_metrics_data


metrics_summarizer_node = create_data_summarizer_node(
    node_name="Metrics Summarizer",
    agent_role=AgentRole.SUMMARIZER,
    data_extractor=extract_metrics_data,
    state_output_key="metrics_summary",
    agent_type="metrics_summarizer",
)
