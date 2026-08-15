# AI Planner

The AI planner turns a Living Dex report JSON into prioritized next tasks.

The model is an assistant, not the source of truth.

## Rule

```text
Save reader + deterministic planner = source of truth
LLM = task summarizer and prioritizer
Executor = only acts on verified tasks
```

Do not let model output directly mutate saves, emulator state, Supabase tables, or game actions without validation.

## Generate report JSON

```powershell
uv run rld report-living-dex "D:\path\to\POKEMON W.sav" --game white --format json --output report.json
```

## Plan from report

Install AI extras:

```powershell
uv sync --extra ai
```

Make sure `.env` contains at least one provider key:

```env
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=
```

Run OpenAI planner:

```powershell
uv run rld plan-report report.json --provider openai
```

Run Anthropic planner:

```powershell
uv run rld plan-report report.json --provider anthropic
```

Run Google planner:

```powershell
uv run rld plan-report report.json --provider google
```

Optional model override:

```powershell
uv run rld plan-report report.json --provider openai --model gpt-4.1-mini
```

## Output shape

```json
{
  "provider": "openai",
  "summary": "Short summary",
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
```

## Cost note

`rld provider-health` is free because it only checks environment variables.

`rld plan-report` calls the selected provider and can spend API money. Use it intentionally.
