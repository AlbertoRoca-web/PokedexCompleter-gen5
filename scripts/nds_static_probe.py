from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / ".runtime" / "rom-analysis"
DEFAULT_ROM = Path(
    r"C:\Users\alroc\Downloads\Pokemon - White Version (USA, Europe) (NDSi Enhanced)"
    r"\Pokemon - White Version (USA, Europe) (NDSi Enhanced).nds"
)
KEYINPUT_ADDRESS = 0x04000130
INTERESTING_CONSTANTS = {
    "nds_keyinput_io": KEYINPUT_ADDRESS,
    "key_a": 0x0001,
    "key_b": 0x0002,
    "key_right": 0x0010,
    "key_left": 0x0020,
    "key_up": 0x0040,
    "key_down": 0x0080,
    "one_tile_pixels": 0x0010,
    "half_tile_pixels": 0x0008,
}


@dataclass(frozen=True)
class RomRegion:
    name: str
    rom_offset: int
    ram_address: int
    size: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "rom_offset": self.rom_offset,
            "hex_rom_offset": f"0x{self.rom_offset:X}",
            "ram_address": self.ram_address,
            "hex_ram_address": f"0x{self.ram_address:X}",
            "size": self.size,
            "hex_size": f"0x{self.size:X}",
        }


@dataclass(frozen=True)
class OverlayEntry:
    overlay_id: int
    ram_address: int
    ram_size: int
    bss_size: int
    static_init_start: int
    static_init_end: int
    file_id: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "overlay_id": self.overlay_id,
            "ram_address": self.ram_address,
            "hex_ram_address": f"0x{self.ram_address:X}",
            "ram_size": self.ram_size,
            "hex_ram_size": f"0x{self.ram_size:X}",
            "bss_size": self.bss_size,
            "static_init_start": self.static_init_start,
            "static_init_end": self.static_init_end,
            "file_id": self.file_id,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect Nintendo DS ROM ARM9/overlay metadata for static RAM clues.")
    parser.add_argument("--rom", default=str(_default_rom_path()))
    parser.add_argument("--max-hits-per-constant", type=int, default=200)
    args = parser.parse_args()

    rom_path = Path(args.rom)
    data = rom_path.read_bytes()
    header = parse_nds_header(data)
    regions = arm_regions_from_header(header)
    overlays = parse_overlay_table(data, header["arm9_overlay_offset"], header["arm9_overlay_size"])
    constant_hits = scan_regions_for_constants(
        data,
        regions=regions,
        constants=INTERESTING_CONSTANTS,
        max_hits_per_constant=args.max_hits_per_constant,
    )
    payload = {
        "ok": True,
        "created_at": datetime.now(UTC).isoformat(),
        "rom_path": str(rom_path),
        "header": header,
        "regions": [region.to_dict() for region in regions],
        "arm9_overlays": [overlay.to_dict() for overlay in overlays],
        "constant_hits": constant_hits,
        "next_reverse_engineering_steps": [
            "Load ARM9 and overlays into Ghidra/radare2 using the RAM addresses from this report.",
            "Start from KEYINPUT references, then walk xrefs into field/input/player movement functions.",
            "Correlate overlay RAM ranges with live ARM9 System Bus RAM scans around candidate movement structs.",
        ],
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-nds-static-probe.json"
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"output_path": str(output_path), **_summary(payload)}, indent=2))
    return 0


def _default_rom_path() -> Path:
    value = os.environ.get("POKEMON_WHITE_ROM")
    return Path(value) if value else DEFAULT_ROM


