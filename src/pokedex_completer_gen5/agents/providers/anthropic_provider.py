from __future__ import annotations

import os


class AnthropicPlannerProvider:
    name = "anthropic"

    def __init__(self, model: str = "claude-3-5-haiku-latest") -> None:
        self.model = model

    def complete(self, prompt: str) -> str:
        try:
            from anthropic import Anthropic  # type: ignore[reportMissingImports]
        except ImportError as exc:  # pragma: no cover - optional dependency.
            raise RuntimeError("Install AI dependencies with: uv sync --extra ai") from exc

        if not os.getenv("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY is not configured")

        client = Anthropic()
        response = client.messages.create(
            model=self.model,
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}],
        )
        chunks: list[str] = []
        for block in response.content:
            text = getattr(block, "text", None)
            if isinstance(text, str):
                chunks.append(text)
        return "".join(chunks)
