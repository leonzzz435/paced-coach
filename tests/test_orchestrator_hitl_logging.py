import logging

import pytest

from services.ai.langgraph.nodes.orchestrator_node import ConsoleInteractionProvider


@pytest.mark.unit
def test_console_interaction_provider_does_not_log_raw_answers(monkeypatch, caplog):
    provider = ConsoleInteractionProvider()
    sensitive_answer = "I had chest pain and my phone number is 555-0101"
    monkeypatch.setattr("builtins.input", lambda _prompt: sensitive_answer)

    questions = [
        {
            "agent": "metrics_expert",
            "question": {
                "message": "How did your recovery feel today?",
                "context": "Optional context",
            },
        }
    ]

    with caplog.at_level(logging.INFO, logger="services.ai.langgraph.nodes.orchestrator_node"):
        answers = provider.collect_answers(questions, "Analysis")

    assert answers[0]["answer"] == sensitive_answer
    assert sensitive_answer not in caplog.text
    assert "answer_chars=" in caplog.text
