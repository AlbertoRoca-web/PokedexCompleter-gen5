from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import httpx
from fastapi import FastAPI, HTTPException, Response, WebSocket
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, ConfigDict, Field

from pokedex_completer_gen5 import __version__
from pokedex_completer_gen5.agents.validator_store import recent_validator_events, record_validator_event
from pokedex_completer_gen5.agents.voice import build_voice_config, create_realtime_session
from pokedex_completer_gen5.ai.router import router_payload
from pokedex_completer_gen5.dex.pc_living_dex import build_pc_living_dex_report
from pokedex_completer_gen5.emulator.artifacts import checkpoint_path, screenshot_path
from pokedex_completer_gen5.emulator.bizhawk_client import BizHawkBridgeError, BizHawkClient, bizhawk_config_from_env
from pokedex_completer_gen5.emulator.controls import controls_payload, normalize_button_or_action
from pokedex_completer_gen5.emulator.diagnostics import build_emulator_diagnostics, wait_for_bridge
from pokedex_completer_gen5.emulator.launcher import bizhawk_launch_config_from_env, launch_bizhawk
from pokedex_completer_gen5.emulator.macro_feedback import recent_macro_feedback, record_macro_feedback
from pokedex_completer_gen5.emulator.macro_visual_verifier import verify_macro_visual_change
from pokedex_completer_gen5.emulator.macros import run_close_menu_macro, run_open_menu_macro
from pokedex_completer_gen5.emulator.native_bridge import NativeBridgeError, native_bridge, wait_for_native_bridge
from pokedex_completer_gen5.emulator.readiness import ensure_emulator_ready
from pokedex_completer_gen5.emulator.rom import identify_rom
from pokedex_completer_gen5.emulator.screen_classifier import classify_screenshot
from pokedex_completer_gen5.emulator.semantic_state import build_semantic_state
from pokedex_completer_gen5.emulator.title_flow import run_resume_saved_game_from_title
from pokedex_completer_gen5.emulator.vision import analyze_screenshot
from pokedex_completer_gen5.emulator.visual_wait import capture_informative_screenshot
from pokedex_completer_gen5.integrations.env import load_environment
from pokedex_completer_gen5.integrations.provider_health import provider_health_payload
from pokedex_completer_gen5.persistence.store import (
    get_artifact,
    latest_artifact_path,
    list_artifacts,
    macro_reliability,
    persist_artifact,
    persist_macro_attempt,
)
from pokedex_completer_gen5.saveio.physical_report import build_save_payload, build_save_report
from pokedex_completer_gen5.server.dashboard import DASHBOARD_HTML
from pokedex_completer_gen5.server.telemetry import (
    recent_telemetry_events,
    record_telemetry_event,
    telemetry_websocket,
)
from pokedex_completer_gen5.settings import get_settings
from pokedex_completer_gen5.trajectory import read_jsonl_events

load_environment()

app = FastAPI(title="PokedexCompleter Gen 5", version=__version__)


class EmulatorLaunchRequest(BaseModel):
    rom_path: Path | None = None
    install_save: bool = True
    restart_existing: bool = True
    wait_for_bridge: bool = True


class EmulatorEnsureReadyRequest(BaseModel):
    relaunch_if_needed: bool = True


class EmulatorPressRequest(BaseModel):
    button: str
    frames: int = Field(default=1, ge=1, le=120)


class EmulatorPressSequenceRequest(BaseModel):
    buttons: list[str] = Field(min_length=1, max_length=50)
    frames: int = Field(default=1, ge=1, le=120)
    gap_frames: int = Field(default=1, ge=0, le=120)


class EmulatorFrameAdvanceRequest(BaseModel):
    frames: int = Field(default=1, ge=1, le=600)


class EmulatorMemoryReadRequest(BaseModel):
    domain: str = Field(default="", max_length=120)
    address: int = Field(ge=0, le=0xFFFFFFFF)


