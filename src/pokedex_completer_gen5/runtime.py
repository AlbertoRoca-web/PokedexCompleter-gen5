from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pokedex_completer_gen5.settings import get_settings


@dataclass(frozen=True)
class RuntimePaths:
    root: Path
    runs: Path
    screenshots: Path
    checkpoints: Path
    logs: Path
    db_path: Path


def runtime_paths() -> RuntimePaths:
    settings = get_settings().runtime
    root = settings.runtime_dir
    return RuntimePaths(
        root=root,
        runs=root / "runs",
        screenshots=root / "screenshots",
        checkpoints=root / "checkpoints",
        logs=root / "logs",
        db_path=settings.db_path,
    )


def ensure_runtime_dirs() -> RuntimePaths:
    paths = runtime_paths()
    for directory in (paths.root, paths.runs, paths.screenshots, paths.checkpoints, paths.logs, paths.db_path.parent):
        directory.mkdir(parents=True, exist_ok=True)
    return paths
