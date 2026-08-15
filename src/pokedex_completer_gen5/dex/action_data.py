from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActionHint:
    acquire: str
    evolve: str = ""
    item: str = ""
    caveat: str = ""


# Initial route/action hints. Keep this table conservative and grow it with verified data.
# The generic method string in unova_data.py remains the fallback.
ACTION_HINTS_BY_NATIONAL: dict[int, ActionHint] = {
    506: ActionHint(
        acquire="Catch Lillipup early in Unova routes, or breed from any Lillipup-line member.",
        evolve="Lillipup -> Herdier -> Stoutland by level-up.",
    ),
    543: ActionHint(
        acquire="Catch Venipede in forest/bug-route areas when available, or breed from Venipede-line member.",
        evolve="Venipede -> Whirlipede -> Scolipede by level-up.",
    ),
    649: ActionHint(
        acquire="Event/mythical. If already present, keep it; otherwise treat as not normally obtainable.",
        caveat="Cannot breed.",
    ),
}


def action_hint_for_national(national_id: int) -> ActionHint | None:
    return ACTION_HINTS_BY_NATIONAL.get(national_id)
