"""Single-owner acquisition and honest source/availability state."""

import asyncio
from dataclasses import dataclass
from io import BytesIO
import os
from pathlib import Path
import time
from urllib.parse import urlsplit, urlunsplit

import httpx
from PIL import Image

from .fusion import FusionEngine, camera_evidence, radar_evidence
from .ir_simulator import IRScenario, IRSimulator
from .radar_ble import find_radar, receive_reports
from .recording import Recorder, utc_now

# Prior weights per operator-selected condition. Disaster priors and their reasoning/citations are
# in docs/RESULTS_GUIDE.md section 4; none is calibrated on ARES data.
PROFILES = {
    "clear": {"camera": 0.7, "radar": 0.3, "ir": 0.0},
    "reduced_visibility": {"camera": 0.2, "radar": 0.8, "ir": 0.0},
    "fire_no_smoke": {"camera": 0.5, "radar": 0.4, "ir": 0.1},
    "fire_smoke": {"camera": 0.1, "radar": 0.8, "ir": 0.1},
    "flood": {"camera": 0.6, "radar": 0.2, "ir": 0.2},
    "earthquake": {"camera": 0.15, "radar": 0.8, "ir": 0.05},
}
PROFILE_INFO = {
    "clear": ("Clear", "PROVISIONAL_NOT_CALIBRATED"),
    "reduced_visibility": ("Low visibility", "PROVISIONAL_NOT_CALIBRATED"),
    "fire_no_smoke": ("Fire, no smoke", "LITERATURE_PRIOR_UNCALIBRATED"),
    "fire_smoke": ("Fire with smoke", "LITERATURE_PRIOR_UNCALIBRATED"),
    "flood": ("Flood", "LITERATURE_PRIOR_UNCALIBRATED"),
    "earthquake": ("Earthquake / rubble", "LITERATURE_PRIOR_UNCALIBRATED"),
}
IR_IS_SYNTHETIC = True


def applied_weights(prior):
    """Weights fusion actually uses: synthetic IR is held at 0 and camera/radar renormalised."""
    weights = dict(prior)
    if IR_IS_SYNTHETIC:
        weights["ir"] = 0.0
    total = sum(weights.values())
    return {name: round(weight / total, 4) for name, weight in weights.items()}
MAX_IMAGE_BYTES = 2 * 1024 * 1024
DEFAULT_DETECTOR_MODEL = Path(__file__).resolve().parents[1] / "models" / "yolox_nano.onnx"


EDGE_PERSON_THRESHOLD = 0.5  # Provisional; the on-node score is uncalibrated on OV7670 frames.


def header_int(headers, name):
    try:
        return int(headers.get(name, ""))
    except ValueError:
        return None


def node_person(headers):
    """On-node (ESP32) person classifier result carried on the same /capture response."""
    status = headers.get("x-ares-person-status")
    if status is None:
        return None  # Firmware without on-node inference.
    try:
        score = float(headers.get("x-ares-person-score", ""))
    except ValueError:
        score = None
    ok = status == "ok" and score is not None and 0.0 <= score <= 1.0
    return {"status": "ok" if ok else "unavailable", "score": score if ok else None,
            "infer_ms": header_int(headers, "x-ares-person-infer-ms") if ok else None,
            "prep_ms": header_int(headers, "x-ares-person-prep-ms") if ok else None,
            "model": headers.get("x-ares-person-model") if ok else None}


