from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

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
            "note": "Browser Realtime session minting is pending; API key is never exposed to browser.",
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
