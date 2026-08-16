from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import httpx
from fastapi import FastAPI, HTTPException, Response, WebSocket
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field

from pokedex_completer_gen5 import __version__
from pokedex_completer_gen5.agents.validator_store import recent_validator_events, record_validator_event
from pokedex_completer_gen5.agents.voice import build_voice_config, create_realtime_session
from pokedex_completer_gen5.dex.pc_living_dex import build_pc_living_dex_report
from pokedex_completer_gen5.emulator.bizhawk_client import BizHawkBridgeError, BizHawkClient, bizhawk_config_from_env
from pokedex_completer_gen5.emulator.launcher import bizhawk_launch_config_from_env, launch_bizhawk
from pokedex_completer_gen5.integrations.env import load_environment
from pokedex_completer_gen5.integrations.provider_health import provider_health_payload
from pokedex_completer_gen5.saveio.physical_report import build_save_payload, build_save_report
from pokedex_completer_gen5.server.dashboard import DASHBOARD_HTML
from pokedex_completer_gen5.server.telemetry import (
    recent_telemetry_events,
    record_telemetry_event,
    telemetry_websocket,
)

load_environment()

app = FastAPI(title="PokedexCompleter Gen 5", version=__version__)


class EmulatorLaunchRequest(BaseModel):
    rom_path: Path | None = None
    install_save: bool = True
    restart_existing: bool = True


class EmulatorPressRequest(BaseModel):
    button: str
    frames: int = Field(default=1, ge=1, le=120)


class EmulatorPressSequenceRequest(BaseModel):
    buttons: list[str] = Field(min_length=1, max_length=50)
    frames: int = Field(default=1, ge=1, le=120)
    gap_frames: int = Field(default=1, ge=0, le=120)


class EmulatorFrameAdvanceRequest(BaseModel):
    frames: int = Field(default=1, ge=1, le=600)


class EmulatorCheckpointRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class UiEventRequest(BaseModel):
    event_type: str = Field(min_length=1, max_length=120)
    payload: dict[str, Any] = Field(default_factory=dict)


class ValidatorEventRequest(BaseModel):
    event_type: str
    message: str
    payload: dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"


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


def bridge_client() -> BizHawkClient:
    return BizHawkClient(bizhawk_config_from_env())


def bridge_response(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    record_telemetry_event(event_type, payload)
    return payload


def bridge_error(event_type: str, exc: BizHawkBridgeError) -> HTTPException:
    payload = {"error": str(exc), "hint": "Start BizHawk, load the ROM, and run lua/bizhawk_gen5_bridge.lua."}
    record_telemetry_event(event_type, payload)
    return HTTPException(status_code=503, detail=payload)


@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket) -> None:
    await telemetry_websocket(websocket)


@app.get("/api/telemetry")
def telemetry(limit: int = 50) -> dict[str, Any]:
    return {"events": recent_telemetry_events(limit=limit)}


@app.post("/api/ui/events")
def ui_event(request: UiEventRequest) -> dict[str, Any]:
    event = record_telemetry_event(f"ui.{request.event_type}", request.payload)
    return event.to_dict()


@app.post("/api/emulator/launch")
def emulator_launch(request: EmulatorLaunchRequest | None = None) -> dict[str, Any]:
    try:
        config = bizhawk_launch_config_from_env(rom_path=request.rom_path if request else None)
        payload = launch_bizhawk(
            config,
            install_save=request.install_save if request else True,
            restart_existing=request.restart_existing if request else True,
        )
        record_telemetry_event("emulator.launch", payload)
        return payload
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to launch BizHawk: {exc}") from exc


@app.get("/api/emulator/state")
def emulator_state() -> dict[str, Any]:
    try:
        return bridge_response("emulator.state", bridge_client().get_state())
    except BizHawkBridgeError as exc:
        raise bridge_error("emulator.state.error", exc) from exc


