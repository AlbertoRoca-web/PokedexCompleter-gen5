from __future__ import annotations

import json
from pathlib import Path

import httpx

from pokedex_completer_gen5.agents.providers.openai_vision_provider import (
    OpenAIVisionPlannerProvider,
    _image_data_url,
    _output_text,
)


def test_image_data_url_encodes_png(tmp_path: Path) -> None:
    path = tmp_path / "screen.png"
    path.write_bytes(b"png")

    assert _image_data_url(path) == "data:image/png;base64,cG5n"


def test_output_text_supports_nested_responses_payload() -> None:
    payload = {"output": [{"content": [{"type": "output_text", "text": '{"actions":["Right"]}'}]}]}

    assert _output_text(payload) == '{"actions":["Right"]}'


def test_openai_vision_provider_sends_prompt_and_image(tmp_path: Path) -> None:
    image = tmp_path / "screen.png"
    image.write_bytes(b"pixels")
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers.get("authorization")
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            content=json.dumps({"output_text": '{"goal":"move","actions":["Right"],"rationale":"clear"}'}).encode(),
            headers={"content-type": "application/json"},
        )

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://api.openai.com")
    provider = OpenAIVisionPlannerProvider(api_key="test-key", client=client)

    result = provider.complete_with_image("inspect screenshot", image)

    assert result.startswith("{")
    assert captured["authorization"] == "Bearer test-key"
    payload = captured["payload"]
    assert isinstance(payload, dict)
    content = payload["input"][0]["content"]
    assert content[0]["text"] == "inspect screenshot"
    assert str(content[1]["image_url"]).startswith("data:image/png;base64,")
