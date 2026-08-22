from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx

from pokedex_completer_gen5.saveio.gen5_save import build_save_payload

DEFAULT_SIZE = 512 * 1024
DEFAULT_CHUNK_SIZE = 32 * 1024


def main() -> int:
    parser = argparse.ArgumentParser(description="Export raw Gen 5 SRAM while BizHawk remains open.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8787")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--size", type=int, default=DEFAULT_SIZE)
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    parser.add_argument("--consistency-attempts", type=int, default=3)
    args = parser.parse_args()

    output = args.output or _default_output_path()
    client = httpx.Client(base_url=args.base_url.rstrip("/"), timeout=180)
    domains = client.get("/api/emulator/memory/domains").json().get("domains", [])
    if "SRAM" not in domains:
        raise RuntimeError(f"Live emulator does not expose SRAM domain: {domains}")
    data = _read_consistent_sram(
        client,
        size=args.size,
        chunk_size=args.chunk_size,
        attempts=args.consistency_attempts,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_bytes(data)
    temporary.replace(output)
    save_payload = build_save_payload(output, "white", "auto")
    dex_status = save_payload.get("dex_status")
    if not isinstance(dex_status, dict):
        dex_status = {}
    payload = {
        "ok": True,
        "transfer_ready": True,
        "output_path": str(output.resolve()),
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "consistency": "two consecutive SRAM reads matched",
        "game_profile": save_payload.get("game_profile"),
        "selected_copy": save_payload.get("selected_copy"),
        "unique_species_owned": dex_status.get("unique_species_owned"),
        "usage": "Transfer this raw .sav with FileZilla and inject it using your 2DS save manager.",
    }
    print(json.dumps(payload, indent=2))
    return 0


def _read_consistent_sram(
    client: httpx.Client,
    *,
    size: int,
    chunk_size: int,
    attempts: int,
) -> bytes:
    for _ in range(attempts):
        first = _read_sram(client, size=size, chunk_size=chunk_size)
        second = _read_sram(client, size=size, chunk_size=chunk_size)
        if hashlib.sha256(first).digest() == hashlib.sha256(second).digest():
            return second
    raise RuntimeError("Live SRAM changed during every export attempt; stop game mutations and retry.")


def _read_sram(client: httpx.Client, *, size: int, chunk_size: int) -> bytes:
    output = bytearray()
    for address in range(0, size, chunk_size):
        length = min(chunk_size, size - address)
        response = client.post(
            "/api/emulator/memory/read-bytes",
            json={"domain": "SRAM", "address": address, "length": length},
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("ok") is not True:
            raise RuntimeError(f"SRAM read failed at 0x{address:X}: {payload}")
        chunk = bytes.fromhex(str(payload.get("hex", "")))
        if len(chunk) != length:
            raise RuntimeError(f"SRAM short read at 0x{address:X}: expected {length}, got {len(chunk)}")
        output.extend(chunk)
    return bytes(output)


def _default_output_path() -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return Path(".runtime/cartridge-exports") / f"pokemon-white-live-{timestamp}.sav"


if __name__ == "__main__":
    raise SystemExit(main())