class EmulatorMemoryReadBytesRequest(EmulatorMemoryReadRequest):
    length: int = Field(default=16, ge=1, le=4096)


class EmulatorMacroRequest(BaseModel):
    wait_frames: int = Field(default=get_settings().timing.macro_wait_frames, ge=1, le=180)
    visual_max_attempts: int = Field(default=get_settings().timing.macro_visual_max_attempts, ge=1, le=10)
    visual_advance_frames: int = Field(default=get_settings().timing.macro_visual_advance_frames, ge=1, le=300)


class InformativeScreenshotRequest(BaseModel):
    label: str = Field(default="manual", min_length=1, max_length=80)
    max_attempts: int = Field(default=5, ge=1, le=20)
    advance_frames: int = Field(default=30, ge=1, le=600)


class TitleResumeRequest(BaseModel):
    initial_wait_frames: int = Field(default=get_settings().timing.title_initial_wait_frames, ge=0, le=1200)
    wait_after_start_frames: int = Field(default=get_settings().timing.title_wait_after_start_frames, ge=1, le=1200)
    wait_after_continue_frames: int = Field(
        default=get_settings().timing.title_wait_after_continue_frames,
        ge=1,
        le=2400,
    )
    visual_max_attempts: int = Field(default=get_settings().timing.title_visual_max_attempts, ge=1, le=20)
    visual_advance_frames: int = Field(default=get_settings().timing.title_visual_advance_frames, ge=1, le=600)
    press_frames: int = Field(default=get_settings().timing.title_press_frames, ge=1, le=30)
    change_max_attempts: int = Field(default=get_settings().timing.title_change_max_attempts, ge=1, le=30)
    change_advance_frames: int = Field(default=get_settings().timing.title_change_advance_frames, ge=1, le=1200)


class EmulatorMacroFeedbackRequest(BaseModel):
    macro_run_id: str = Field(min_length=1)
    outcome: str
    notes: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)


class EmulatorCheckpointRequest(BaseModel):
    name: str = Field(min_length=1, max_length=260)


class EmulatorCheckpointArtifactRequest(BaseModel):
    artifact_id: str = Field(min_length=1)


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


@app.get("/api/ai/model-router")
def ai_model_router() -> dict[str, str | None]:
    return router_payload()


def bridge_client() -> BizHawkClient:
    return BizHawkClient(bizhawk_config_from_env())


