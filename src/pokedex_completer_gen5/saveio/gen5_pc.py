from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from pokedex_completer_gen5.dex.national_species import national_species_name
from pokedex_completer_gen5.saveio.gen5_pk5 import PK5_BOXED_SIZE, parse_pk5

BOX_COUNT = 24
BOX_SLOTS = 30
BOX_STRIDE = 0x1000
PC_SLOTS = BOX_COUNT * BOX_SLOTS
EMPTY_FILLER_PREFIX = bytes.fromhex("491c036eaa3189aa")


def is_empty_filler(raw: bytes) -> bool:
    # Early BW saves appear to use a repeated invalid-looking placeholder for empty PC slots.
    # It is not a valid PK5, but it repeats across box storage like wallpaper from hell.
    return raw.startswith(EMPTY_FILLER_PREFIX)


def species_name(species_id: int) -> str:
    return national_species_name(species_id)


def inspect_pc(data: bytes, base: int, verbose: bool) -> Counter[int]:
    counts: Counter[int] = Counter()
    empty_zero = 0
    empty_filler = 0
    invalid = 0

    for box_index in range(BOX_COUNT):
        box_start = base + box_index * BOX_STRIDE
        for box_slot_index in range(BOX_SLOTS):
            start = box_start + box_slot_index * PK5_BOXED_SIZE
            raw = data[start : start + PK5_BOXED_SIZE]
            if len(raw) < PK5_BOXED_SIZE:
                invalid += 1
                continue
            parsed = parse_pk5(raw)
            box = box_index + 1
            box_slot = box_slot_index + 1
            if parsed.is_empty:
                empty_zero += 1
                continue
            if is_empty_filler(raw):
                empty_filler += 1
                continue
            if parsed.checksum_valid and parsed.plausible_species:
                counts[parsed.species_id] += 1
                if verbose:
                    print(
                        f"  Box {box:02d} Slot {box_slot:02d}: "
                        f"{species_name(parsed.species_id)} ({parsed.species_id}) "
                        f"pid=0x{parsed.pid:08X} checksum=0x{parsed.checksum:04X}"
                    )
            else:
                invalid += 1
                if verbose and invalid <= 20:
                    print(
                        f"  Box {box:02d} Slot {box_slot:02d}: invalid/non-empty-looking "
                        f"species={parsed.species_id} checksum_valid={parsed.checksum_valid} "
                        f"pid=0x{parsed.pid:08X} head={raw[:8].hex()}"
                    )

    print(f"pc_base=0x{base:05X}")
    print(f"  valid_mons={sum(counts.values())}")
    print(f"  empty_zero={empty_zero}")
    print(f"  empty_filler={empty_filler}")
    print(f"  invalid_other={invalid}")
    return counts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only Gen 5 PC inspector for BW-style saves.")
    parser.add_argument("save_path", type=Path)
    parser.add_argument("--base", type=lambda value: int(value, 0), default=0x400)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data = args.save_path.read_bytes()
    print(f"save={args.save_path}")
    print(f"size={len(data)}")
    counts = inspect_pc(data, args.base, args.verbose)
    print("species_counts:")
    for species_id, count in sorted(counts.items()):
        print(f"  {species_id:03d}\t{count}\t{species_name(species_id)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
