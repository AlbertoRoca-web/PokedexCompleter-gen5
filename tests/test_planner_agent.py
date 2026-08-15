from __future__ import annotations

from pokedex_completer_gen5.agents.planner import build_planner_prompt, plan_next_tasks


class FakeProvider:
    name = "fake"

    def complete(self, prompt: str) -> str:
        assert "Living Dex" in prompt
        return """
        {
          "summary": "Breed and evolve the Lillipup line first.",
          "tasks": [
            {
              "priority": 10,
              "task_type": "breed",
              "title": "Breed two extra Lillipup",
              "rationale": "The report owns one Lillipup and needs the full family.",
              "species_id": 506,
              "species_name": "Lillipup"
            }
          ]
        }
        """


def sample_report_payload() -> dict[str, object]:
    return {
        "game_profile": "white",
        "regional_dex_key": "bw_unova",
        "planner_supported": True,
        "selected_species_counts": [{"species_id": 506, "species_name": "Lillipup", "count": 1}],
        "dex_status": {
            "unique_species_owned": 2,
            "missing_species_count": 154,
            "missing": [
                {"regional": 14, "national": 507, "name": "Herdier"},
                {"regional": 15, "national": 508, "name": "Stoutland"},
            ],
        },
    }


def test_build_planner_prompt_contains_compact_report() -> None:
    prompt = build_planner_prompt(sample_report_payload())

    assert "Lillipup" in prompt
    assert "missing_preview" in prompt
    assert "Return strict JSON only" in prompt


def test_plan_next_tasks_parses_provider_json() -> None:
    result = plan_next_tasks(sample_report_payload(), FakeProvider())

    assert result.provider == "fake"
    assert result.summary == "Breed and evolve the Lillipup line first."
    assert len(result.tasks) == 1
    assert result.tasks[0].task_type == "breed"
    assert result.tasks[0].species_name == "Lillipup"