def bridge_request(method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    bridge = native_bridge()
    if bridge.status()["connected"]:
        try:
            return bridge.request(method, params)
        except NativeBridgeError:
            pass
    client = bridge_client()
    if hasattr(client, "request"):
        return client.request(method, params)
    if method == "get_state":
        return client.get_state()
    if method == "press":
        if params is None:
            raise BizHawkBridgeError("press requires params")
        return client.press(str(params["button"]), frames=int(params.get("frames", 1)))
    if method == "press_sequence":
        buttons = params.get("buttons_csv", "").split(",") if params else []
        return client.press_sequence(
            buttons,
            frames=params.get("frames", 1) if params else 1,
            gap_frames=params.get("gap_frames", 1) if params else 1,
        )
    raise BizHawkBridgeError(f"Unsupported bridge method for compatibility fallback: {method}")


def bridge_response(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    record_telemetry_event(event_type, payload)
    return payload


def bridge_error(event_type: str, exc: BizHawkBridgeError) -> HTTPException:
    payload = {
        "error": str(exc),
        "hint": "Launch from the website, then click Diagnose Bridge. Native comm bridge should use port 8766.",
        "native_bridge": native_bridge().status(),
    }
    record_telemetry_event(event_type, payload)
    return HTTPException(status_code=503, detail=payload)


@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket) -> None:
    await telemetry_websocket(websocket)


@app.get("/api/telemetry")
def telemetry(limit: int = 50) -> dict[str, Any]:
    return {"events": recent_telemetry_events(limit=limit)}


@app.get("/api/trajectory")
def trajectory(limit: int = 100) -> dict[str, Any]:
    return {"events": read_jsonl_events(limit=limit)}


@app.post("/api/ui/events")
def ui_event(request: UiEventRequest) -> dict[str, Any]:
    event = record_telemetry_event(f"ui.{request.event_type}", request.payload)
    return event.to_dict()


def add_native_diagnosis(payload: dict[str, Any]) -> dict[str, Any]:
    bridge = native_bridge()
    native_status = bridge.status()
    payload["native_bridge"] = native_status
    if native_status["connected"]:
        payload["diagnosis"] = {
            "status": "ready-native",
            "message": "BizHawk is connected through the native comm bridge on port 8766.",
            "next_step": "Click Get State, then try A/B/D-pad buttons.",
        }
    return payload


@app.get("/api/emulator/controls")
def emulator_controls() -> dict[str, Any]:
    return controls_payload()


@app.get("/api/emulator/rom")
def emulator_rom_identity() -> dict[str, Any]:
    return identify_rom(bizhawk_launch_config_from_env().rom_path)


@app.get("/api/emulator/diagnostics")
def emulator_diagnostics() -> dict[str, Any]:
    launch_config = bizhawk_launch_config_from_env()
    bridge_config = bizhawk_config_from_env()
    payload = add_native_diagnosis(build_emulator_diagnostics(launch_config, bridge_config))
    record_telemetry_event("emulator.diagnostics", payload)
    return payload


@app.post("/api/emulator/ensure-ready")
def emulator_ensure_ready(request: EmulatorEnsureReadyRequest | None = None) -> dict[str, Any]:
    payload = ensure_emulator_ready(relaunch_if_needed=request.relaunch_if_needed if request else True).to_dict()
    record_telemetry_event("emulator.ensure_ready", payload)
    return payload


@app.post("/api/emulator/launch")
def emulator_launch(request: EmulatorLaunchRequest | None = None) -> dict[str, Any]:
    try:
        native_bridge().start()
        config = bizhawk_launch_config_from_env(rom_path=request.rom_path if request else None)
        payload = launch_bizhawk(
            config,
            install_save=request.install_save if request else True,
            restart_existing=request.restart_existing if request else True,
        )
        if request is None or request.wait_for_bridge:
            payload["native_bridge_after_launch"] = wait_for_native_bridge()
            payload["legacy_bridge_after_launch"] = wait_for_bridge(bizhawk_config_from_env(), timeout_seconds=1)
            payload["diagnostics"] = add_native_diagnosis(build_emulator_diagnostics(config, bizhawk_config_from_env()))
        record_telemetry_event("emulator.launch", payload)
        return payload
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to launch BizHawk: {exc}") from exc


@app.get("/api/emulator/info")
def emulator_info() -> dict[str, Any]:
    try:
        return bridge_response("emulator.info", bridge_request("bridge.info"))
    except BizHawkBridgeError as exc:
        raise bridge_error("emulator.info.error", exc) from exc


@app.get("/api/emulator/state")
def emulator_state() -> dict[str, Any]:
    try:
        return bridge_response("emulator.state", bridge_request("get_state"))
    except BizHawkBridgeError as exc:
        raise bridge_error("emulator.state.error", exc) from exc


@app.get("/api/emulator/semantic-state")
def emulator_semantic_state(profile_id: str = "white_us_eu") -> dict[str, Any]:
    try:
        payload = build_semantic_state(bridge_request, profile_id=profile_id).to_dict()
        record_telemetry_event("emulator.semantic_state", payload)
        return payload
    except BizHawkBridgeError as exc:
        raise bridge_error("emulator.semantic_state.error", exc) from exc


@app.post("/api/emulator/press")
def emulator_press(request: EmulatorPressRequest) -> dict[str, Any]:
    try:
        return bridge_response(
            "emulator.press",
            bridge_request("press", {"button": normalize_button_or_action(request.button), "frames": request.frames}),
        )
    except BizHawkBridgeError as exc:
        raise bridge_error("emulator.press.error", exc) from exc


@app.post("/api/emulator/press-sequence")
def emulator_press_sequence(request: EmulatorPressSequenceRequest) -> dict[str, Any]:
    try:
        return bridge_response(
            "emulator.press_sequence",
            bridge_request(
                "press_sequence",
                {
                    "buttons_csv": ",".join(normalize_button_or_action(button) for button in request.buttons),
                    "frames": request.frames,
                    "gap_frames": request.gap_frames,
                },
            ),
        )
    except BizHawkBridgeError as exc:
        raise bridge_error("emulator.press_sequence.error", exc) from exc


@app.post("/api/emulator/frame-advance")
def emulator_frame_advance(request: EmulatorFrameAdvanceRequest) -> dict[str, Any]:
    try:
        return bridge_response("emulator.frame_advance", bridge_request("frame_advance", {"frames": request.frames}))
    except BizHawkBridgeError as exc:
        raise bridge_error("emulator.frame_advance.error", exc) from exc


def _run_macro_with_visual_verification(
    macro_name: str,
    macro_runner: Any,
    request: EmulatorMacroRequest | None,
) -> dict[str, Any]:
    visual_before = capture_informative_screenshot(
        bridge_request,
        label=f"before-{macro_name}",
        max_attempts=request.visual_max_attempts if request else 3,
        advance_frames=request.visual_advance_frames if request else 30,
    )
    macro = macro_runner(bridge_request, wait_frames=request.wait_frames if request else 20)
    visual_after = capture_informative_screenshot(
        bridge_request,
        label=f"after-{macro_name}",
        max_attempts=request.visual_max_attempts if request else 3,
        advance_frames=request.visual_advance_frames if request else 30,
    )
    payload = macro.to_dict()
    verification = verify_macro_visual_change(macro_name, visual_before, visual_after)
    payload["verification"] = verification.to_dict()
    persist_macro_attempt(payload)
    status = "accepted" if verification.status == "verified-success" else "needs-human"
    validator_event = record_validator_event(
        "macro_visual_verification",
        f"{macro_name} visual check: {payload['verification']['status']}",
        payload={"macro_run_id": payload["id"], "macro_name": macro_name, "verification": payload["verification"]},
        status=status,  # type: ignore[arg-type]
    )
    payload["validator_event"] = validator_event.to_dict()
    return payload


@app.post("/api/emulator/macro/open-menu")
def emulator_macro_open_menu(request: EmulatorMacroRequest | None = None) -> dict[str, Any]:
    try:
        payload = _run_macro_with_visual_verification("open_menu", run_open_menu_macro, request)
        record_telemetry_event("emulator.macro.open_menu", payload)
        return payload
    except BizHawkBridgeError as exc:
        raise bridge_error("emulator.macro.open_menu.error", exc) from exc


@app.post("/api/emulator/macro/close-menu")
def emulator_macro_close_menu(request: EmulatorMacroRequest | None = None) -> dict[str, Any]:
    try:
        payload = _run_macro_with_visual_verification("close_menu", run_close_menu_macro, request)
        record_telemetry_event("emulator.macro.close_menu", payload)
        return payload
    except BizHawkBridgeError as exc:
        raise bridge_error("emulator.macro.close_menu.error", exc) from exc


@app.post("/api/emulator/macro/resume-save-from-title")
def emulator_macro_resume_save_from_title(request: TitleResumeRequest | None = None) -> dict[str, Any]:
    try:
        result = run_resume_saved_game_from_title(
            bridge_request,
            initial_wait_frames=request.initial_wait_frames if request else 60,
            wait_after_start_frames=request.wait_after_start_frames if request else 90,
            wait_after_continue_frames=request.wait_after_continue_frames if request else 600,
            visual_max_attempts=request.visual_max_attempts if request else 5,
            visual_advance_frames=request.visual_advance_frames if request else 30,
            press_frames=request.press_frames if request else 4,
            change_max_attempts=request.change_max_attempts if request else 8,
            change_advance_frames=request.change_advance_frames if request else 90,
        )
        payload = result.to_dict()
        status = "accepted" if payload["verification"]["status"] == "candidate-overworld" else "needs-human"
        validator_event = record_validator_event(
            "macro_visual_verification",
            f"resume_saved_game_from_title visual check: {payload['verification']['status']}",
            payload={
                "macro_run_id": payload["id"],
                "macro_name": payload["macro_name"],
                "verification": payload["verification"],
            },
            status=status,  # type: ignore[arg-type]
        )
        payload["validator_event"] = validator_event.to_dict()
        record_telemetry_event("emulator.macro.resume_save_from_title", payload)
        return payload
    except BizHawkBridgeError as exc:
        raise bridge_error("emulator.macro.resume_save_from_title.error", exc) from exc


@app.get("/api/emulator/macro/feedback")
def emulator_macro_feedback_recent(limit: int = 50) -> dict[str, Any]:
    return {"feedback": recent_macro_feedback(limit=limit), "reliability": macro_reliability(limit=limit)}


@app.post("/api/emulator/macro/feedback")
def emulator_macro_feedback(request: EmulatorMacroFeedbackRequest) -> dict[str, Any]:
    if request.outcome not in ("success", "failure", "uncertain"):
        raise HTTPException(status_code=400, detail="Outcome must be success, failure, or uncertain")
    feedback = record_macro_feedback(
        request.macro_run_id,
        request.outcome,  # type: ignore[arg-type]
        notes=request.notes,
        payload=request.payload,
    )
    payload = feedback.to_dict()
    record_telemetry_event("emulator.macro.feedback", payload)
    return payload


@app.post("/api/emulator/pause")
def emulator_pause() -> dict[str, Any]:
    try:
        return bridge_response("emulator.pause", bridge_request("pause"))
    except BizHawkBridgeError as exc:
        raise bridge_error("emulator.pause.error", exc) from exc


@app.post("/api/emulator/resume")
def emulator_resume() -> dict[str, Any]:
    try:
        return bridge_response("emulator.resume", bridge_request("resume"))
    except BizHawkBridgeError as exc:
        raise bridge_error("emulator.resume.error", exc) from exc


@app.post("/api/emulator/checkpoint/save")
def emulator_save_checkpoint(request: EmulatorCheckpointRequest) -> dict[str, Any]:
    try:
        path = checkpoint_path(request.name)
        payload = bridge_request("save_checkpoint", {"name": request.name, "path": path.as_posix()})
        payload["artifact_path"] = str(path)
        payload["artifact"] = persist_artifact("checkpoint", path, payload)
        return bridge_response("emulator.save_checkpoint", payload)
    except BizHawkBridgeError as exc:
        raise bridge_error("emulator.save_checkpoint.error", exc) from exc


@app.post("/api/emulator/checkpoint/load")
def emulator_load_checkpoint(request: EmulatorCheckpointRequest) -> dict[str, Any]:
    try:
        path = Path(request.name)
        payload = bridge_request("load_checkpoint", {"name": request.name, "path": path.as_posix()})
        payload["artifact_path"] = str(path)
        return bridge_response("emulator.load_checkpoint", payload)
    except BizHawkBridgeError as exc:
        raise bridge_error("emulator.load_checkpoint.error", exc) from exc


@app.post("/api/emulator/checkpoint/load-artifact")
def emulator_load_checkpoint_artifact(request: EmulatorCheckpointArtifactRequest) -> dict[str, Any]:
    artifact = get_artifact(request.artifact_id)
    if artifact is None or artifact["artifact_type"] != "checkpoint":
        raise HTTPException(status_code=404, detail="Checkpoint artifact not found")
    try:
        path = Path(str(artifact["path"]))
        payload = bridge_request("load_checkpoint", {"name": request.artifact_id, "path": path.as_posix()})
        payload["artifact"] = artifact
        return bridge_response("emulator.load_checkpoint", payload)
    except BizHawkBridgeError as exc:
        raise bridge_error("emulator.load_checkpoint.error", exc) from exc


@app.get("/api/emulator/artifacts")
def emulator_artifacts(artifact_type: str | None = None, limit: int = 50) -> dict[str, Any]:
    return {"artifacts": list_artifacts(artifact_type=artifact_type, limit=limit)}


@app.get("/api/emulator/screenshot")
def emulator_screenshot() -> dict[str, Any]:
    try:
        path = screenshot_path()
        payload = bridge_request("screenshot", {"path": path.as_posix()})
        payload["artifact_path"] = str(path)
        payload["artifact"] = persist_artifact("screenshot", path, payload)
        return bridge_response("emulator.screenshot", payload)
    except BizHawkBridgeError as exc:
        raise bridge_error("emulator.screenshot.error", exc) from exc


@app.get("/api/emulator/screenshot/latest.png")
def emulator_latest_screenshot_image() -> FileResponse:
    path = latest_artifact_path("screenshot")
    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail="No screenshot artifact exists yet")
    return FileResponse(path, media_type="image/png", filename=path.name)


