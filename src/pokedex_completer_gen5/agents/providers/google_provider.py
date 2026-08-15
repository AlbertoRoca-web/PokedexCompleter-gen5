from __future__ import annotations

import os


class GooglePlannerProvider:
    name = "google"

    def __init__(self, model: str = "gemini-2.0-flash") -> None:
        self.model = model

    def complete(self, prompt: str) -> str:
        try:
            from google import genai
        except ImportError as exc:  # pragma: no cover - optional dependency.
            raise RuntimeError("Install AI dependencies with: uv sync --extra ai") from exc

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY is not configured")

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )
        return response.text or ""
