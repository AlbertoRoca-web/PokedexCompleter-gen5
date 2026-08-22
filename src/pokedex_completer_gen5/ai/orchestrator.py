from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Literal, Protocol

from pokedex_completer_gen5.agents.providers.factory import create_planner_provider

OrchestrationMode = Literal["single", "route", "ensemble", "review"]
ProviderName = Literal["openai", "anthropic", "google", "compatible"]

DEFAULT_MODELS: dict[str, str] = {
    "openai": os.getenv("AI_ORCHESTRATOR_OPENAI_MODEL", "gpt-4.1-mini"),
    "anthropic": os.getenv("AI_ORCHESTRATOR_ANTHROPIC_MODEL", "claude-3-5-haiku-latest"),
    "google": os.getenv("AI_ORCHESTRATOR_GOOGLE_MODEL", "gemini-2.0-flash"),
    "compatible": os.getenv("AI_MODEL_COMPATIBLE", "local-model"),
}


class TextProvider(Protocol):
    name: str

    def complete(self, prompt: str) -> str: ...


@dataclass(frozen=True)
class ModelCandidate:
    provider: str
    model: str
    ok: bool
    text: str
    latency_ms: int
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "ok": self.ok,
            "text": self.text,
            "latency_ms": self.latency_ms,
            "error": self.error,
        }


