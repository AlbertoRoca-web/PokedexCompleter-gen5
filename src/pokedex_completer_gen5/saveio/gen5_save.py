from __future__ import annotations

import argparse
from pathlib import Path

from pokedex_completer_gen5.dex.game_profiles import supported_game_keys
from pokedex_completer_gen5.saveio.active_copy import choose_copy
from pokedex_completer_gen5.saveio.gen5_reader import (
    PhysicalMon,
    SaveCopyReport,
    read_party_mons,
    read_pc_mons,
    read_save_copy,
)
from pokedex_completer_gen5.saveio.physical_report import (
    build_save_output,
    build_save_payload,
    build_save_report,
    default_report_path,
    render_physical_summary,
    status_from_counts,
    write_save_report,
)

__all__ = [
    "PhysicalMon",
    "SaveCopyReport",
    "build_save_output",
    "build_save_payload",
    "build_save_report",
    "choose_copy",
    "default_report_path",
    "read_party_mons",
    "read_pc_mons",
    "read_save_copy",
    "render_physical_summary",
    "status_from_counts",
    "write_save_report",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only Gen 5 save to regional living dex report.")
    parser.add_argument("save_path", type=Path)
    parser.add_argument("--game", choices=supported_game_keys(), default="white")
    parser.add_argument(
        "--copy",
        choices=("auto", "0", "1"),
        default="auto",
        help="Save copy to use. auto picks matching copy 0 or the copy with more decoded physical mons.",
    )
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output, report = write_save_report(args.save_path, args.game, args.copy, args.output, args.format)
    print(report)
    print(f"Report written to: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