@app.get("/api/emulator/screenshot/latest-analysis")
def emulator_latest_screenshot_analysis() -> dict[str, Any]:
    path = latest_artifact_path("screenshot")
    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail="No screenshot artifact exists yet")
    try:
        analysis = analyze_screenshot(path)
        analysis["classification"] = classify_screenshot(path).to_dict()
        return analysis
    except RuntimeError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc


@app.post("/api/emulator/screenshot/wait-informative")
def emulator_wait_informative_screenshot(request: InformativeScreenshotRequest | None = None) -> dict[str, Any]:
    try:
        result = capture_informative_screenshot(
            bridge_request,
            label=request.label if request else "manual",
            max_attempts=request.max_attempts if request else 5,
            advance_frames=request.advance_frames if request else 30,
        )
        payload = result.to_dict()
        validator_event = record_validator_event(
            "screenshot_visual_verification",
            f"Informative screenshot wait: {payload['reason']}",
            payload=payload,
            status="accepted" if result.ok else "needs-human",
        )
        payload["validator_event"] = validator_event.to_dict()
        record_telemetry_event("emulator.screenshot.wait_informative", payload)
        return payload
    except BizHawkBridgeError as exc:
        raise bridge_error("emulator.screenshot.wait_informative.error", exc) from exc


