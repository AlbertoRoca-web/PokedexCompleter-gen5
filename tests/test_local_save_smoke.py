from __future__ import annotations

from pathlib import Path

import pytest

from pokedex_completer_gen5.saveio.gen5_save import build_save_report

WHITE_SAVE = Path(r"D:\Users\alroc\Downloads\rolplete\POKEMON W.sav")
BLACK2_SAVE = Path(r"D:\alroc\codepup\POKEMON B2.sav")


@pytest.mark.skipif(not WHITE_SAVE.exists(), reason="local Pokémon White save fixture is not present")
def test_local_white_save_report_smoke() -> None:
    report = build_save_report(WHITE_SAVE, "white")
    assert "game_profile=white" in report
    assert "Unique species owned:" in report
    assert "Living Dex family checklist:" in report


@pytest.mark.skipif(not BLACK2_SAVE.exists(), reason="local Pokémon Black 2 save fixture is not present")
def test_local_black2_save_guardrail_smoke() -> None:
    report = build_save_report(BLACK2_SAVE, "black2")
    assert "game_profile=black2" in report
    assert "physical extraction worked" in report
    assert "refusing to silently use the wrong BW Unova checklist" in report
