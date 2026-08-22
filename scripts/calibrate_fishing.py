from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import httpx
from PIL import Image


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe deterministic fishing hook timing from a checkpoint.")
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--base-url", default="http://127.0.0.1:8787")
    parser.add_argument("--jitter-start", type=int, default=0)
    parser.add_argument("--jitter-stop", type=int, default=20)
    parser.add_argument("--hook-delay", type=int, default=300)
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Probe successive casts and stop at a bite RNG state.",
    )
    args = parser.parse_args()

    checkpoint = args.checkpoint.resolve()
    client = httpx.Client(base_url=args.base_url, timeout=180)
    if args.sequential:
        return _probe_sequential(client, checkpoint, args.jitter_stop, args.hook_delay)
    for jitter in range(args.jitter_start, args.jitter_stop + 1):
        _post(client, "/api/emulator/checkpoint/load", {"name": str(checkpoint)})
        if jitter:
            _post(client, "/api/emulator/frame-advance", {"frames": jitter})
        _post(client, "/api/emulator/press", {"button": "Y", "frames": 1})
        _post(client, "/api/emulator/frame-advance", {"frames": 30})
        _post(
            client,
            "/api/emulator/fishing/cast-hook",
            {"hook_delay_frames": args.hook_delay, "settle_frames": 60},
        )
        screenshot = client.get("/api/emulator/screenshot").json()
        path = Path(str(screenshot["artifact_path"]))
        text = _ocr_dialogue(path)
        print(f"jitter={jitter:02d} delay={args.hook_delay:03d} text={text!r} screenshot={path}")
    return 0


def _probe_sequential(client: httpx.Client, checkpoint: Path, attempts: int, hook_delay: int) -> int:
    _post(client, "/api/emulator/checkpoint/load", {"name": str(checkpoint)})
    for attempt in range(1, attempts + 1):
        before = _post(
            client,
            "/api/emulator/checkpoint/save",
            {"name": f"fishing-calibration-attempt-{attempt:03d}"},
        )
        _post(client, "/api/emulator/press", {"button": "Y", "frames": 1})
        _post(client, "/api/emulator/frame-advance", {"frames": 30})
        _post(
            client,
            "/api/emulator/fishing/cast-hook",
            {"hook_delay_frames": hook_delay, "settle_frames": 60},
        )
        screenshot = client.get("/api/emulator/screenshot").json()
        path = Path(str(screenshot["artifact_path"]))
        text = _ocr_dialogue(path)
        checkpoint_path = before.get("artifact_path")
        print(f"attempt={attempt:03d} text={text!r} checkpoint={checkpoint_path} screenshot={path}")
        normalized = text.lower()
        if "late" in normalized:
            print("Bite RNG state found; binary-search hook delay from the reported checkpoint.")
            return 0
        if "landed" in normalized or "wild" in normalized or "what will" in normalized:
            print("Encounter started; stop before battle controls and inspect the species manually.")
            return 0
        if "not even" not in normalized:
            print("Unknown screen; stop rather than issuing unsafe fishing or Surf inputs.")
            return 2
        _post(client, "/api/emulator/press", {"button": "A", "frames": 1})
        _post(client, "/api/emulator/frame-advance", {"frames": 30})
    return 1


def _post(client: httpx.Client, path: str, payload: dict[str, object]) -> dict[str, object]:
    response = client.post(path, json=payload)
    response.raise_for_status()
    return response.json()


def _ocr_dialogue(path: Path) -> str:
    crop_path = path.with_name(path.stem + "-dialogue.png")
    with Image.open(path) as image:
        image.crop((0, 140, 256, 192)).resize((768, 156)).save(crop_path)
    result = subprocess.run(
        ["tesseract", str(crop_path), "stdout", "--psm", "6"],
        check=False,
        capture_output=True,
        text=True,
    )
    crop_path.unlink(missing_ok=True)
    return " ".join(result.stdout.split())


if __name__ == "__main__":
    raise SystemExit(main())
