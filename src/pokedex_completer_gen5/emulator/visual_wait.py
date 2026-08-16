from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from pokedex_completer_gen5.emulator.artifacts import screenshot_path
from pokedex_completer_gen5.emulator.vision import analyze_screenshot
from pokedex_completer_gen5.persistence.store import persist_artifact

BridgeRequest = Callable[[str, dict[str, Any] | None], dict[str, Any]]


@dataclass(frozen=True)
class ScreenshotAttempt:
    attempt: int
    path: str
    response: dict[str, Any]
    analysis: dict[str, Any]
    artifact: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempt": self.attempt,
            "path": self.path,
            "response": self.response,
            "analysis": self.analysis,
            "artifact": self.artifact,
        }


@dataclass(frozen=True)
class InformativeScreenshotResult:
    ok: bool
    reason: str
    attempts: list[ScreenshotAttempt] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "reason": self.reason,
            "attempts": [attempt.to_dict() for attempt in self.attempts],
            "latest": self.attempts[-1].to_dict() if self.attempts else None,
        }


def capture_informative_screenshot(
    bridge_request: BridgeRequest,
    *,
    label: str = "visual-wait",
    max_attempts: int = 5,
    advance_frames: int = 30,
) -> InformativeScreenshotResult:
    attempts: list[ScreenshotAttempt] = []
    for attempt_number in range(1, max_attempts + 1):
        path = screenshot_path(f"{label}-{attempt_number}")
        response = bridge_request("screenshot", {"path": path.as_posix()})
        analysis: dict[str, Any]
        if path.exists():
            analysis = analyze_screenshot(path)
        else:
            analysis = {"visually_informative": False, "analysis_error": "screenshot file was not created"}
        artifact = persist_artifact("screenshot", path, {"response": response, "analysis": analysis, "label": label})
        attempt = ScreenshotAttempt(
            attempt=attempt_number,
            path=str(path),
            response=response,
            analysis=analysis,
            artifact=artifact,
        )
        attempts.append(attempt)
        if analysis.get("visually_informative") is True:
            return InformativeScreenshotResult(ok=True, reason="informative_screenshot_found", attempts=attempts)
        if attempt_number < max_attempts:
            bridge_request("frame_advance", {"frames": advance_frames})
    return InformativeScreenshotResult(ok=False, reason="no_informative_screenshot_before_timeout", attempts=attempts)
