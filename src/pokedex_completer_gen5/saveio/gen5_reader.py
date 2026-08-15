from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from pokedex_completer_gen5.saveio.gen5_pk5 import PK5_BOXED_SIZE, PK5_PARTY_SIZE, parse_pk5

BOX_COUNT = 24
BOX_SLOTS = 30
BOX_STRIDE = 0x1000
PARTY_SLOTS = 6
SAVE_COPY_STRIDE = 0x24000
PC_BASE_IN_COPY = 0x400
PARTY_BASE_IN_COPY = 0x18E00


@dataclass(frozen=True)
class PhysicalMon:
    species_id: int
    source: str
    slot_label: str
    pid: int
    checksum: int


@dataclass(frozen=True)
class SaveCopyReport:
    copy_index: int
    copy_base: int
    mons: tuple[PhysicalMon, ...]
    party_count_hint: int

    @property
    def counts(self) -> Counter[int]:
        return Counter(mon.species_id for mon in self.mons)


def read_pc_mons(data: bytes, copy_base: int) -> list[PhysicalMon]:
    mons: list[PhysicalMon] = []
    base = copy_base + PC_BASE_IN_COPY
    for box_index in range(BOX_COUNT):
        box_start = base + box_index * BOX_STRIDE
        for box_slot_index in range(BOX_SLOTS):
            start = box_start + box_slot_index * PK5_BOXED_SIZE
            raw = data[start : start + PK5_BOXED_SIZE]
            if len(raw) < PK5_BOXED_SIZE:
                continue
            parsed = parse_pk5(raw)
            if parsed.checksum_valid and parsed.plausible_species:
                mons.append(
                    PhysicalMon(
                        species_id=parsed.species_id,
                        source="pc",
                        slot_label=f"Box {box_index + 1:02d} Slot {box_slot_index + 1:02d}",
                        pid=parsed.pid,
                        checksum=parsed.checksum,
                    )
                )
    return mons


def read_party_mons(data: bytes, copy_base: int) -> tuple[int, list[PhysicalMon]]:
    mons: list[PhysicalMon] = []
    base = copy_base + PARTY_BASE_IN_COPY
    party_count_hint = int.from_bytes(data[base + 4 : base + 8], "little")
    for slot_index in range(PARTY_SLOTS):
        start = base + 8 + slot_index * PK5_PARTY_SIZE
        raw = data[start : start + PK5_PARTY_SIZE]
        if len(raw) < PK5_PARTY_SIZE:
            continue
        parsed = parse_pk5(raw)
        if parsed.checksum_valid and parsed.plausible_species:
            mons.append(
                PhysicalMon(
                    species_id=parsed.species_id,
                    source="party",
                    slot_label=f"Party Slot {slot_index + 1}",
                    pid=parsed.pid,
                    checksum=parsed.checksum,
                )
            )
    return party_count_hint, mons


def read_save_copy(data: bytes, copy_index: int) -> SaveCopyReport:
    copy_base = copy_index * SAVE_COPY_STRIDE
    pc_mons = read_pc_mons(data, copy_base)
    party_count_hint, party_mons = read_party_mons(data, copy_base)
    return SaveCopyReport(
        copy_index=copy_index,
        copy_base=copy_base,
        mons=tuple(pc_mons + party_mons),
        party_count_hint=party_count_hint,
    )
