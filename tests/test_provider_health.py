from __future__ import annotations

from pokedex_completer_gen5.integrations.provider_health import provider_health_payload


def test_provider_health_reports_missing_without_values() -> None:
    payload = provider_health_payload({})

    assert payload["configured_count"] == 0
    assert payload["total_count"] == 6
    assert payload["providers"]["openai"]["status"] == "missing"


def test_provider_health_reports_configured_supabase_aliases() -> None:
    payload = provider_health_payload(
        {
            "OPENAI_API_KEY": "secret",
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_SECRET_KEY": "secret",
        }
    )

    assert payload["providers"]["openai"]["status"] == "configured"
    assert payload["providers"]["supabase"]["status"] == "configured"
    assert payload["configured_count"] == 2
