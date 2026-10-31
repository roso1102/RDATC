"""ARES local FastAPI service. Run one worker to keep acquisition single-owner."""

import asyncio
from contextlib import asynccontextmanager
import json
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .backend import Hub, Settings
from .ir_simulator import IRScenario
from .radar_ble import discover_radars


class CameraConfig(BaseModel):
    url: str | None = Field(default=None, max_length=2048)


class IRConfig(BaseModel):
    scenario: IRScenario


class ProfileConfig(BaseModel):
    profile: Literal["clear", "reduced_visibility", "fire_no_smoke", "fire_smoke", "flood", "earthquake"]


class RadarConfig(BaseModel):
    enabled: bool = False
    address: str | None = Field(default=None, max_length=100)


class ScanConfig(BaseModel):
    timeout: float = Field(default=8.0, ge=2.0, le=15.0)


def create_app(settings=None, *, transport=None, scanner=discover_radars, detector=None):
    settings = settings or Settings.from_env()
    hub = Hub(settings, transport=transport, detector=detector)

    @asynccontextmanager
    async def lifespan(_):
        await hub.start()
        try:
            yield
        finally:
            await hub.close()

    application = FastAPI(title="ARES local ground station", version="0.1.0", lifespan=lifespan)
    application.state.hub = hub
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["GET", "POST"], allow_headers=["Content-Type"],
    )

    @application.get("/api/health")
    async def health():
        state = hub.snapshot()
        return {"service": "ARES", "status": "OK", "mode": state["mode"],
                "camera_status": state["camera"]["status"],
                "radar_status": state["radar"]["status"],
                "ir_source": "SYNTHETIC", "detector_status": state["detection"]["status"]}

    @application.get("/api/state")
    async def state():
        return hub.snapshot()

    @application.get("/api/camera/frame")
    async def frame():
        current = hub.snapshot()["camera"]
        if not current["available"]:
            raise HTTPException(503, f"Camera unavailable: {current['status']}")
        cached = hub.frame
        return Response(cached["bytes"], media_type="image/jpeg", headers={
            "Cache-Control": "no-store", "X-Frame-Id": cached["metadata"]["frame_id"],
            "X-Received-At": cached["metadata"]["received_at_utc"],
            "X-Age-Basis": "BACKEND_RECEIVE_TIME",
            "X-Receive-Age-Ms": str(current["receive_age_ms"]),
        })

    @application.post("/api/config/camera")
    async def configure_camera(config: CameraConfig):
        try:
            hub.configure_camera(config.url)
        except ValueError as error:
            raise HTTPException(400, str(error)) from error
        await asyncio.to_thread(hub.recorder.record, "camera_config", {"url": hub.settings.camera_url})
        return hub.snapshot()["camera"]

    @application.post("/api/config/ir")
    async def configure_ir(config: IRConfig):
        hub.ir_scenario = config.scenario
        await asyncio.to_thread(hub.recorder.record, "ir_scenario", {
            "source": "SYNTHETIC", "scenario_id": config.scenario.value,
        })
        return {"source": "SYNTHETIC", "scenario": config.scenario.value,
                "eligible_for_live_fusion": False}

    @application.post("/api/config/profile")
    async def configure_profile(config: ProfileConfig):
        hub.profile = config.profile
        hub.profile_command_id += 1
        result = hub.snapshot()["profile"]
        await asyncio.to_thread(hub.recorder.record, "profile_applied", result)
        return result

    @application.post("/api/radar/scan")
    async def scan_radar(config: ScanConfig):
        try:
            found = await asyncio.wait_for(scanner(config.timeout), timeout=config.timeout + 5.0)
        except Exception as error:
            raise HTTPException(503, f"Bluetooth scan failed ({type(error).__name__})") from error
        return {"devices": [info for _, info in found],
                "note": "Disconnect HLKRadarTool before a laptop connection; only one BLE client is supported."}

    @application.post("/api/config/radar")
    async def configure_radar(config: RadarConfig):
        if config.enabled and not config.address:
            raise HTTPException(400, "Select an explicit radar address before connecting")
        hub.configure_radar(config.enabled, config.address)
        await asyncio.to_thread(hub.recorder.record, "radar_config", config.model_dump())
        return hub.snapshot()["radar"]

    @application.post("/api/recording/start")
    async def start_recording():
        try:
            result = await asyncio.to_thread(hub.recorder.start, hub.snapshot())
        except RuntimeError as error:
            raise HTTPException(409, str(error)) from error
        except OSError as error:
            raise HTTPException(503, "Recording storage is unavailable") from error
        hub.record_accepting = True
        return result

    @application.post("/api/recording/stop")
    async def stop_recording():
        hub.record_accepting = False
        try:
            await asyncio.wait_for(hub.radar_record_queue.join(), timeout=2.0)
        except asyncio.TimeoutError:
            pass
        return await asyncio.to_thread(hub.recorder.stop)

    @application.get("/api/recordings")
    async def recordings():
        result = []
        if settings.recording_dir.exists():
            for manifest in sorted(settings.recording_dir.glob("*/manifest.json"), reverse=True):
                try:
                    record = json.loads(manifest.read_text(encoding="utf-8"))
                    result.append({key: record.get(key) for key in (
                        "session_id", "started_at_utc", "stopped_at_utc", "events", "frames",
                    )})
                except (ValueError, OSError):
                    continue
        return {"sessions": result}

    @application.get("/api/recordings/{session_id}/events")
    async def recorded_events(session_id: str):
        if len(session_id) != 32 or any(character not in "0123456789abcdef" for character in session_id):
            raise HTTPException(400, "Invalid session ID")
        path = settings.recording_dir / session_id / "events.jsonl"
        if not path.is_file():
            raise HTTPException(404, "Recorded session not found")
        return FileResponse(path, media_type="application/x-ndjson",
                            headers={"X-ARES-Mode": "REPLAY", "Cache-Control": "no-store"})

    web_dist = Path(__file__).resolve().parents[2] / "web" / "dist"
    if web_dist.is_dir():
        application.mount("/", StaticFiles(directory=web_dist, html=True), name="dashboard")
    else:
        @application.get("/")
        async def root():
            return {"service": "ARES", "api_docs": "/docs", "dashboard": "Frontend build pending"}

    return application


app = create_app()
