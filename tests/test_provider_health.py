from __future__ import annotations

from typing import Any, cast

from pokedex_completer_gen5.integrations.provider_health import provider_health_payload


def providers(payload: dict[str, object]) -> dict[str, Any]:
    return cast(dict[str, Any], payload["providers"])


def test_provider_health_reports_missing_without_values() -> None:
    payload = provider_health_payload({})

    assert payload["configured_count"] == 0
    assert payload["total_count"] == 6
    assert providers(payload)["openai"]["status"] == "missing"


def test_provider_health_reports_configured_supabase_aliases() -> None:
    payload = provider_health_payload(
        {
            "OPENAI_API_KEY": "secret",
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_SECRET_KEY": "secret",
        }
    )

    assert providers(payload)["openai"]["status"] == "configured"
    assert providers(payload)["supabase"]["status"] == "configured"
    assert payload["configured_count"] == 2
