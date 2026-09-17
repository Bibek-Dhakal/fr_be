import json
import os
from pathlib import Path

from openai import OpenAI


PROMPT_VERSION = "triage-v1"
PROMPT_PATH = Path(__file__).parents[1] / "prompts" / f"{PROMPT_VERSION}.md"


def load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def complete_triage(text: str) -> str:
    client = OpenAI(
        base_url=os.environ["LLM_BASE_URL"],
        api_key=os.environ["LLM_API_KEY"],
        timeout=30.0,
        max_retries=0,
    )
    response = client.chat.completions.create(
        model=os.environ["LLM_MODEL"],
        messages=[
            {"role": "system", "content": load_prompt()},
            {"role": "user", "content": json.dumps({"text": text})},
        ],
        temperature=0,
    )
    content = response.choices[0].message.content
    if not content:
        raise ValueError("The model returned an empty response")
    return content
