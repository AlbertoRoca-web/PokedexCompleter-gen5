from __future__ import annotations

import hashlib
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from pokedex_completer_gen5.backend.supabase_client import create_supabase_client


@dataclass(frozen=True)
class DexReportRow:
    game_profile: str
    regional_dex_key: str | None
    planner_supported: bool
    selected_copy: int | None
    unique_species_owned: int | None
    missing_species_count: int | None
    save_sha256: str | None
    report_json: dict[str, Any]

    def to_insert_dict(self) -> dict[str, Any]:
        return {
            "game_profile": self.game_profile,
            "regional_dex_key": self.regional_dex_key,
            "planner_supported": self.planner_supported,
            "selected_copy": self.selected_copy,
            "unique_species_owned": self.unique_species_owned,
            "missing_species_count": self.missing_species_count,
            "save_sha256": self.save_sha256,
            "report_json": self.report_json,
        }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def path_leaf(value: str) -> str:
    """Return a file name from either Windows or POSIX path text.

    CI runs on Linux, but local reports may contain Windows paths like
    `D:\\alroc\\codepup\\rolo3\\POKEMON W.sav`. `Path(...).name` is OS-native,
    so Linux treats backslashes as normal characters. Pure path flavors avoid that
    tiny portable-code rake to the face.
    """
    candidates = (
        PureWindowsPath(value).name,
        PurePosixPath(value).name,
    )
    return min((candidate for candidate in candidates if candidate), key=len, default=value)


def sanitized_report_payload(payload: dict[str, Any]) -> dict[str, Any]:
    sanitized = deepcopy(payload)
    save_value = sanitized.get("save")
    if isinstance(save_value, str) and save_value:
        sanitized["save"] = path_leaf(save_value)
        sanitized["save_path_redacted"] = True
    return sanitized


def build_dex_report_row(payload: dict[str, Any], save_sha256: str | None = None) -> DexReportRow:
    dex_status = payload.get("dex_status")
    if not isinstance(dex_status, dict):
        dex_status = {}

    selected_copy = payload.get("selected_copy")
    return DexReportRow(
        game_profile=str(payload.get("game_profile", "unknown")),
        regional_dex_key=payload.get("regional_dex_key") if isinstance(payload.get("regional_dex_key"), str) else None,
        planner_supported=bool(payload.get("planner_supported", False)),
        selected_copy=selected_copy if isinstance(selected_copy, int) else None,
        unique_species_owned=_optional_int(dex_status.get("unique_species_owned")),
        missing_species_count=_optional_int(dex_status.get("missing_species_count")),
        save_sha256=save_sha256,
        report_json=sanitized_report_payload(payload),
    )


def store_dex_report(
    payload: dict[str, Any],
    save_sha256: str | None = None,
    client: Any | None = None,
) -> Any:
    supabase = client or create_supabase_client(use_service_role=True)
    row = build_dex_report_row(payload, save_sha256).to_insert_dict()
    return supabase.table("dex_reports").insert(row).execute()


def _optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) else None
