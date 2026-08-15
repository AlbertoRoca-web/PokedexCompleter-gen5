from __future__ import annotations

import os


class OpenAIPlannerProvider:
    name = "openai"

    def __init__(self, model: str = "gpt-4.1-mini") -> None:
        self.model = model

    def complete(self, prompt: str) -> str:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - optional dependency.
            raise RuntimeError("Install AI dependencies with: uv sync --extra ai") from exc

        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not configured")

        client = OpenAI()
        response = client.responses.create(
            model=self.model,
            input=prompt,
            text={"format": {"type": "json_object"}},
        )
        return response.output_text
