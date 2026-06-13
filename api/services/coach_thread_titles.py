from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

from langchain_core.messages import HumanMessage, SystemMessage

from services.ai.ai_settings import AgentRole
from services.ai.model_config import ModelSelector

_TITLE_MAX_WORDS = 8
_TITLE_MAX_CHARS = 120
_TITLE_PROMPT = (
    "Generate a short coaching thread title.\n"
    "Rules:\n"
    "- Max 8 words.\n"
    "- Be specific to the athlete training topic.\n"
    "- No quotes.\n"
    "- Output title text only.\n"
)


def _to_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
            elif isinstance(item, str):
                parts.append(item)
        return " ".join(parts)
    return str(content)


def _normalize_title(raw_title: str) -> str | None:
    cleaned = re.sub(r"\s+", " ", raw_title).strip().strip("\"'`")
    if not cleaned:
        return None
    words = cleaned.split(" ")
    limited = " ".join(words[:_TITLE_MAX_WORDS]).strip()
    if not limited:
        return None
    return limited[:_TITLE_MAX_CHARS].strip()


async def generate_thread_title_from_exchange(*, user_message: str, coach_reply: str) -> str | None:
    try:
        llm = ModelSelector.get_llm(AgentRole.COACH_TRIAGE)
    except RuntimeError:
        return None

    response = await llm.ainvoke(
        [
            SystemMessage(content=_TITLE_PROMPT),
            HumanMessage(
                content=(
                    "Athlete:\n"
                    f"{user_message[:300]}\n\n"
                    "Coach:\n"
                    f"{coach_reply[:300]}"
                )
            ),
        ]
    )
    return _normalize_title(_to_text(response.content))


def derive_proactive_thread_title(alert_message: str) -> str:
    candidate = re.sub(r"\s+", " ", alert_message).strip()
    if not candidate:
        return "Coach Alert"
    first_sentence = candidate.split(".", maxsplit=1)[0].strip()
    if not first_sentence:
        return "Coach Alert"
    if len(first_sentence) > _TITLE_MAX_CHARS:
        return f"{first_sentence[:_TITLE_MAX_CHARS - 1].rstrip()}..."
    return first_sentence


def derive_weekly_recap_thread_title(anchor_utc: datetime, *, timezone: str = "UTC") -> str:
    date_label = anchor_utc.astimezone(ZoneInfo(timezone)).date().isoformat()
    return f"Weekly Recap - {date_label}"
