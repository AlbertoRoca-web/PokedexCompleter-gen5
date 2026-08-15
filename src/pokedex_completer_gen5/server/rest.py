from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field

from pokedex_completer_gen5 import __version__
from pokedex_completer_gen5.agents.voice import build_voice_config
from pokedex_completer_gen5.dex.pc_living_dex import build_pc_living_dex_report
from pokedex_completer_gen5.emulator.bizhawk_client import BizHawkBridgeError, BizHawkClient, bizhawk_config_from_env
from pokedex_completer_gen5.integrations.env import load_environment
from pokedex_completer_gen5.integrations.provider_health import provider_health_payload
from pokedex_completer_gen5.saveio.physical_report import build_save_payload, build_save_report
from pokedex_completer_gen5.server.dashboard import DASHBOARD_HTML

load_environment()

app = FastAPI(title="PokedexCompleter Gen 5", version=__version__)


class EmulatorPressRequest(BaseModel):
    button: str
    frames: int = Field(default=1, ge=1, le=120)


class PcLivingDexRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    save_path: Path = Field(description="Local path to Gen 5 save file. Local dev API only.")
    game: str = Field(default="white", description="black, white, black2, or white2")
    requested_copy: str = Field(default="auto", alias="copy", description="auto, 0, or 1")
    scope: str = Field(default="regional", description="regional now; national later")
    include_party: bool = True
    target_policy: str = Field(default="game-regional", description="game-regional, all-regional, or catchable-only")


class SaveReportRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    save_path: Path = Field(description="Local path to a Gen 5 save file. Local dev API only.")
    game: str = Field(default="white", description="black, white, black2, or white2")
    requested_copy: str = Field(default="auto", alias="copy", description="auto, 0, or 1")
    format: Literal["json", "markdown"] = "json"


@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    return DASHBOARD_HTML


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/health/providers")
def provider_health() -> dict[str, object]:
    return provider_health_payload()


@app.get("/api/emulator/state")
def emulator_state() -> dict[str, Any]:
    try:
        return BizHawkClient(bizhawk_config_from_env()).get_state()
    except BizHawkBridgeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/emulator/press")
def emulator_press(request: EmulatorPressRequest) -> dict[str, Any]:
    try:
        return BizHawkClient(bizhawk_config_from_env()).press(request.button, frames=request.frames)
    except BizHawkBridgeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/voice/config")
def voice_config(mode: str = "off") -> dict[str, Any]:
    try:
        return build_voice_config(mode).to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/pc-living-dex")
def pc_living_dex(request: PcLivingDexRequest) -> dict[str, object]:
    try:
        payload = build_save_payload(request.save_path, request.game, request.requested_copy)
        return build_pc_living_dex_report(
            payload,
            request.game,
            scope=request.scope,
            include_party=request.include_party,
            target_policy=request.target_policy,
        ).to_dict()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Save file not found: {request.save_path}") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=f"Cannot read save file: {request.save_path}") from exc
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=400, detail=f"Could not read save file: {exc}") from exc


@app.post("/inspect-save")
def inspect_save(request: SaveReportRequest) -> dict[str, object]:
    return build_save_payload(request.save_path, request.game, request.requested_copy)


@app.post("/report-living-dex")
def report_living_dex(request: SaveReportRequest) -> dict[str, object] | str:
    if request.format == "markdown":
        return build_save_report(request.save_path, request.game, request.requested_copy)
    return build_save_payload(request.save_path, request.game, request.requested_copy)
