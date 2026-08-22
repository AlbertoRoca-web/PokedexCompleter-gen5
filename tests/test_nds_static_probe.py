from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "nds_static_probe.py"
_SPEC = importlib.util.spec_from_file_location("nds_static_probe", _SCRIPT_PATH)
assert _SPEC is not None
assert _SPEC.loader is not None
nds_static_probe = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = nds_static_probe
_SPEC.loader.exec_module(nds_static_probe)


def _put_u32(data: bytearray, offset: int, value: int) -> None:
    data[offset : offset + 4] = value.to_bytes(4, "little")


def test_parse_nds_header_reads_arm_offsets() -> None:
    data = bytearray(0x200)
    data[0:12] = b"POKEMON W   "
    data[0x0C:0x10] = b"IRAO"
    _put_u32(data, 0x20, 0x4000)
    _put_u32(data, 0x28, 0x02000000)
    _put_u32(data, 0x2C, 0x1234)
    _put_u32(data, 0x50, 0x180)
    _put_u32(data, 0x54, 32)

    header = nds_static_probe.parse_nds_header(bytes(data))

    assert header["game_title"] == "POKEMON W"
    assert header["game_code"] == "IRAO"
    assert header["arm9_rom_offset"] == 0x4000
    assert header["arm9_ram_address"] == 0x02000000
    assert header["arm9_overlay_offset"] == 0x180


def test_parse_overlay_table_reads_entries() -> None:
    data = bytearray(0x220)
    _put_u32(data, 0x180, 7)
    _put_u32(data, 0x184, 0x02100000)
    _put_u32(data, 0x188, 0x400)
    _put_u32(data, 0x198, 42)

    overlays = nds_static_probe.parse_overlay_table(bytes(data), 0x180, 32)

    assert len(overlays) == 1
    assert overlays[0].overlay_id == 7
    assert overlays[0].ram_address == 0x02100000
    assert overlays[0].ram_size == 0x400
    assert overlays[0].file_id == 42


def test_scan_regions_for_constants_reports_rom_and_ram_addresses() -> None:
    data = bytearray(0x100)
    data[0x42:0x46] = (0x04000130).to_bytes(4, "little")
    region = nds_static_probe.RomRegion("arm9", 0x40, 0x02000000, 0x40)

    hits = nds_static_probe.scan_regions_for_constants(
        bytes(data),
        regions=[region],
        constants={"keyinput": 0x04000130},
        max_hits_per_constant=10,
    )

    assert hits["keyinput"] == [
        {
            "region": "arm9",
            "pattern": "u32le",
            "rom_offset": 0x42,
            "hex_rom_offset": "0x42",
            "ram_address": 0x02000002,
            "hex_ram_address": "0x2000002",
        }
    ]
