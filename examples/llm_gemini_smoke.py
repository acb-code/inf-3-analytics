"""Gemini smoke test: direct API call.

Run:
  uv run python examples/llm_gemini_smoke.py

Notes:
- Loads .env from the repo root.
- Requires GEMINI_API_KEY or GOOGLE_API_KEY to be set.
- Default model: gemini-3-flash-preview
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
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY is not set. Check your .env.")


def run_direct(model: str, question: str) -> None:
    from google import genai

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=question,
    )
    text = response.text or ""
    print("Direct API response:")
    print(text.strip() or "<empty response>")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gemini smoke test")
    parser.add_argument(
        "--model",
        default="gemini-3-flash-preview",
        help="Model name (default: gemini-3-flash-preview)",
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
