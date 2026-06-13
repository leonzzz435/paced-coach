import logging
from typing import Any

from services.ai.langgraph.state.training_analysis_state import TrainingAnalysisState

logger = logging.getLogger(__name__)


async def plot_resolution_node(state: TrainingAnalysisState) -> dict[str, Any]:
    logger.info("Starting plot resolution node")

    if not state.get("plotting_enabled", False):
        logger.info("Plotting disabled - skipping plot resolution")
        return {
            "plot_resolution_stats": {
                "total_references": 0,
                "resolved_count": 0,
                "missing_plots": [],
                "skipped": True,
                "reason": "plotting_disabled",
            },
        }

    try:
        logger.info("Plot resolution currently only supports analysis HTML exports; skipping")
        return {
            "plot_resolution_stats": {
                "total_references": 0,
                "resolved_count": 0,
                "missing_plots": [],
                "skipped": True,
                "reason": "not_supported",
            }
        }

    except Exception as exc:
        logger.exception("Plot resolution node failed")
        return {
            "errors": [f"Plot resolution failed: {exc!s}"],
        }
