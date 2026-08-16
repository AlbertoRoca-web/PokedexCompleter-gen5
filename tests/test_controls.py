from __future__ import annotations

import pytest

from pokedex_completer_gen5.emulator.controls import controls_payload, normalize_button_or_action


def test_gen5_menu_action_maps_to_nds_x_button() -> None:
    assert normalize_button_or_action("menu") == "X"
    assert normalize_button_or_action("confirm") == "A"
    assert normalize_button_or_action("cancel") == "B"


def test_direct_nds_buttons_are_allowed() -> None:
    assert normalize_button_or_action("Start") == "Start"
    assert normalize_button_or_action("Select") == "Select"


def test_unknown_button_or_action_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unsupported NDS button/action"):
        normalize_button_or_action("keyboard-s")


def test_controls_payload_documents_keyboard_s_as_nds_x() -> None:
    payload = controls_payload()
    assert payload["default_keyboard"]["X"] == "S"
    menu_binding = next(binding for binding in payload["gen5_actions"] if binding["action"] == "menu")
    assert menu_binding == {"action": "menu", "button": "X", "default_keyboard": "S"}
