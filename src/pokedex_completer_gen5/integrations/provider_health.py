from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderHealth:
    name: str
    configured: bool
    required_env: tuple[str, ...]
    optional_env: tuple[str, ...] = tuple()
    note: str = ""

    @property
    def status(self) -> str:
        return "configured" if self.configured else "missing"

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "status": self.status,
            "configured": self.configured,
            "required_env": list(self.required_env),
            "optional_env": list(self.optional_env),
            "note": self.note,
        }


@dataclass(frozen=True)
class EnvRequirement:
    name: str
    any_of: tuple[str, ...]
    optional: tuple[str, ...] = tuple()
    note: str = ""


def has_any_env(names: tuple[str, ...], env: Mapping[str, str]) -> bool:
    return any(bool(env.get(name)) for name in names)


def provider_health(env: Mapping[str, str] | None = None) -> list[ProviderHealth]:
    values = os.environ if env is None else env
    requirements = (
        EnvRequirement("openai", ("OPENAI_API_KEY",), note="LLM planner and tool-calling provider."),
        EnvRequirement("anthropic", ("ANTHROPIC_API_KEY",), note="Optional alternate LLM planner provider."),
        EnvRequirement("google", ("GOOGLE_API_KEY",), note="Optional Gemini planner or vision provider."),
        EnvRequirement(
            "openai-compatible",
            ("OPENAI_COMPATIBLE_BASE_URL",),
            optional=("OPENAI_COMPATIBLE_API_KEY",),
            note="Optional local or alternative OpenAI-compatible model server.",
        ),
        EnvRequirement("huggingface", ("HF_TOKEN",), note="Optional model, dataset, or Space hosting."),
        EnvRequirement("pypi", ("PYPI_API_TOKEN",), note="Manual package publishing only."),
        EnvRequirement(
            "supabase",
            ("SUPABASE_URL",),
            optional=(
                "SUPABASE_PUBLISHABLE_KEY",
                "SUPABASE_ANON_KEY",
                "SUPABASE_SECRET_KEY",
                "SUPABASE_SERVICE_ROLE_KEY",
            ),
            note="Backend storage. Needs URL plus at least one Supabase key for real API calls.",
        ),
    )

    health: list[ProviderHealth] = []
    for requirement in requirements:
        configured = has_any_env(requirement.any_of, values)
        if requirement.name == "supabase":
            configured = configured and has_any_env(requirement.optional, values)
        health.append(
            ProviderHealth(
                name=requirement.name,
                configured=configured,
                required_env=requirement.any_of,
                optional_env=requirement.optional,
                note=requirement.note,
            )
        )
    return health


def provider_health_payload(env: Mapping[str, str] | None = None) -> dict[str, object]:
    providers = provider_health(env)
    return {
        "providers": {provider.name: provider.to_dict() for provider in providers},
        "configured_count": sum(provider.configured for provider in providers),
        "total_count": len(providers),
    }
