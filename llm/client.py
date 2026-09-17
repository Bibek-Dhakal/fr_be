import json
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path

from openai import APIStatusError, APITimeoutError, OpenAI


PROMPT_VERSION = "triage-v1"
PROMPT_PATH = Path(__file__).parents[1] / "prompts" / f"{PROMPT_VERSION}.md"


def load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def complete_triage(
    text: str,
    previous_output: str | None = None,
    validation_error: str | None = None,
    repair: bool = False,
) -> str:
    client = OpenAI(
        base_url=os.environ["LLM_BASE_URL"],
        api_key=os.environ["LLM_API_KEY"],
        timeout=30.0,
        max_retries=0,
    )
    user_content = json.dumps({"text": text})
    if previous_output is not None and validation_error is not None:
        user_content = (
            f"{user_content}\n\nPrevious answer rejected:\n{previous_output}\n"
            f"Validation error:\n{validation_error}\n"
            "Return only corrected JSON matching the schema."
        )

    model = os.environ["LLM_MODEL"]
    for attempt in range(3):
        started = time.perf_counter()
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": load_prompt()},
                    {"role": "user", "content": user_content},
                ],
                temperature=0,
            )
            content = response.choices[0].message.content
            if not content:
                raise ValueError("The model returned an empty response")
            usage = response.usage
            _log_cost(
                model=model,
                input_tokens=getattr(usage, "prompt_tokens", 0) if usage else 0,
                output_tokens=getattr(usage, "completion_tokens", 0) if usage else 0,
                duration_ms=round((time.perf_counter() - started) * 1000),
                repair=repair,
            )
            return content
        except (APITimeoutError, APIStatusError) as error:
            status_code = getattr(error, "status_code", None)
            retryable = isinstance(error, APITimeoutError) or status_code == 429 or (
                isinstance(status_code, int) and status_code >= 500
            )
            if not retryable or attempt == 2:
                raise
            time.sleep((2**attempt) + random.uniform(0, 0.25))


def _log_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    duration_ms: int,
    repair: bool,
) -> None:
    Path("logs").mkdir(exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt_version": PROMPT_VERSION,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "duration_ms": duration_ms,
        "repair": repair,
    }
    with Path("logs/cost.jsonl").open("a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(record) + "\n")
