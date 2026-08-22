from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from pokedex_completer_gen5.dex.catchable_targets import build_catchable_inventory_report
from pokedex_completer_gen5.saveio.gen5_save import build_save_payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("save_path", type=Path, nargs="?", default=None)
    parser.add_argument("--game", default="white")
    parser.add_argument("--mode", default="direct", choices=("direct", "obtainable"))
    args = parser.parse_args()
    save_path = args.save_path or Path(os.environ["RLD_SAVE_PATH"])
    payload = build_save_payload(save_path, args.game, "auto")
    report = build_catchable_inventory_report(payload, args.game, mode=args.mode)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
