from __future__ import annotations

import json
from pathlib import Path

import httpx

from pokedex_completer_gen5.autonomy.http_gameplay_environment import HttpGameplayEnvironment


def _response(payload: dict[str, object]) -> httpx.Response:
    return httpx.Response(200, content=json.dumps(payload).encode(), headers={"content-type": "application/json"})


def test_http_environment_observes_screenshot_and_semantic_state(tmp_path: Path) -> None:
    screenshot = tmp_path / "screen.png"
    screenshot.write_bytes(b"pixels")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/emulator/screenshot":
            return _response(
                {
                    "ok": True,
                    "artifact_path": str(screenshot),
                    "artifact": {"sha256": "abc"},
                }
            )
        if request.url.path == "/api/emulator/semantic-state":
            return _response({"mode": "overworld", "state": {"menu_open": False}})
        raise AssertionError(request.url.path)

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://test")
    environment = HttpGameplayEnvironment(client)

    observation = environment.observe(
        step=3,
        objective="reach route",
        recent_actions=("Right",),
        repeated_frame_count=1,
    )

    assert observation.screenshot_path == screenshot
    assert observation.screenshot_sha256 == "abc"
    assert observation.semantic_state["mode"] == "overworld"
    assert observation.recent_actions == ("Right",)


def test_http_environment_executes_one_action_then_settles() -> None:
    requests: list[tuple[str, dict[str, object]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        requests.append((request.url.path, payload))
        return _response({"ok": True})

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://test")
    environment = HttpGameplayEnvironment(client, movement_press_frames=7, settle_frames=11)

    environment.act("Right")

    assert requests == [
        ("/api/emulator/press", {"button": "Right", "frames": 7}),
        ("/api/emulator/frame-advance", {"frames": 11}),
    ]


def test_http_environment_saves_checkpoint() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/emulator/checkpoint/save"
        assert json.loads(request.content) == {"name": "step-1"}
        return _response({"ok": True, "artifact_path": "step-1.State"})

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://test")
    environment = HttpGameplayEnvironment(client)

    result = environment.checkpoint("step-1")

    assert result["ok"] is True
