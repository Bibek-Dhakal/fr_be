import os

from openai import OpenAI


def main() -> None:
    client = OpenAI(
        base_url=os.environ["LLM_BASE_URL"],
        api_key=os.environ["LLM_API_KEY"],
        timeout=30.0,
        max_retries=0,
    )
    response = client.chat.completions.create(
        model=os.environ["LLM_MODEL"],
        messages=[{"role": "user", "content": "Reply with exactly the word: ready"}],
        temperature=0,
    )
    print(response.choices[0].message.content)


if __name__ == "__main__":
    main()
