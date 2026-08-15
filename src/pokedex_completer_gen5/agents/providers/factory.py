from __future__ import annotations

from pokedex_completer_gen5.agents.planner import PlannerProvider
from pokedex_completer_gen5.agents.providers.anthropic_provider import AnthropicPlannerProvider
from pokedex_completer_gen5.agents.providers.google_provider import GooglePlannerProvider
from pokedex_completer_gen5.agents.providers.openai_provider import OpenAIPlannerProvider


def create_planner_provider(name: str, model: str | None = None) -> PlannerProvider:
    normalized = name.lower().strip()
    if normalized == "openai":
        return OpenAIPlannerProvider(model=model or "gpt-4.1-mini")
    if normalized == "anthropic":
        return AnthropicPlannerProvider(model=model or "claude-3-5-haiku-latest")
    if normalized == "google":
        return GooglePlannerProvider(model=model or "gemini-2.0-flash")
    raise ValueError(f"Unknown planner provider: {name}")
