from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field

from pokedex_completer_gen5 import __version__
from pokedex_completer_gen5.integrations.env import load_environment
from pokedex_completer_gen5.integrations.provider_health import provider_health_payload
from pokedex_completer_gen5.saveio.physical_report import build_save_payload, build_save_report

load_environment()

app = FastAPI(title="PokedexCompleter Gen 5", version=__version__)


class SaveReportRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    save_path: Path = Field(description="Local path to a Gen 5 save file. Local dev API only.")
    game: str = Field(default="white", description="black, white, black2, or white2")
    requested_copy: str = Field(default="auto", alias="copy", description="auto, 0, or 1")
    format: Literal["json", "markdown"] = "json"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/health/providers")
def provider_health() -> dict[str, object]:
    return provider_health_payload()


@app.post("/inspect-save")
def inspect_save(request: SaveReportRequest) -> dict[str, object]:
    return build_save_payload(request.save_path, request.game, request.requested_copy)


@app.post("/report-living-dex")
def report_living_dex(request: SaveReportRequest) -> dict[str, object] | str:
    if request.format == "markdown":
        return build_save_report(request.save_path, request.game, request.requested_copy)
    return build_save_payload(request.save_path, request.game, request.requested_copy)
