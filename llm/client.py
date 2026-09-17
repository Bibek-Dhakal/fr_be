import json
import os
from pathlib import Path

from openai import OpenAI


PROMPT_VERSION = "triage-v1"
PROMPT_PATH = Path(__file__).parents[1] / "prompts" / f"{PROMPT_VERSION}.md"


def load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def complete_triage(
    text: str,
    previous_output: str | None = None,
    validation_error: str | None = None,
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

    response = client.chat.completions.create(
        model=os.environ["LLM_MODEL"],
        messages=[
            {"role": "system", "content": load_prompt()},
            {"role": "user", "content": user_content},
        ],
        temperature=0,
    )
    content = response.choices[0].message.content
    if not content:
        raise ValueError("The model returned an empty response")
    return content
