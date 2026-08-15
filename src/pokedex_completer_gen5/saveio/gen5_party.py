from __future__ import annotations

import argparse
from pathlib import Path

from pokedex_completer_gen5.dex.national_species import national_species_name
from pokedex_completer_gen5.saveio.gen5_pk5 import PK5_PARTY_SIZE, parse_pk5

PARTY_SLOT_COUNT = 6


def describe_species(species_id: int) -> str:
    return national_species_name(species_id)


def inspect_party(data: bytes, base: int) -> tuple[int, list[str]]:
    lines: list[str] = []
    valid = 0
    party_count_hint = int.from_bytes(data[base : base + 4], "little") if base + 4 <= len(data) else -1
    lines.append(f"candidate_base=0x{base:05X} party_count_hint_u32={party_count_hint}")
    for slot in range(PARTY_SLOT_COUNT):
        start = base + 8 + slot * PK5_PARTY_SIZE
        raw = data[start : start + PK5_PARTY_SIZE]
        if len(raw) < PK5_PARTY_SIZE:
            lines.append(f"  slot {slot + 1}: out of bounds")
            continue
        parsed = parse_pk5(raw)
        if parsed.is_empty:
            lines.append(f"  slot {slot + 1}: empty")
        elif parsed.checksum_valid and parsed.plausible_species:
            valid += 1
            lines.append(
                f"  slot {slot + 1}: species={parsed.species_id:03d} "
                f"{describe_species(parsed.species_id)} pid=0x{parsed.pid:08X} checksum=0x{parsed.checksum:04X}"
            )
        else:
            lines.append(
                f"  slot {slot + 1}: invalid species={parsed.species_id} "
                f"checksum_valid={parsed.checksum_valid} pid=0x{parsed.pid:08X}"
            )
    return valid, lines


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only Gen 5 party inspector.")
    parser.add_argument("save_path", type=Path)
    parser.add_argument("--base", type=lambda value: int(value, 0), action="append")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data = args.save_path.read_bytes()
    bases = args.base or [0x18E00, 0x3CE00]
    print(f"save={args.save_path}")
    print(f"size={len(data)}")
    for base in bases:
        valid, lines = inspect_party(data, base)
        print("\n".join(lines))
        print(f"  valid_slots={valid}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