@dataclass(frozen=True)
class OrchestrationResult:
    mode: str
    answer: str
    selected_provider: str | None
    selected_model: str | None
    candidates: tuple[ModelCandidate, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "answer": self.answer,
            "selected_provider": self.selected_provider,
            "selected_model": self.selected_model,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class OrchestrationRequest:
    prompt: str
    mode: OrchestrationMode = "route"
    provider: ProviderName | None = None
    model: str | None = None
    system_prompt: str = ""
    max_providers: int = 3


class OpenAICompatibleProvider:
    name = "compatible"

    def __init__(self, model: str, base_url: str | None = None, api_key: str | None = None) -> None:
        self.model = model
        self.base_url = base_url or os.getenv("OPENAI_COMPATIBLE_BASE_URL", "http://127.0.0.1:11434/v1")
        self.api_key = api_key or os.getenv("OPENAI_COMPATIBLE_API_KEY", "local")

    def complete(self, prompt: str) -> str:
        try:
            from openai import OpenAI  # type: ignore[reportMissingImports]
        except ImportError as exc:  # pragma: no cover - optional dependency.
            raise RuntimeError("Install AI dependencies with: uv sync --extra ai") from exc
        client = OpenAI(base_url=self.base_url, api_key=self.api_key)
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content or ""


def configured_providers(env: dict[str, str] | None = None) -> tuple[str, ...]:
    values = os.environ if env is None else env
    available: list[str] = []
    if values.get("OPENAI_API_KEY"):
        available.append("openai")
    if values.get("ANTHROPIC_API_KEY"):
        available.append("anthropic")
    if values.get("GOOGLE_API_KEY"):
        available.append("google")
    if values.get("OPENAI_COMPATIBLE_BASE_URL"):
        available.append("compatible")
    return tuple(available)


def orchestrator_capabilities() -> dict[str, Any]:
    available = configured_providers()
    return {
        "modes": ["single", "route", "ensemble", "review"],
        "configured_providers": list(available),
        "default_models": DEFAULT_MODELS,
        "browser_chat_automation": False,
        "browser_chat_note": "Use authenticated provider APIs or an OpenAI-compatible local endpoint.",
    }


def orchestrate(request: OrchestrationRequest) -> OrchestrationResult:
    prompt = request.prompt.strip()
    if not prompt:
        raise ValueError("Prompt is empty")
    available = list(configured_providers())
    if request.provider and request.provider not in available:
        raise RuntimeError(f"Provider is not configured: {request.provider}")
    if not available:
        raise RuntimeError("No LLM providers are configured")

    full_prompt = _build_prompt(prompt, request.system_prompt)
    if request.mode == "single":
        name = request.provider or available[0]
        candidate = _call_provider(name, request.model, full_prompt)
        return _result_from_candidate(request.mode, candidate)
    if request.mode == "route":
        name = request.provider or _route_provider(prompt, available)
        candidate = _call_provider(name, request.model, full_prompt)
        return _result_from_candidate(request.mode, candidate)

    provider_names = available[: max(1, min(request.max_providers, 3))]
    candidates = _call_parallel(provider_names, request.model, full_prompt)
    successful = [candidate for candidate in candidates if candidate.ok]
    if not successful:
        errors = "; ".join(candidate.error or "unknown error" for candidate in candidates)
        raise RuntimeError(f"Every provider failed: {errors}")

    if request.mode == "review" and len(successful) >= 2:
        answer, selected = _review_candidate(prompt, successful[0], successful[1])
        return OrchestrationResult(
            mode=request.mode,
            answer=answer,
            selected_provider=selected.provider,
            selected_model=selected.model,
            candidates=tuple(candidates),
            warnings=tuple(_candidate_warnings(candidates)),
        )

    answer = _synthesize_candidates(prompt, successful)
    return OrchestrationResult(
        mode=request.mode,
        answer=answer,
        selected_provider="deterministic-synthesis",
        selected_model=None,
        candidates=tuple(candidates),
        warnings=tuple(_candidate_warnings(candidates)),
    )


def _build_prompt(prompt: str, system_prompt: str) -> str:
    safety = (
        "You are an advisory component in a Pokemon Living Dex automation system. "
        "Never claim an emulator action happened unless the supplied evidence proves it. "
        "Prefer deterministic, testable recommendations."
    )
    parts = [safety]
    if system_prompt.strip():
        parts.append(system_prompt.strip())
    parts.append(prompt)
    return "\n\n".join(parts)


def _route_provider(prompt: str, available: list[str]) -> str:
    lower = prompt.lower()
    if "image" in lower or "screenshot" in lower:
        preference = ("google", "openai", "anthropic", "compatible")
    elif len(prompt) > 6000 or any(word in lower for word in ("audit", "architecture", "review")):
        preference = ("anthropic", "google", "openai", "compatible")
    else:
        preference = ("openai", "google", "anthropic", "compatible")
    return next(name for name in preference if name in available)


def _make_provider(name: str, model: str | None) -> tuple[TextProvider, str]:
    selected_model = model or DEFAULT_MODELS[name]
    if name == "compatible":
        return OpenAICompatibleProvider(selected_model), selected_model
    return create_planner_provider(name, model=selected_model), selected_model


def _call_provider(name: str, model: str | None, prompt: str) -> ModelCandidate:
    provider, selected_model = _make_provider(name, model)
    started = perf_counter()
    try:
        text = provider.complete(prompt)
        return ModelCandidate(name, selected_model, True, text, int((perf_counter() - started) * 1000))
    except Exception as exc:  # Provider SDK/network errors become inspectable candidate failures.
        return ModelCandidate(name, selected_model, False, "", int((perf_counter() - started) * 1000), str(exc))


def _call_parallel(names: list[str], model: str | None, prompt: str) -> list[ModelCandidate]:
    results: dict[str, ModelCandidate] = {}
    with ThreadPoolExecutor(max_workers=len(names)) as executor:
        futures = {executor.submit(_call_provider, name, model, prompt): name for name in names}
        for future in as_completed(futures):
            results[futures[future]] = future.result()
    return [results[name] for name in names]


def _review_candidate(prompt: str, candidate: ModelCandidate, reviewer: ModelCandidate) -> tuple[str, ModelCandidate]:
    if len(reviewer.text.strip()) > len(candidate.text.strip()) and _looks_structured(reviewer.text):
        return reviewer.text, reviewer
    return candidate.text, candidate


def _synthesize_candidates(prompt: str, candidates: list[ModelCandidate]) -> str:
    if len(candidates) == 1:
        return candidates[0].text
    ranked = sorted(candidates, key=lambda item: (_looks_structured(item.text), len(item.text)), reverse=True)
    primary = ranked[0]
    agreements = _shared_terms([candidate.text for candidate in candidates])
    prefix = f"Consensus synthesis from {len(candidates)} providers; primary: {primary.provider}."
    if agreements:
        prefix += " Shared concepts: " + ", ".join(agreements[:8]) + "."
    return prefix + "\n\n" + primary.text


def _shared_terms(texts: list[str]) -> list[str]:
    stop = {"that", "this", "with", "from", "have", "will", "your", "into", "should", "about"}
    term_sets = [
        {word.strip(".,:;()[]{}\"'").lower() for word in text.split() if len(word.strip(".,:;()[]{}\"'")) >= 5} - stop
        for text in texts
    ]
    return sorted(set.intersection(*term_sets)) if term_sets else []


def _looks_structured(text: str) -> bool:
    stripped = text.strip()
    if stripped.startswith(("{", "[")):
        try:
            json.loads(stripped)
            return True
        except json.JSONDecodeError:
            pass
    return any(marker in text for marker in ("\n- ", "\n1.", "## ", "```"))


def _candidate_warnings(candidates: list[ModelCandidate]) -> list[str]:
    return [f"{candidate.provider}: {candidate.error}" for candidate in candidates if not candidate.ok]


def _result_from_candidate(mode: str, candidate: ModelCandidate) -> OrchestrationResult:
    if not candidate.ok:
        raise RuntimeError(candidate.error or f"{candidate.provider} failed")
    return OrchestrationResult(
        mode=mode,
        answer=candidate.text,
        selected_provider=candidate.provider,
        selected_model=candidate.model,
        candidates=(candidate,),
        warnings=tuple(),
    )