@app.post("/api/emulator/memory/read-u8")
def emulator_memory_read_u8(request: EmulatorMemoryReadRequest) -> dict[str, Any]:
    try:
        payload = bridge_request("memory.read_u8", {"domain": request.domain, "address": request.address})
        return bridge_response("emulator.memory.read_u8", payload)
    except BizHawkBridgeError as exc:
        raise bridge_error("emulator.memory.read_u8.error", exc) from exc


@app.post("/api/emulator/memory/read-bytes")
def emulator_memory_read_bytes(request: EmulatorMemoryReadBytesRequest) -> dict[str, Any]:
    try:
        payload = bridge_request(
            "memory.read_bytes",
            {"domain": request.domain, "address": request.address, "length": request.length},
        )
        values_csv = str(payload.get("values_csv", ""))
        payload["values"] = [int(item) for item in values_csv.split(",") if item]
        return bridge_response("emulator.memory.read_bytes", payload)
    except BizHawkBridgeError as exc:
        raise bridge_error("emulator.memory.read_bytes.error", exc) from exc


@app.get("/api/emulator/memory/domains")
def emulator_memory_domains() -> dict[str, Any]:
    try:
        payload = bridge_request("memory.list_domains")
        domains_csv = str(payload.get("domains_csv", ""))
        payload["domains"] = [item for item in domains_csv.split(",") if item]
        return bridge_response("emulator.memory.domains", payload)
    except BizHawkBridgeError as exc:
        raise bridge_error("emulator.memory.domains.error", exc) from exc


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
