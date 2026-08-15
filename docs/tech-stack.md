# Tech Stack

## Local core

- **Python 3.12+** for package, CLI, API server, planner, and save decoding.
- **Lua** for BizHawk bridge scripts.
- **BizHawk + melonDS core** for Nintendo DS emulation with memory/input APIs.
- **Pydantic** for schemas.
- **FastAPI** for REST and WebSocket telemetry.
- **MCP** for agent-facing tool protocol.
- **SQLite** for local run/task/checkpoint history.
- **JSONL logs** for trajectories, debugging, and supervised learning.

## Python libraries

Planned core dependencies:

```text
fastapi
uvicorn[standard]
pydantic
httpx
websockets
mcp
pillow
opencv-python
numpy
platformdirs
rich
typer
sqlmodel or sqlalchemy
```

Potential later dependencies:

```text
gymnasium
stable-baselines3
supabase
openai
anthropic
google-genai
pytesseract or easyocr
python-dotenv
```

## Emulator layer

Preferred path:

- BizHawk with melonDS Nintendo DS core;
- Lua bridge exposing structured memory reads, screenshots, controller input, touchscreen, frame advance, and save states;
- study/fork `it-was-katsumata/BizHawk-nds-mcp` if useful.

## AI layer

Primary architecture:

- LLM planner via MCP or function tools;
- deterministic executors for repetitive actions;
- vision/computer-use tools only as fallback/debug/demo mode.

Possible model providers:

- OpenAI Responses API;
- Anthropic tool use;
- Gemini Computer Use;
- local models later for classifiers or planning experiments.

## Backend options

### Supabase

Use for:

- accounts;
- save snapshot metadata;
- dex reports;
- tasks;
- emulator session logs;
- labeled screenshots;
- supervised learning feedback.

Do not require raw save uploads by default.

### Hugging Face Spaces

Use for:

- demo UI;
- model hosting;
- dataset preview;
- classifier experiments.

Do not use it as the main database. Wrong tool, cute logo.

## Pokémon metadata

- PokéAPI for upstream metadata and encounter data.
- Local cached Gen V acquisition graph for deterministic planning.
- PKHeX.Core as an external auditor/verifier, not as the mechanism for creating Pokémon.

## Optional RL

Wrap the emulator API in a Gymnasium environment later.

Use RL for narrow tasks:

- navigation;
- menu movement;
- battle policy;
- encounter farming;
- anti-stuck recovery.

Do not block the MVP on RL. That would be YAGNI wearing a lab coat.
