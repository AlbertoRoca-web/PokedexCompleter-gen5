from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image

from pokedex_completer_gen5.emulator.visual_wait import capture_informative_screenshot
from pokedex_completer_gen5.persistence.database import init_database, reset_database_engine_for_tests
from pokedex_completer_gen5.settings import get_settings


def configure_runtime(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("POKEDEX_RUNTIME_DIR", str(tmp_path / "runtime"))
    monkeypatch.setenv("POKEDEX_DB_PATH", str(tmp_path / "runtime" / "run.sqlite3"))
    get_settings.cache_clear()
    reset_database_engine_for_tests()
    init_database()


def test_capture_informative_screenshot_retries_blank_frame(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    configure_runtime(monkeypatch, tmp_path)
    calls: list[tuple[str, dict[str, Any] | None]] = []
    screenshot_count = 0

    def fake_bridge(method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        nonlocal screenshot_count
        calls.append((method, params))
        if method == "screenshot":
            screenshot_count += 1
            path = Path(str(params["path"]))  # type: ignore[index]
            if screenshot_count == 1:
                Image.new("RGB", (8, 8), "white").save(path)
            else:
                image = Image.new("RGB", (8, 8), "white")
                image.putpixel((0, 0), (0, 0, 0))
                image.save(path)
            return {"ok": True, "method": method}
        if method == "frame_advance":
            return {"ok": True, "method": method, "frames": params["frames"]}  # type: ignore[index]
        raise AssertionError(method)

    result = capture_informative_screenshot(fake_bridge, label="test", max_attempts=3, advance_frames=7)

    assert result.ok is True
    assert len(result.attempts) == 2
    assert calls[1] == ("frame_advance", {"frames": 7})
    assert result.attempts[-1].analysis["visually_informative"] is True


def test_capture_informative_screenshot_times_out_on_blank(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    configure_runtime(monkeypatch, tmp_path)

    def fake_bridge(method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if method == "screenshot":
            Image.new("RGB", (8, 8), "white").save(Path(str(params["path"])))  # type: ignore[index]
            return {"ok": True, "method": method}
        if method == "frame_advance":
            return {"ok": True, "method": method}
        raise AssertionError(method)

    result = capture_informative_screenshot(fake_bridge, label="blank", max_attempts=2, advance_frames=1)

    assert result.ok is False
    assert result.reason == "no_informative_screenshot_before_timeout"
    assert len(result.attempts) == 2