def camera_url(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    parts = urlsplit(value.strip())
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ValueError("Camera URL must be an http(s) endpoint")
    if parts.username or parts.password or parts.fragment:
        raise ValueError("Camera URL cannot contain credentials or a fragment")
    _ = parts.port  # Validate port syntax/range before the worker uses it.
    return urlunsplit((parts.scheme, parts.netloc, parts.path or "/capture", parts.query, ""))


@dataclass
class Settings:
    camera_url: str | None = None
    camera_interval_s: float = 0.5  # Wait after each fetch; 0.75 s measured 0.95 fps (pipeline-2026-10-31).
    camera_stale_s: float = 3.0
    radar_stale_s: float = 3.0
    ir_interval_s: float = 1.0
    radar_address: str | None = None
    radar_enabled: bool = False
    radar_password: str = "HiLink"
    recording_dir: Path = Path(__file__).resolve().parents[2] / "benchmarks" / "sessions"
    detector_model: Path | None = None
    detector_score_threshold: float = 0.35
    detector_profile: str = "laptop"
    fusion_interval_s: float = 0.5

    def __post_init__(self):
        self.camera_url = camera_url(self.camera_url)
        if min(self.camera_interval_s, self.camera_stale_s, self.radar_stale_s, self.ir_interval_s,
               self.fusion_interval_s) <= 0:
            raise ValueError("Acquisition intervals and stale limits must be positive")
        if not 0 < self.detector_score_threshold < 1:
            raise ValueError("Detector score threshold must be between 0 and 1")

    @classmethod
    def from_env(cls):
        model = os.getenv("ARES_DETECTOR_MODEL")
        if model is None and DEFAULT_DETECTOR_MODEL.is_file():
            model = str(DEFAULT_DETECTOR_MODEL)
        return cls(
            camera_url=os.getenv("ARES_CAMERA_URL"),
            camera_interval_s=float(os.getenv("ARES_CAMERA_INTERVAL", str(cls.camera_interval_s))),
            radar_address=os.getenv("ARES_RADAR_ADDRESS"),
            radar_enabled=os.getenv("ARES_RADAR_ENABLED", "0") == "1",
            radar_password=os.getenv("ARES_RADAR_PASSWORD", "HiLink"),
            recording_dir=Path(os.getenv("ARES_RECORDING_DIR", str(cls.recording_dir))),
            detector_model=Path(model) if model and os.getenv("ARES_DETECTOR", "1") != "0" else None,
            detector_score_threshold=float(os.getenv("ARES_DETECTOR_THRESHOLD", "0.35")),
            detector_profile=os.getenv("ARES_DETECTOR_PROFILE", "laptop"),
        )


class Hub:
    def __init__(self, settings: Settings, transport=None, detector=None):
        self.settings = settings
        self.transport = transport
        self.detector = detector
        self.detector_error = None
        self.detection = None
        self.frame_ready = asyncio.Event()
        self.fusion_engine = FusionEngine()
        self.fusion = None
        self.started = time.monotonic()
        self.ir = IRSimulator(seed=42)
        self.ir_scenario = IRScenario.BASELINE
        self.ir_reading = None
        self.profile = "clear"
        self.profile_command_id = 0
        self.camera_state = "NOT_CONFIGURED" if not settings.camera_url else "CONNECTING"
        self.camera_error = None
        self.camera_generation = 0
        self.camera_sequence = 0
        self.frame = None
        self.radar_state = "NOT_CONFIGURED"
        self.radar_error = None
        self.radar_reading = None
        self.radar_received = None
        self.radar_generation = 0
        self.radar_stop = None
        self.radar_record_queue = asyncio.Queue(maxsize=128)
        self.dropped_record_reports = 0
        self.recorder = Recorder(settings.recording_dir)
        self.record_accepting = False
        self.tasks = []

    async def start(self):
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(3.0), transport=self.transport, trust_env=False,
            follow_redirects=False,
        )
        self.tasks = [asyncio.create_task(worker()) for worker in (
            self.camera_worker, self.ir_worker, self.radar_worker, self.radar_recorder,
            self.detector_worker, self.fusion_worker,
        )]

    async def close(self):
        if self.radar_stop:
            self.radar_stop.set()
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        await self.client.aclose()
        self.recorder.stop()

    def configure_camera(self, url):
        self.settings.camera_url = camera_url(url)
        self.camera_generation += 1
        self.frame = None
        self.detection = None
        self.camera_error = None
        self.camera_state = "CONNECTING" if self.settings.camera_url else "NOT_CONFIGURED"

    def configure_radar(self, enabled, address):
        self.settings.radar_enabled = enabled
        self.settings.radar_address = address
        self.radar_generation += 1
        self.radar_reading = None
        self.radar_received = None
        self.radar_error = None
        self.radar_state = "SEARCHING" if enabled and address else "NOT_CONFIGURED"
        if self.radar_stop:
            self.radar_stop.set()

    def snapshot(self):
        now = time.monotonic()
        age = (now - self.frame["received_mono"]) * 1000 if self.frame else None
        camera_available = bool(self.frame and age <= self.settings.camera_stale_s * 1000
                                and self.camera_state == "READY")
        radar_age = (now - self.radar_received) * 1000 if self.radar_received is not None else None
        radar_available = bool(self.radar_reading and radar_age <= self.settings.radar_stale_s * 1000
                               and self.radar_state == "STREAMING")
        camera_state = "STALE" if self.camera_state == "READY" and not camera_available else self.camera_state
        radar_state = "STALE" if self.radar_state == "STREAMING" and not radar_available else self.radar_state
        detection = self.detection_state(camera_available, now)
        return {
            "schema_version": 1, "server_time_utc": utc_now(),
            "mode": "MIXED" if camera_available or radar_available else "SIMULATION",
            "camera": {
                "source": "LIVE_NODE", "status": camera_state, "available": camera_available,
                "url": self.settings.camera_url, "error": self.camera_error,
                "receive_age_ms": round(age) if age is not None else None,
                "capture_timestamp_known": False,
                "frame": dict(self.frame["metadata"]) if self.frame else None,
            },
            "ir": {"source": "SYNTHETIC", "hardware_status": "UNAVAILABLE",
                   "eligible_for_live_fusion": False, "scenario": self.ir_scenario.value,
                   "reading": self.ir_reading},
            "radar": {
                "source": "LIVE_EXTERNAL", "status": radar_state,
                "available": radar_available, "error": self.radar_error,
                "address": self.settings.radar_address,
                "enabled": self.settings.radar_enabled,
                "receive_age_ms": round(radar_age) if radar_age is not None else None,
                "reading": self.radar_reading,
                "dropped_record_reports": self.dropped_record_reports,
            },
            "profile": {
                "selected": self.profile, "active": self.profile,
                "version": "demo-provisional-v2", "command_id": self.profile_command_id,
                "label": PROFILE_INFO[self.profile][0],
                "prior_weights": dict(PROFILES[self.profile]),
                "weights": applied_weights(PROFILES[self.profile]),
                "weights_status": PROFILE_INFO[self.profile][1],
                "ir_rule": ("IR is synthetic: its prior weight is applied as 0 and camera/radar are renormalised."
                            if IR_IS_SYNTHETIC else None),
                "executor": "LAPTOP", "applied": True,
            },
            "detection": detection,
            "edge_detection": self.edge_detection_state(camera_available),
            "fusion": self.current_fusion(now),
            "assessment": self.assessment(detection, self.current_fusion(now)),
            "recording": self.recorder.status(),
        }

    def current_fusion(self, now):
        if self.fusion is None or now - self.fusion["computed_mono"] > 3 * self.settings.fusion_interval_s:
            return None
        if self.fusion["profile_command_id"] != self.profile_command_id:
            return None  # Computed under the previous operator profile.
        return {key: value for key, value in self.fusion.items() if key != "computed_mono"}

    def edge_detection_state(self, camera_available):
        """ESP32 result for the current frame. Same camera as the laptop detector, so it is shown
        alongside it but not fused as an independent source."""
        result = {"status": "NOT_REPORTED", "inference_location": "ESP32", "output": "PERSON_SCORE_ONLY",
                  "input": "centre 240x240 crop, 96x96 grayscale", "threshold": EDGE_PERSON_THRESHOLD,
                  "accuracy_status": "NOT_EVALUATED_ON_OV7670", "fused": False, "frame_id": None,
                  "score": None, "person": None, "infer_ms": None, "prep_ms": None, "model": None}
        reported = self.frame["metadata"].get("node_person") if self.frame else None
        if not camera_available:
            result["status"] = "CAMERA_UNAVAILABLE"
        elif reported is None:
            pass  # Node firmware does not send on-node results.
        elif self.frame["metadata"]["content"] != "SCENE":
            result["status"] = "TEST_PATTERN"
        elif reported["status"] != "ok":
            result["status"] = "UNAVAILABLE"
        else:
            result.update(status="READY", frame_id=self.frame["metadata"]["frame_id"], score=reported["score"],
                          person=reported["score"] >= EDGE_PERSON_THRESHOLD, infer_ms=reported["infer_ms"],
                          prep_ms=reported["prep_ms"], model=reported["model"])
        return result

    def detection_state(self, camera_available, now):
        result = {
            "status": "MODEL_NOT_LOADED", "inference_location": "NONE", "model": None,
            "execution_note": None, "score_threshold": None, "error": self.detector_error,
            "accuracy_status": "NOT_EVALUATED_ON_OV7670",
            "frame_id": None, "person_count": None, "detections": [], "inference_ms": None,
            "input_width": None, "input_height": None,
        }
        if self.detector is None:
            if self.detector_error:
                result["status"] = "LOAD_FAILED"
            elif self.settings.detector_model:
                result["status"] = "LOADING"
            return result
        result.update(inference_location=self.detector.inference_location,
                      execution_note=getattr(self.detector, "profile_note", None),
                      model=self.detector.info.to_record(),
                      score_threshold=self.detector.score_threshold)
        current = self.detection
        if not camera_available:
            result["status"] = "CAMERA_UNAVAILABLE"
        elif self.frame["metadata"]["content"] != "SCENE":
            result["status"] = "TEST_PATTERN"
        elif current is None or (now - current["frame_received_mono"]) > self.settings.camera_stale_s:
            result["status"] = "ERROR" if self.detector_error else "WAITING_FOR_FRAME"
        else:
            result["status"] = "READY"
            result.update({key: current[key] for key in (
                "frame_id", "person_count", "detections", "inference_ms", "input_width", "input_height",
            )})
        return result

    @staticmethod
    def assessment(detection, fusion):
        person_count = detection["person_count"] if detection["status"] == "READY" else None
        if fusion and fusion["index"] is not None:
            sources = [name for name, part in fusion["contributions"].items() if part["available"]]
            status = ("FUSED_PROVISIONAL" if fusion["coverage_status"] == "FULL"
                      else f"{sources[0].upper()}_ONLY_PARTIAL_COVERAGE")
            return {
                "status": status, "inference_location": "LAPTOP", "fusion_enabled": True,
                "presence_score": None, "fusion_index": fusion["index"],
                "decision": fusion["decision"], "coverage": fusion["coverage"],
                "person_count": person_count,
                "reason": "Provisional weighted evidence index from " + " + ".join(sources)
                          + "; weights and thresholds are not calibrated and the index is not a probability.",
            }
        status = detection["status"]
        if status == "MODEL_NOT_LOADED":
            reason = "Person detector is not loaded; no automatic fused person result is produced."
        elif status == "READY":
            status, reason = "AWAITING_FUSION", "A current detection exists; the next fusion update is pending."
        else:
            reason = f"No current camera detection ({status.lower().replace('_', ' ')})."
        return {"status": status, "inference_location": detection["inference_location"],
                "fusion_enabled": False, "presence_score": None, "fusion_index": None,
                "decision": "INSUFFICIENT_EVIDENCE", "coverage": 0.0, "person_count": None, "reason": reason}

    async def fusion_worker(self):
        while True:
            previous = self.fusion["decision"] if self.fusion else None
            result = self.fuse_once()
            if result["decision"] != previous:
                await asyncio.to_thread(self.recorder.record, "fusion_decision", result)
            await asyncio.sleep(self.settings.fusion_interval_s)

    def fuse_once(self):
        state = self.snapshot()
        detection, radar = state["detection"], state["radar"]
        evidence = {"camera": camera_evidence(detection),
                    "radar": radar_evidence(radar["available"], radar["reading"])}
        result = self.fusion_engine.update(evidence, applied_weights(PROFILES[self.profile]),
                                           (self.profile, self.profile_command_id))
        result.update({
            "profile": self.profile, "profile_command_id": self.profile_command_id,
            "executor": "LAPTOP", "computed_at_utc": utc_now(),
            "camera_frame_id": detection["frame_id"],
            "radar_sequence": radar["reading"]["sequence"] if radar["available"] else None,
            "spatial_alignment": "UNVERIFIED",
        })
        self.fusion = {**result, "computed_mono": time.monotonic()}
        return result

    async def camera_worker(self):
        while True:
            if self.settings.camera_url:
                await self.fetch_camera()
            await asyncio.sleep(self.settings.camera_interval_s)

    async def fetch_camera(self):
        generation, url = self.camera_generation, self.settings.camera_url
        try:
            started = time.monotonic()
            async with self.client.stream("GET", url) as response:
                response.raise_for_status()
                headers = response.headers
                if "image/jpeg" not in headers.get("content-type", "").lower():
                    raise ValueError("Camera response was not JPEG")
                data = bytearray()
                async for chunk in response.aiter_bytes():
                    data.extend(chunk)
                    if len(data) > MAX_IMAGE_BYTES:
                        raise ValueError("Camera image exceeds the configured size limit")
            image_bytes = bytes(data)
            with Image.open(BytesIO(image_bytes)) as image:
                width, height = image.size
                if image.format != "JPEG" or width * height > 2_000_000:
                    raise ValueError("Unexpected camera image format/dimensions")
                image.verify()
            if generation != self.camera_generation:
                return
            self.camera_sequence += 1
            metadata = {
                "frame_id": f"camera-{generation}-{self.camera_sequence:08d}",
                "source": "LIVE_NODE", "received_at_utc": utc_now(),
                "hardware_sample_time_ms": None, "width": width, "height": height,
                "bytes": len(image_bytes),
                "fetch_duration_ms": round((time.monotonic() - started) * 1000, 1),
                # Node headers (firmware ares-node-0.2+); uptime is the node clock, not wall time.
                "node_frame_seq": header_int(headers, "x-ares-frame-seq"),
                "node_uptime_ms": header_int(headers, "x-ares-uptime-ms"),
                "node_rssi_dbm": header_int(headers, "x-ares-rssi-dbm"),
                "content": "SENSOR_TEST_PATTERN" if headers.get("x-ares-test-pattern") == "1" else "SCENE",
                "node_person": node_person(headers),
            }
            self.frame = {"metadata": metadata, "bytes": image_bytes, "received_mono": time.monotonic()}
            self.camera_state, self.camera_error = "READY", None
            self.frame_ready.set()
            await asyncio.to_thread(self.recorder.record, "camera_frame", metadata, image_bytes)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            if generation == self.camera_generation:
                self.camera_state = "ERROR"
                self.camera_error = f"Camera acquisition failed ({type(error).__name__})"

    async def detector_worker(self):
        if self.detector is None and self.settings.detector_model:
            try:
                from .detector import YoloxPersonDetector
                self.detector = await asyncio.to_thread(
                    YoloxPersonDetector, self.settings.detector_model, self.settings.detector_score_threshold,
                    profile=self.settings.detector_profile)
            except Exception as error:
                self.detector_error = f"Detector failed to load ({type(error).__name__})"
                return
        if self.detector is None:
            return
        while True:
            await self.frame_ready.wait()
            self.frame_ready.clear()
            frame, generation = self.frame, self.camera_generation
            # Sensor test patterns are not scenes; never report people in them.
            if frame is None or frame["metadata"]["content"] != "SCENE":
                continue
            try:
                result = await asyncio.to_thread(self.detector.detect, frame["bytes"])
            except asyncio.CancelledError:
                raise
            except Exception as error:
                self.detector_error = f"Detection failed ({type(error).__name__})"
                continue
            if generation != self.camera_generation:
                continue
            self.detector_error = None
            record = {"frame_id": frame["metadata"]["frame_id"], "completed_at_utc": utc_now(),
                      "inference_location": self.detector.inference_location,
                      "model_sha256": self.detector.info.sha256,
                      "score_threshold": self.detector.score_threshold, **result}
            self.detection = {**record, "frame_received_mono": frame["received_mono"]}
            await asyncio.to_thread(self.recorder.record, "person_detection", record)

    async def ir_worker(self):
        while True:
            elapsed = int((time.monotonic() - self.started) * 1000)
            self.ir_reading = self.ir.sample(self.ir_scenario, elapsed).to_record()
            self.ir_reading["generated_at_utc"] = utc_now()
            await asyncio.to_thread(self.recorder.record, "telemetry", self.snapshot())
            await asyncio.sleep(self.settings.ir_interval_s)

    def radar_report(self, generation, record):
        if generation != self.radar_generation:
            return
        self.radar_received = time.monotonic()
        self.radar_reading = dict(record)
        self.radar_reading.setdefault("received_at_utc", utc_now())
        if self.record_accepting and self.recorder.status()["active"]:
            try:
                self.radar_record_queue.put_nowait((self.recorder.status()["session_id"], self.radar_reading))
            except asyncio.QueueFull:
                self.dropped_record_reports += 1

    def radar_status(self, generation, state, error):
        if generation == self.radar_generation:
            self.radar_state, self.radar_error = state, error

    async def radar_recorder(self):
        while True:
            session_id, reading = await self.radar_record_queue.get()
            try:
                if self.recorder.status()["session_id"] == session_id:
                    await asyncio.to_thread(self.recorder.record, "radar_report", reading)
            finally:
                self.radar_record_queue.task_done()

    async def radar_worker(self):
        while True:
            if not self.settings.radar_enabled or not self.settings.radar_address:
                await asyncio.sleep(0.5)
                continue
            generation = self.radar_generation
            self.radar_stop = asyncio.Event()
            self.radar_status(generation, "SEARCHING", None)
            try:
                device = await find_radar(self.settings.radar_address, timeout=5.0)
                if generation != self.radar_generation:
                    continue
                if device is None:
                    raise RuntimeError("Configured radar was not advertising; disconnect its phone app and retry")
                await receive_reports(
                    device, lambda reading: self.radar_report(generation, reading),
                    lambda state, error: self.radar_status(generation, state, error),
                    password=self.settings.radar_password, stop=self.radar_stop,
                )
            except asyncio.CancelledError:
                raise
            except Exception as error:
                self.radar_status(generation, "ERROR", str(error))
                if "permission rejected" in str(error).lower():
                    self.radar_status(generation, "AUTH_FAILED", str(error))
                    while generation == self.radar_generation:
                        await asyncio.sleep(0.5)
            if generation == self.radar_generation:
                await asyncio.sleep(5.0)
