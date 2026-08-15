from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx

VOICE_MODES = ("off", "talk-to-me", "rubberduck")


@dataclass(frozen=True)
class VoiceConfig:
    mode: str
    realtime_ready: bool
    model: str
    instructions: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "realtime_ready": self.realtime_ready,
            "model": self.model,
            "instructions": self.instructions,
            "note": "Browser Realtime sessions use ephemeral credentials; API key is never exposed to browser.",
        }


def build_voice_config(mode: str = "off") -> VoiceConfig:
    if mode not in VOICE_MODES:
        raise ValueError(f"Unsupported voice mode: {mode}")
    return VoiceConfig(
        mode=mode,
        realtime_ready=bool(os.getenv("OPENAI_API_KEY")) and mode != "off",
        model=os.getenv("OPENAI_REALTIME_MODEL", "gpt-realtime"),
        instructions=voice_instructions(mode),
    )


def create_realtime_session(mode: str = "talk-to-me") -> dict[str, Any]:
    config = build_voice_config(mode)
    if mode == "off":
        raise ValueError("Voice mode must not be off when creating a Realtime session")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    response = httpx.post(
        "https://api.openai.com/v1/realtime/sessions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": config.model,
            "voice": os.getenv("OPENAI_REALTIME_VOICE", "alloy"),
            "instructions": config.instructions,
        },
        timeout=20,
    )
    response.raise_for_status()
    decoded = response.json()
    if not isinstance(decoded, dict):
        raise RuntimeError("Realtime session response must be a JSON object")
    return decoded


def voice_instructions(mode: str) -> str:
    if mode == "talk-to-me":
        return (
            "Narrate important emulator and Living Dex progress to Alberto. "
            "Be concise, playful, and do not issue emulator actions directly."
        )
    if mode == "rubberduck":
        return (
            "Commentate observations and send claims to a validator before action. "
            "Highlight rare encounters, route progress, and suspicious uncertainty."
        )
    return "Voice copilot disabled."
