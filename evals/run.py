import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from llm.parse import parse_triage_output
from llm.client import complete_triage


def main() -> None:
    cases = json.loads(Path("evals/cases.json").read_text(encoding="utf-8"))
    matched = 0
    failures: list[dict[str, str]] = []

    for case in cases:
        try:
            result = parse_triage_output(complete_triage(case["text"]))
            category = result.category.value
        except Exception as error:
            category = ""
            failures.append({"text": case["text"], "error": str(error)})
        if category == case["category"]:
            matched += 1
        elif not failures or failures[-1].get("text") != case["text"]:
            failures.append(
                {
                    "text": case["text"],
                    "expected": case["category"],
                    "actual": category,
                }
            )

    print(f"category_score={matched}/{len(cases)} ({matched / len(cases):.0%})")
    if failures:
        print(json.dumps(failures, indent=2))
    print(f"model={os.getenv('LLM_MODEL', 'not configured')}")


if __name__ == "__main__":
    main()
