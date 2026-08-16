from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

from pokedex_completer_gen5.runtime import ensure_runtime_dirs

_SAFE_NAME = re.compile(r"[^A-Za-z0-9_.-]+")


def safe_artifact_name(name: str) -> str:
    cleaned = _SAFE_NAME.sub("-", name.strip()).strip("-._")
    return cleaned or "artifact"


def timestamp_prefix() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def screenshot_path(name: str = "screen") -> Path:
    paths = ensure_runtime_dirs()
    return (paths.screenshots / f"{timestamp_prefix()}-{safe_artifact_name(name)}.png").resolve()


def checkpoint_path(name: str) -> Path:
    paths = ensure_runtime_dirs()
    return (paths.checkpoints / f"{timestamp_prefix()}-{safe_artifact_name(name)}.State").resolve()
