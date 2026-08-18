from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from dotenv import dotenv_values


@dataclass
class OpenAIVisionPlannerProvider:
    model: str = "gpt-5-mini"
    api_key: str | None = None
    client: httpx.Client | None = None
    name: str = "openai-vision"

    def complete_with_image(self, prompt: str, image_path: Path) -> str:
        api_key = self.api_key or os.getenv("OPENAI_API_KEY") or _dotenv_key("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        client = self.client or httpx.Client(base_url="https://api.openai.com", timeout=180)
        response = client.post(
            "/v1/responses",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": self.model,
                "input": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": prompt},
                            {
                                "type": "input_image",
                                "image_url": _image_data_url(image_path),
                            },
                        ],
                    }
                ],
                "text": {"format": {"type": "json_object"}},
            },
        )
        response.raise_for_status()
        return _output_text(response.json())


def _image_data_url(path: Path) -> str:
    suffix = path.suffix.lower()
    media_type = "image/jpeg" if suffix in {".jpg", ".jpeg"} else "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{media_type};base64,{encoded}"


def _output_text(payload: dict[str, Any]) -> str:
    direct = payload.get("output_text")
    if isinstance(direct, str) and direct:
        return direct
    output = payload.get("output")
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    return str(part["text"])
    raise RuntimeError("OpenAI response did not contain output text")


def _dotenv_key(name: str) -> str | None:
    value = dotenv_values(".env").get(name)
    return value if isinstance(value, str) and value else None
