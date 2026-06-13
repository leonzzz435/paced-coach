import uuid

from api.services import ai_run_costs


def test_capture_langsmith_run_costs_maps_extractor_payload(monkeypatch):
    class _FakeExtractor:
        def __init__(self):
            self.client = object()

        def extract_run_costs(self, run_id: str) -> dict:
            assert run_id == "root-123"
            return {
                "trace_id": "trace-123",
                "run_id": run_id,
                "total_cost_usd": 0.0123,
                "total_tokens": 456,
                "total_input_tokens": 300,
                "total_output_tokens": 156,
                "total_web_searches": 2,
                "model_breakdown": {
                    "gpt-5-mini": {
                        "cost_usd": 0.0123,
                        "total_tokens": 456,
                    }
                },
            }

    monkeypatch.setattr(ai_run_costs, "LangSmithCostExtractor", _FakeExtractor)

    snapshot = ai_run_costs.capture_langsmith_run_costs(
        ai_run_costs.AiTraceMetadata(
            project_name="paced_coach",
            trace_id="trace-123",
            root_run_id="root-123",
            run_name="daily_update",
        )
    )

    assert snapshot.cost_status == "captured"
    assert snapshot.total_cost_usd == 0.0123
    assert snapshot.total_tokens == 456
    assert snapshot.total_input_tokens == 300
    assert snapshot.total_output_tokens == 156
    assert snapshot.total_web_searches == 2
    assert snapshot.model_breakdown["gpt-5-mini"]["cost_usd"] == 0.0123


def test_snapshot_from_legacy_cost_summary_marks_empty_payload_missing():
    snapshot = ai_run_costs.snapshot_from_legacy_cost_summary(
        {"total_cost_usd": 0.0, "total_tokens": 0, "model_breakdown": {}}
    )

    assert snapshot.cost_status == "missing"
    assert snapshot.total_cost_usd is None
    assert snapshot.total_tokens is None


def test_build_ai_run_cost_record_carries_trace_and_source_metadata():
    user_id = uuid.uuid4()
    thread_id = uuid.uuid4()

    record = ai_run_costs.build_ai_run_cost_record(
        user_id=user_id,
        thread_id=thread_id,
        feature="coach_turn",
        source_type="coach_turn_run",
        source_id="turn-123",
        run_name="continuum_coach_turn",
        trace_metadata=ai_run_costs.AiTraceMetadata(
            project_name="paced_coach",
            trace_id="trace-123",
            root_run_id="root-123",
            run_name="continuum_coach_turn",
        ),
        cost_snapshot=ai_run_costs.AiRunCostSnapshot(
            cost_status="captured",
            total_cost_usd=0.02,
            total_tokens=900,
            total_input_tokens=600,
            total_output_tokens=300,
            total_web_searches=1,
            model_breakdown={"gpt-5-mini": {"total_tokens": 900}},
        ),
        source_metadata={"turn_seq_anchor": 14},
    )

    assert record.total_cost_usd is not None
    assert record.user_id == user_id
    assert record.thread_id == thread_id
    assert record.feature == "coach_turn"
    assert record.source_type == "coach_turn_run"
    assert record.source_id == "turn-123"
    assert record.langsmith_trace_id == "trace-123"
    assert record.langsmith_root_run_id == "root-123"
    assert float(record.total_cost_usd) == 0.02
    assert record.total_tokens == 900
    assert record.source_metadata == {"turn_seq_anchor": 14}
