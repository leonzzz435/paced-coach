from services.ai.coach.athlete_model_agent import AthleteModelSummary


def test_athlete_model_summary_confidence_schema_is_object_array():
    schema = AthleteModelSummary.model_json_schema()
    confidence_schema = schema["properties"]["confidence_by_field"]
    assert confidence_schema["type"] == "array"
    items_schema = confidence_schema["items"]
    assert "$ref" in items_schema