@app.post("/api/emulator/press")
def emulator_press(request: EmulatorPressRequest) -> dict[str, Any]:
    try:
        return bridge_response(
            "emulator.press",
            bridge_client().press(request.button, frames=request.frames),
        )
    except BizHawkBridgeError as exc:
        raise bridge_error("emulator.press.error", exc) from exc


@app.post("/api/emulator/press-sequence")
def emulator_press_sequence(request: EmulatorPressSequenceRequest) -> dict[str, Any]:
    try:
        return bridge_response(
            "emulator.press_sequence",
            bridge_client().press_sequence(request.buttons, frames=request.frames, gap_frames=request.gap_frames),
        )
    except BizHawkBridgeError as exc:
        raise bridge_error("emulator.press_sequence.error", exc) from exc


@app.post("/api/emulator/frame-advance")
def emulator_frame_advance(request: EmulatorFrameAdvanceRequest) -> dict[str, Any]:
    try:
        return bridge_response("emulator.frame_advance", bridge_client().frame_advance(frames=request.frames))
    except BizHawkBridgeError as exc:
        raise bridge_error("emulator.frame_advance.error", exc) from exc


@app.post("/api/emulator/pause")
def emulator_pause() -> dict[str, Any]:
    try:
        return bridge_response("emulator.pause", bridge_client().pause())
    except BizHawkBridgeError as exc:
        raise bridge_error("emulator.pause.error", exc) from exc


@app.post("/api/emulator/resume")
def emulator_resume() -> dict[str, Any]:
    try:
        return bridge_response("emulator.resume", bridge_client().resume())
    except BizHawkBridgeError as exc:
        raise bridge_error("emulator.resume.error", exc) from exc


@app.post("/api/emulator/checkpoint/save")
def emulator_save_checkpoint(request: EmulatorCheckpointRequest) -> dict[str, Any]:
    try:
        return bridge_response("emulator.save_checkpoint", bridge_client().save_checkpoint(request.name))
    except BizHawkBridgeError as exc:
        raise bridge_error("emulator.save_checkpoint.error", exc) from exc


@app.post("/api/emulator/checkpoint/load")
def emulator_load_checkpoint(request: EmulatorCheckpointRequest) -> dict[str, Any]:
    try:
        return bridge_response("emulator.load_checkpoint", bridge_client().load_checkpoint(request.name))
    except BizHawkBridgeError as exc:
        raise bridge_error("emulator.load_checkpoint.error", exc) from exc


@app.get("/api/emulator/screenshot")
def emulator_screenshot() -> dict[str, Any]:
    try:
        return bridge_response("emulator.screenshot", bridge_client().screenshot())
    except BizHawkBridgeError as exc:
        raise bridge_error("emulator.screenshot.error", exc) from exc


@app.get("/api/voice/config")
def voice_config(mode: str = "off") -> dict[str, Any]:
    try:
        return build_voice_config(mode).to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/voice/realtime-session")
def voice_realtime_session(mode: str = "talk-to-me") -> dict[str, Any]:
    try:
        return create_realtime_session(mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"OpenAI Realtime session failed: {exc}") from exc


@app.get("/api/validator/events")
def validator_events(limit: int = 50) -> dict[str, Any]:
    return {"events": recent_validator_events(limit=limit)}


@app.post("/api/validator/events")
def validator_event(request: ValidatorEventRequest) -> dict[str, Any]:
    try:
        event = record_validator_event(
            request.event_type,
            request.message,
            payload=request.payload,
            status=request.status,  # type: ignore[arg-type]
        )
        record_telemetry_event("validator.event", event.to_dict())
        return event.to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/pc-living-dex")
def pc_living_dex(request: PcLivingDexRequest) -> dict[str, object]:
    try:
        if str(request.save_path).strip() in ("", "."):
            raise HTTPException(status_code=400, detail="Save path is empty. Paste a full .sav path first.")
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
