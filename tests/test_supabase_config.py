from __future__ import annotations

import pytest

from pokedex_completer_gen5.backend.supabase_client import load_supabase_config


def test_load_supabase_config_accepts_publishable_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "publishable")

    config = load_supabase_config()

    assert config.url == "https://example.supabase.co"
    assert config.publishable_key == "publishable"


def test_load_supabase_config_can_require_service_role(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon")

    with pytest.raises(RuntimeError, match="SUPABASE_SERVICE_ROLE_KEY"):
        load_supabase_config(require_service_role=True)
