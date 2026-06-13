import types

from pydantic import BaseModel

from services.ai.utils.structured_output import coerce_structured_output


class _SampleStructuredOutput(BaseModel):
    answer: str
    repetitions: int


def test_coerce_structured_output_returns_matching_model_instance():
    response = _SampleStructuredOutput(answer="steady progress", repetitions=5)

    result = coerce_structured_output(response, _SampleStructuredOutput)

    assert result is response


def test_coerce_structured_output_prefers_output_parsed_wrapper():
    parsed = _SampleStructuredOutput(answer="controlled discomfort", repetitions=6)
    response = types.SimpleNamespace(output_parsed=parsed, output=["raw wrapper should be ignored"])

    result = coerce_structured_output(response, _SampleStructuredOutput)

    assert result == parsed


def test_coerce_structured_output_reads_mapping_parsed_payload():
    response = {
        "parsed": {
            "answer": "no stagnation",
            "repetitions": 5,
        }
    }

    result = coerce_structured_output(response, _SampleStructuredOutput)

    assert result == _SampleStructuredOutput(answer="no stagnation", repetitions=5)


def test_coerce_structured_output_reads_additional_kwargs_parsed_payload():
    response = types.SimpleNamespace(
        additional_kwargs={
            "parsed": {
                "answer": "threshold stable",
                "repetitions": 4,
            }
        }
    )

    result = coerce_structured_output(response, _SampleStructuredOutput)

    assert result == _SampleStructuredOutput(answer="threshold stable", repetitions=4)
