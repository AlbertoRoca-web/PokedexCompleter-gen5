from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from pokedex_completer_gen5.autonomy.gameplay_agent import GameplayAction, GameplayObservation


@dataclass
class HttpGameplayEnvironment:
    client: httpx.Client
    movement_press_frames: int = 12
    button_press_frames: int = 4
    settle_frames: int = 90

    def observe(
        self,
        *,
        step: int,
        objective: str,
        recent_actions: tuple[GameplayAction, ...],
        repeated_frame_count: int,
    ) -> GameplayObservation:
        screenshot = self._get("/api/emulator/screenshot")
        semantic = self._get("/api/emulator/semantic-state")
        path = _artifact_path(screenshot)
        sha256 = _artifact_sha256(screenshot)
        if not sha256 and path.exists():
            sha256 = _sha256(path)
        return GameplayObservation(
            step=step,
            screenshot_path=path,
            screenshot_sha256=sha256,
            semantic_state=semantic,
            recent_actions=recent_actions,
            repeated_frame_count=repeated_frame_count,
            objective=objective,
        )

    def act(self, action: GameplayAction) -> None:
        frames = self.movement_press_frames if action in {"Up", "Down", "Left", "Right"} else self.button_press_frames
        press = self._post("/api/emulator/press", {"button": action, "frames": frames})
        if press.get("ok") is not True:
            raise RuntimeError(f"Emulator rejected action {action}: {press}")
        advance = self._post("/api/emulator/frame-advance", {"frames": self.settle_frames})
        if advance.get("ok") is not True:
            raise RuntimeError(f"Emulator frame advance failed after {action}: {advance}")

    def checkpoint(self, name: str) -> dict[str, Any]:
        return self._post("/api/emulator/checkpoint/save", {"name": name})

    def ensure_ready(self) -> dict[str, Any]:
        return self._post("/api/emulator/ensure-ready", {"relaunch_if_needed": True})

    def _get(self, path: str) -> dict[str, Any]:
        response = self.client.get(path)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError(f"Expected object response from {path}")
        return payload

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = self.client.post(path, json=payload)
        response.raise_for_status()
        result = response.json()
        if not isinstance(result, dict):
            raise RuntimeError(f"Expected object response from {path}")
        return result


def _artifact_path(payload: dict[str, Any]) -> Path:
    raw_path = payload.get("artifact_path") or payload.get("path")
    if not isinstance(raw_path, str) or not raw_path:
        raise RuntimeError(f"Screenshot response did not contain an artifact path: {payload}")
    return Path(raw_path)


def _artifact_sha256(payload: dict[str, Any]) -> str:
    artifact = payload.get("artifact")
    if not isinstance(artifact, dict):
        return ""
    value = artifact.get("sha256")
    return value if isinstance(value, str) else ""


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
