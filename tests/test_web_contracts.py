import pytest


@pytest.mark.unit
def test_analysis_run_response_includes_job_id_key():
    """Web contract: /api/analysis/run returns `job_id`.

    The Next.js client routes to `/app/jobs/<job_id>`.
    """
    from api.routers.analysis import AnalysisJobResponse

    schema = AnalysisJobResponse.model_json_schema()
    assert "properties" in schema
    assert "job_id" in schema["properties"]
