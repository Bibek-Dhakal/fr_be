import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def quarantine_triage(
    text: str, raw_output: str, error: str, prompt_version: str
) -> None:
    log_path = Path("logs/quarantine.jsonl")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    record: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt_version": prompt_version,
        "input": text,
        "raw_output": raw_output,
        "error": error,
    }
    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(record) + "\n")
