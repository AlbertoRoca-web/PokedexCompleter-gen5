from __future__ import annotations

from pathlib import Path
from typing import Any

from pokedex_completer_gen5.dex.pc_living_dex import build_pc_living_dex_report
from pokedex_completer_gen5.domain.game_state import EmulatorState, semantic_state_from_bridge
from pokedex_completer_gen5.persistence.store import macro_reliability
from pokedex_completer_gen5.saveio.physical_report import build_save_payload


class PokedexCompleterService:
    def inspect_save(self, save_path: Path, game: str = "white", copy: str = "auto") -> dict[str, Any]:
        return build_save_payload(save_path, game, copy)

    def pc_living_dex_status(
        self,
        save_path: Path,
        game: str = "white",
        copy: str = "auto",
        scope: str = "regional",
        include_party: bool = True,
        target_policy: str = "game-regional",
    ) -> dict[str, Any]:
        payload = self.inspect_save(save_path, game, copy)
        return build_pc_living_dex_report(
            payload,
            game,
            scope=scope,
            include_party=include_party,
            target_policy=target_policy,
        ).to_dict()

    def semantic_emulator_state(self, raw_bridge_state: dict[str, Any]) -> EmulatorState:
        return semantic_state_from_bridge(raw_bridge_state)

    def macro_reliability(self, limit: int = 1000) -> list[dict[str, Any]]:
        return macro_reliability(limit=limit)


_service = PokedexCompleterService()


def service() -> PokedexCompleterService:
    return _service
