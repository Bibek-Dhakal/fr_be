import json

from pydantic import ValidationError

from llm.schema import TriageResult


def parse_triage_output(raw_output: str) -> TriageResult:
    cleaned = raw_output.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(lines[1:-1]).strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end < start:
        raise ValueError("Model output did not contain a JSON object")

    try:
        return TriageResult.model_validate(json.loads(cleaned[start : end + 1]))
    except (json.JSONDecodeError, ValidationError) as error:
        raise ValueError(str(error)) from error
