from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from pokedex_completer_gen5.saveio.gen5_save import build_save_payload
from pokedex_completer_gen5.settings import get_settings

EXPECTED_GEN5_SAVE_SIZE = 512 * 1024


def main() -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Export a validated raw Gen 5 save for cartridge/2DS injection.")
    parser.add_argument("--source", type=Path, default=settings.emulator.bizhawk_white_saveram)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    source = args.source
    if not source.exists():
        raise FileNotFoundError(source)
    if source.stat().st_size != EXPECTED_GEN5_SAVE_SIZE:
        raise ValueError(f"Expected {EXPECTED_GEN5_SAVE_SIZE} bytes, got {source.stat().st_size}: {source}")
    output = args.output or _default_output_path()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    shutil.copy2(source, temporary)
    temporary.replace(output)
    payload = build_save_payload(output, "white", "auto")
    dex_status = payload.get("dex_status")
    if not isinstance(dex_status, dict):
        dex_status = {}
    result = {
        "ok": True,
        "source": str(source.resolve()),
        "output_path": str(output.resolve()),
        "size": output.stat().st_size,
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "game_profile": payload.get("game_profile"),
        "selected_copy": payload.get("selected_copy"),
        "unique_species_owned": dex_status.get("unique_species_owned"),
        "usage": "Transfer this raw .sav with FileZilla, then inject it with your 2DS save manager.",
    }
    print(json.dumps(result, indent=2))
    return 0


def _default_output_path() -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return Path(".runtime/cartridge-exports") / f"pokemon-white-{timestamp}.sav"


if __name__ == "__main__":
    raise SystemExit(main())
