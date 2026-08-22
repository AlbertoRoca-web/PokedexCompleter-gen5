from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_EVOLUTION_KB = Path("data/knowledge/white-evolutions.jsonl")


def evolution_record(national: int, path: Path = DEFAULT_EVOLUTION_KB) -> dict[str, Any]:
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("national") == national:
            return record
    raise ValueError(f"No White evolution record for National #{national}")