def parse_nds_header(data: bytes) -> dict[str, Any]:
    if len(data) < 0x160:
        raise ValueError("NDS ROM is too small to contain a valid header.")
    return {
        "game_title": data[0x000:0x00C].decode("ascii", errors="replace").rstrip("\0 "),
        "game_code": data[0x00C:0x010].decode("ascii", errors="replace"),
        "maker_code": data[0x010:0x012].decode("ascii", errors="replace"),
        "unit_code": data[0x012],
        "device_type": data[0x013],
        "device_capacity": data[0x014],
        "arm9_rom_offset": _u32le(data, 0x020),
        "arm9_entry_address": _u32le(data, 0x024),
        "arm9_ram_address": _u32le(data, 0x028),
        "arm9_size": _u32le(data, 0x02C),
        "arm7_rom_offset": _u32le(data, 0x030),
        "arm7_entry_address": _u32le(data, 0x034),
        "arm7_ram_address": _u32le(data, 0x038),
        "arm7_size": _u32le(data, 0x03C),
        "fnt_offset": _u32le(data, 0x040),
        "fnt_size": _u32le(data, 0x044),
        "fat_offset": _u32le(data, 0x048),
        "fat_size": _u32le(data, 0x04C),
        "arm9_overlay_offset": _u32le(data, 0x050),
        "arm9_overlay_size": _u32le(data, 0x054),
        "arm7_overlay_offset": _u32le(data, 0x058),
        "arm7_overlay_size": _u32le(data, 0x05C),
        "normal_card_control": _u32le(data, 0x060),
        "secure_card_control": _u32le(data, 0x064),
        "total_used_rom_size": _u32le(data, 0x080),
        "rom_header_size": _u32le(data, 0x084),
    }


def arm_regions_from_header(header: dict[str, Any]) -> list[RomRegion]:
    return [
        RomRegion(
            "arm9",
            int(header["arm9_rom_offset"]),
            int(header["arm9_ram_address"]),
            int(header["arm9_size"]),
        ),
        RomRegion(
            "arm7",
            int(header["arm7_rom_offset"]),
            int(header["arm7_ram_address"]),
            int(header["arm7_size"]),
        ),
    ]


def parse_overlay_table(data: bytes, table_offset: int, table_size: int) -> list[OverlayEntry]:
    overlays: list[OverlayEntry] = []
    if table_offset <= 0 or table_size <= 0:
        return overlays
    for offset in range(table_offset, table_offset + table_size, 32):
        if offset + 32 > len(data):
            break
        overlays.append(
            OverlayEntry(
                overlay_id=_u32le(data, offset + 0x00),
                ram_address=_u32le(data, offset + 0x04),
                ram_size=_u32le(data, offset + 0x08),
                bss_size=_u32le(data, offset + 0x0C),
                static_init_start=_u32le(data, offset + 0x10),
                static_init_end=_u32le(data, offset + 0x14),
                file_id=_u32le(data, offset + 0x18),
            )
        )
    return overlays


def scan_regions_for_constants(
    data: bytes,
    *,
    regions: list[RomRegion],
    constants: dict[str, int],
    max_hits_per_constant: int,
) -> dict[str, list[dict[str, Any]]]:
    hits: dict[str, list[dict[str, Any]]] = {name: [] for name in constants}
    for region in regions:
        blob = data[region.rom_offset : region.rom_offset + region.size]
        for name, value in constants.items():
            patterns = _constant_patterns(value)
            for pattern_name, pattern in patterns.items():
                start = 0
                while len(hits[name]) < max_hits_per_constant:
                    index = blob.find(pattern, start)
                    if index < 0:
                        break
                    hits[name].append(
                        {
                            "region": region.name,
                            "pattern": pattern_name,
                            "rom_offset": region.rom_offset + index,
                            "hex_rom_offset": f"0x{region.rom_offset + index:X}",
                            "ram_address": region.ram_address + index,
                            "hex_ram_address": f"0x{region.ram_address + index:X}",
                        }
                    )
                    start = index + 1
    return hits


def _constant_patterns(value: int) -> dict[str, bytes]:
    patterns = {"u32le": value.to_bytes(4, "little", signed=False)}
    if value <= 0xFFFF:
        patterns["u16le"] = value.to_bytes(2, "little", signed=False)
    if value <= 0xFF:
        patterns["u8"] = value.to_bytes(1, "little", signed=False)
    return patterns


def _summary(payload: dict[str, Any]) -> dict[str, Any]:
    header = payload["header"]
    constant_hits = payload["constant_hits"]
    return {
        "game_title": header["game_title"],
        "game_code": header["game_code"],
        "arm9_ram_address": f"0x{int(header['arm9_ram_address']):X}",
        "arm9_size": f"0x{int(header['arm9_size']):X}",
        "arm9_overlay_count": len(payload["arm9_overlays"]),
        "constant_hit_counts": {name: len(hits) for name, hits in constant_hits.items()},
    }


def _u32le(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "little", signed=False)


if __name__ == "__main__":
    raise SystemExit(main())
