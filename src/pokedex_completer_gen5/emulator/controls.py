from __future__ import annotations

from dataclasses import dataclass
from typing import Any

NDS_BUTTONS = (
    "A",
    "B",
    "X",
    "Y",
    "Up",
    "Down",
    "Left",
    "Right",
    "L",
    "R",
    "Start",
    "Select",
)

# BizHawk default keyboard bindings for the NDS controller, from defctrl.json.
NDS_DEFAULT_KEYBOARD = {
    "A": "X",
    "B": "Z",
    "X": "S",
    "Y": "A",
    "Up": "Up",
    "Down": "Down",
    "Left": "Left",
    "Right": "Right",
    "L": "W",
    "R": "E",
    "Start": "Enter",
    "Select": "Space",
}

# Semantic controls for Pokemon Gen 5. These are game intentions, not keyboard keys.
GEN5_ACTIONS = {
    "confirm": "A",
    "cancel": "B",
    "menu": "X",
    "registered-item": "Y",
    "start": "Start",
    "select": "Select",
    "up": "Up",
    "down": "Down",
    "left": "Left",
    "right": "Right",
    "l": "L",
    "r": "R",
}


@dataclass(frozen=True)
class ControlBinding:
    action: str
    button: str
    default_keyboard: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "button": self.button,
            "default_keyboard": self.default_keyboard,
        }


def normalize_button_or_action(value: str) -> str:
    cleaned = value.strip()
    if cleaned in NDS_BUTTONS:
        return cleaned
    lower = cleaned.lower()
    if lower in GEN5_ACTIONS:
        return GEN5_ACTIONS[lower]
    raise ValueError(f"Unsupported NDS button/action: {value}")


def controls_payload() -> dict[str, Any]:
    bindings = [
        ControlBinding(action=action, button=button, default_keyboard=NDS_DEFAULT_KEYBOARD.get(button)).to_dict()
        for action, button in GEN5_ACTIONS.items()
    ]
    return {
        "system": "NDS",
        "note": "Use virtual NDS buttons for automation, not human keyboard letters.",
        "buttons": list(NDS_BUTTONS),
        "default_keyboard": NDS_DEFAULT_KEYBOARD,
        "gen5_actions": bindings,
    }
