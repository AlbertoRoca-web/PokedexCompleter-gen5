from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

KNOWN_ROM_PROFILES: dict[str, dict[str, str]] = {}


def sha1_file(path: Path) -> str:
    digest = hashlib.sha1()  # noqa: S324 - ROM identity, not security.
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def identify_rom(path: Path | None, *, fallback_profile: str = "white-us-eu-rev0") -> dict[str, Any]:
    if path is None:
        return {"ok": False, "error": "ROM path is not configured", "profile": None}
    if not path.exists():
        return {"ok": False, "error": f"ROM not found: {path}", "path": str(path), "profile": None}
    sha1 = sha1_file(path)
    known = KNOWN_ROM_PROFILES.get(sha1)
    if known:
        return {"ok": True, "path": str(path), "sha1": sha1, "known": True, **known}
    return {
        "ok": True,
        "path": str(path),
        "sha1": sha1,
        "known": False,
        "profile": fallback_profile,
        "warning": "ROM SHA1 is not in the verified profile table yet; memory reads must remain fail-closed.",
    }
