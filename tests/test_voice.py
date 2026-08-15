from __future__ import annotations

import pytest

from pokedex_completer_gen5.agents.voice import create_realtime_session


def test_create_realtime_session_rejects_off_before_key_check(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ValueError, match="must not be off"):
        create_realtime_session("off")
