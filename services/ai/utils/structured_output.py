from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel


def coerce_structured_output[StructuredOutputT: BaseModel](
    response: Any, schema: type[StructuredOutputT]
) -> StructuredOutputT:
    if isinstance(response, schema):
        return response

    parsed_payload = _extract_parsed_payload(response)
    if parsed_payload is not None:
        return _validate_payload(parsed_payload, schema)

    return _validate_payload(response, schema)


def _extract_parsed_payload(response: Any) -> Any:
    output_parsed = getattr(response, "output_parsed", None)
    if output_parsed is not None:
        return output_parsed

    parsed_attr = getattr(response, "parsed", None)
    if parsed_attr is not None:
        return parsed_attr

    if isinstance(response, Mapping):
        parsed_value = response.get("parsed")
        if parsed_value is not None:
            return parsed_value

    additional_kwargs = getattr(response, "additional_kwargs", None)
    if isinstance(additional_kwargs, Mapping):
        parsed_value = additional_kwargs.get("parsed")
        if parsed_value is not None:
            return parsed_value

    return None


def _validate_payload[StructuredOutputT: BaseModel](payload: Any, schema: type[StructuredOutputT]) -> StructuredOutputT:
    if isinstance(payload, schema):
        return payload
    if isinstance(payload, BaseModel):
        return schema.model_validate(payload.model_dump(mode="json"))
    if isinstance(payload, Mapping):
        return schema.model_validate(dict(payload))
    return schema.model_validate(payload)
