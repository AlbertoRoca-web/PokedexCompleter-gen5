from __future__ import annotations

from pokedex_completer_gen5.dex.nickname_generator import generate_safe_nickname, nickname_is_home_safe


def test_generated_nickname_is_deterministic_and_home_safe() -> None:
    nickname = generate_safe_nickname(seed=504)

    assert nickname == generate_safe_nickname(seed=504)
    assert nickname_is_home_safe(nickname)
    assert len(nickname) <= 10


def test_home_safe_nickname_rejects_urls_symbols_and_long_text() -> None:
    assert nickname_is_home_safe("free.com") is False
    assert nickname_is_home_safe("!!!") is False
    assert nickname_is_home_safe("WayTooLongName") is False
