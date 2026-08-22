from __future__ import annotations

from typing import Any

import pytest

from pokedex_completer_gen5.ai import orchestrator
from pokedex_completer_gen5.ai.orchestrator import ModelCandidate, OrchestrationRequest


def test_configured_providers_detects_api_and_compatible_endpoints() -> None:
    env = {
        "OPENAI_API_KEY": "configured",
        "GOOGLE_API_KEY": "configured",
        "OPENAI_COMPATIBLE_BASE_URL": "http://127.0.0.1:11434/v1",
    }

    assert orchestrator.configured_providers(env) == ("openai", "google", "compatible")


def test_route_prefers_anthropic_for_architecture_audit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(orchestrator, "configured_providers", lambda: ("openai", "anthropic", "google"))
    calls: list[str] = []

    def fake_call(name: str, model: str | None, prompt: str) -> ModelCandidate:
        calls.append(name)
        return ModelCandidate(name, model or "test", True, "review result", 7)

    monkeypatch.setattr(orchestrator, "_call_provider", fake_call)
    result = orchestrator.orchestrate(OrchestrationRequest(prompt="Audit the architecture", mode="route"))

    assert calls == ["anthropic"]
    assert result.answer == "review result"


def test_ensemble_keeps_failures_as_warnings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(orchestrator, "configured_providers", lambda: ("openai", "anthropic"))
    candidates = [
        ModelCandidate("openai", "gpt", True, "## Safe plan\n- verify state", 10),
        ModelCandidate("anthropic", "claude", False, "", 12, "temporary failure"),
    ]
    monkeypatch.setattr(orchestrator, "_call_parallel", lambda names, model, prompt: candidates)

    result = orchestrator.orchestrate(OrchestrationRequest(prompt="Plan safely", mode="ensemble"))

    assert "Safe plan" in result.answer
    assert result.warnings == ("anthropic: temporary failure",)


def test_empty_prompt_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(orchestrator, "configured_providers", lambda: ("openai",))
    with pytest.raises(ValueError, match="Prompt is empty"):
        orchestrator.orchestrate(OrchestrationRequest(prompt="   "))


def test_orchestrator_rest_capabilities(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    from pokedex_completer_gen5.server.rest import app

    monkeypatch.setattr(
        "pokedex_completer_gen5.server.rest.orchestrator_capabilities",
        lambda: {
            "modes": ["single", "route", "ensemble", "review"],
            "configured_providers": ["openai", "google"],
            "browser_chat_automation": False,
        },
    )
    response = TestClient(app).get("/api/ai/orchestrator")

    assert response.status_code == 200
    payload: dict[str, Any] = response.json()
    assert payload["browser_chat_automation"] is False
    assert payload["modes"] == ["single", "route", "ensemble", "review"]
