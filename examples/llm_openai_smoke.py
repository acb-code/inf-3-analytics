"""OpenAI smoke test: direct API call.

Run:
  uv run python examples/llm_openai_smoke.py

Notes:
- Loads .env from the repo root.
- Requires OPENAI_API_KEY to be set.
- Default model: gpt-5-mini
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_QUESTION = "What is the capital of France?"


def _load_env() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    load_dotenv(repo_root / ".env")


def _validate_env() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set. Check your .env or shell env.")


def run_direct(model: str, question: str) -> None:
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": question}],
    )
    text = response.choices[0].message.content or ""
    print("Direct API response:")
    print(text.strip() or "<empty response>")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OpenAI smoke test")
    parser.add_argument(
        "--model",
        default="gpt-5-mini",
        help="Model name (default: gpt-5-mini)",
    )
    parser.add_argument(
        "--question",
        default=DEFAULT_QUESTION,
        help="Prompt/question to send (default: 'What is the capital of France?')",
    )
    return parser.parse_args()


def main() -> int:
    _load_env()
    _validate_env()
    args = parse_args()
    run_direct(args.model, args.question)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
