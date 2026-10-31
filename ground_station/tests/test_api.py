import asyncio
from io import BytesIO
import json
from pathlib import Path
import tempfile
import time
import unittest

from fastapi.testclient import TestClient
import httpx
from PIL import Image

from ares.api import create_app
from ares.backend import Hub, Settings
from ares.detector import ModelInfo


def jpeg_fixture():
    output = BytesIO()
    Image.new("RGB", (32, 24), (20, 40, 60)).save(output, format="JPEG")
    return output.getvalue()


class FakeDetector:
    """Deterministic stand-in: proves plumbing and labels, not detection accuracy."""

    inference_location = "LAPTOP"
    score_threshold = 0.35
    info = ModelInfo("fake", "test", "n/a", "test fixture", "0" * 64, 416)

    def __init__(self):
        self.calls = 0

    def detect(self, _):
        self.calls += 1
        return {"detections": [{"label": "person", "score": 0.9, "box_xyxy": [1.0, 2.0, 10.0, 20.0],
                                "box_basis": "SOURCE_PIXELS"}],
                "person_count": 1, "inference_ms": 1.0, "input_width": 32, "input_height": 24}


def wait_state(client, predicate):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        state = client.get("/api/state").json()
        if predicate(state):
            return state
        time.sleep(0.02)
    raise AssertionError("Expected backend state was not reached")


class APITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def settings(self, **kwargs):
        return Settings(recording_dir=Path(self.temp.name), ir_interval_s=0.03, **kwargs)

    def test_missing_hardware_is_not_replaced_by_fake_live_inputs(self):
        with TestClient(create_app(self.settings())) as client:
            state = wait_state(client, lambda state: state["ir"]["reading"] is not None)
            self.assertEqual(state["mode"], "SIMULATION")
            self.assertEqual(state["camera"]["status"], "NOT_CONFIGURED")
            self.assertFalse(state["radar"]["available"])
            self.assertEqual(state["ir"]["reading"]["source"], "SYNTHETIC")
            self.assertFalse(state["ir"]["reading"]["eligible_for_live_fusion"])
            self.assertIsNone(state["assessment"]["presence_score"])
            self.assertEqual(client.get("/api/camera/frame").status_code, 503)
            self.assertEqual(client.post("/api/config/radar", json={"enabled": True}).status_code, 400)

    def test_profile_and_synthetic_scenario_are_independent(self):
        with TestClient(create_app(self.settings())) as client:
            client.post("/api/config/ir", json={"scenario": "hot_background"}).raise_for_status()
            profile = client.post("/api/config/profile", json={"profile": "reduced_visibility"}).json()
            state = client.get("/api/state").json()
            self.assertEqual(state["ir"]["scenario"], "hot_background")
            self.assertEqual(profile["weights"]["ir"], 0)
            self.assertTrue(profile["applied"])
            self.assertEqual(profile["weights_status"], "PROVISIONAL_NOT_CALIBRATED")
            self.assertEqual(client.post("/api/config/profile", json={"profile": "unknown"}).status_code, 422)
            fire = client.post("/api/config/profile", json={"profile": "fire_smoke"}).json()
            self.assertEqual(fire["weights_status"], "LITERATURE_PRIOR_UNCALIBRATED")
            self.assertEqual(fire["prior_weights"]["ir"], 0.1)
            self.assertEqual(fire["weights"]["ir"], 0.0)
            self.assertIn("synthetic", fire["ir_rule"])
            # Selecting a fire profile must not create temperature evidence or change the IR scenario.
            state = client.get("/api/state").json()
            self.assertEqual(state["ir"]["scenario"], "hot_background")
            self.assertFalse(state["ir"]["eligible_for_live_fusion"])
            self.assertEqual(client.post("/api/config/camera", json={"url": "file:///private"}).status_code, 400)

    def test_preview_clients_share_one_acquisition_and_stale_frames_are_unavailable(self):
        calls = []

        def camera(request):
            calls.append(request.url)
            return httpx.Response(200, content=jpeg_fixture(), headers={"content-type": "image/jpeg"})

        app = create_app(self.settings(camera_url="http://camera.test/capture", camera_interval_s=10),
                         transport=httpx.MockTransport(camera))
        with TestClient(app) as client:
            state = wait_state(client, lambda state: state["camera"]["available"])
            self.assertEqual(state["mode"], "MIXED")
            first = client.get("/api/camera/frame")
            second = client.get("/api/camera/frame")
            self.assertEqual(first.headers["x-frame-id"], second.headers["x-frame-id"])
            self.assertEqual(len(calls), 1)
            self.assertFalse(state["camera"]["capture_timestamp_known"])
            app.state.hub.frame["received_mono"] -= 10
            self.assertEqual(client.get("/api/camera/frame").status_code, 503)
            self.assertEqual(client.get("/api/state").json()["camera"]["status"], "STALE")

    def test_recorded_sources_and_images_retain_provenance(self):
        transport = httpx.MockTransport(lambda _: httpx.Response(
            200, content=jpeg_fixture(), headers={"content-type": "image/jpeg"}))
        app = create_app(self.settings(camera_url="http://camera.test/capture", camera_interval_s=0.03),
                         transport=transport)
        with TestClient(app) as client:
            session = client.post("/api/recording/start").json()["session_id"]
            self.assertEqual(client.post("/api/recording/start").status_code, 409)
            wait_state(client, lambda state: state["recording"]["events"] >= 3
                       and state["recording"]["frames"] >= 1)
            stopped = client.post("/api/recording/stop").json()
            self.assertFalse(stopped["active"])
            response = client.get(f"/api/recordings/{session}/events")
            self.assertEqual(response.headers["x-ares-mode"], "REPLAY")
            events = [json.loads(line) for line in response.text.splitlines()]
            telemetry = next(event["data"] for event in events if event["kind"] == "telemetry")
            self.assertEqual(telemetry["ir"]["reading"]["source"], "SYNTHETIC")
            self.assertFalse(telemetry["ir"]["reading"]["eligible_for_live_fusion"])
            frames = [event for event in events if event["kind"] == "camera_frame"]
            self.assertTrue((Path(self.temp.name) / session / frames[0]["data"]["image_file"]).exists())
            self.assertEqual(client.get("/api/recordings").json()["sessions"][0]["session_id"], session)


class DetectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def app(self, detector, headers=None):
        response_headers = {"content-type": "image/jpeg", **(headers or {})}
        transport = httpx.MockTransport(lambda _: httpx.Response(
            200, content=jpeg_fixture(), headers=response_headers))
        settings = Settings(recording_dir=Path(self.temp.name), ir_interval_s=0.03,
                            camera_url="http://camera.test/capture", camera_interval_s=0.05)
        return create_app(settings, transport=transport, detector=detector)

    def test_detections_are_laptop_camera_only_and_match_a_frame(self):
        detector = FakeDetector()
        with TestClient(self.app(detector, {"x-ares-frame-seq": "7", "x-ares-uptime-ms": "1234",
                                            "x-ares-rssi-dbm": "-18"})) as client:
            session = client.post("/api/recording/start").json()["session_id"]
            state = wait_state(client, lambda state: state["detection"]["status"] == "READY"
                               and state["fusion"] is not None and state["fusion"]["index"] is not None)
            detection, assessment = state["detection"], state["assessment"]
            self.assertEqual(detection["inference_location"], "LAPTOP")
            self.assertEqual(detection["accuracy_status"], "NOT_EVALUATED_ON_OV7670")
            self.assertEqual(detection["person_count"], 1)
            self.assertTrue(detection["frame_id"].startswith("camera-0-"))
            # Radar is absent, so camera-only fusion must say partial coverage, never full.
            self.assertEqual(assessment["status"], "CAMERA_ONLY_PARTIAL_COVERAGE")
            self.assertTrue(assessment["fusion_enabled"])
            self.assertIsNone(assessment["presence_score"])
            self.assertEqual(assessment["coverage"], 0.7)
            self.assertEqual(state["fusion"]["contributions"]["radar"]["available"], False)
            self.assertEqual(state["fusion"]["spatial_alignment"], "UNVERIFIED")
            frame = state["camera"]["frame"]
            self.assertEqual((frame["node_frame_seq"], frame["node_uptime_ms"], frame["node_rssi_dbm"]),
                             (7, 1234, -18))
            self.assertEqual(frame["content"], "SCENE")
            self.assertEqual(client.get("/api/health").json()["detector_status"], "READY")
            wait_state(client, lambda state: state["recording"]["events"] >= 3)
            client.post("/api/recording/stop").raise_for_status()
            events = [json.loads(line) for line in
                      client.get(f"/api/recordings/{session}/events").text.splitlines()]
            recorded = next(event["data"] for event in events if event["kind"] == "person_detection")
            self.assertEqual(recorded["inference_location"], "LAPTOP")
            self.assertNotIn("frame_received_mono", recorded)

    def test_camera_and_radar_fuse_with_full_coverage_and_record_decisions(self):
        with TestClient(self.app(FakeDetector())) as client:
            hub = client.app.state.hub
            session = client.post("/api/recording/start").json()["session_id"]
            hub.radar_state = "STREAMING"
            deadline = time.monotonic() + 3
            state = None
            while time.monotonic() < deadline:
                hub.radar_report(hub.radar_generation, {"presence": True, "valid": True, "sequence": 9})
                state = client.get("/api/state").json()
                if state["assessment"]["decision"] == "POSSIBLE_PERSON":
                    break
                time.sleep(0.05)
            assessment = state["assessment"]
            self.assertEqual(assessment["status"], "FUSED_PROVISIONAL")
            self.assertEqual(assessment["decision"], "POSSIBLE_PERSON")
            self.assertEqual(assessment["coverage"], 1.0)
            self.assertIsNone(assessment["presence_score"])
            self.assertEqual(state["fusion"]["radar_sequence"], 9)
            # Fusion runs on its own 0.5 s tick, so it may cite a slightly older frame.
            self.assertTrue(state["fusion"]["camera_frame_id"].startswith("camera-0-"))
            client.post("/api/recording/stop").raise_for_status()
            kinds = [json.loads(line)["kind"] for line in
                     client.get(f"/api/recordings/{session}/events").text.splitlines()]
            self.assertIn("fusion_decision", kinds)

    def test_profile_change_withdraws_the_previous_profiles_fusion_result(self):
        with TestClient(self.app(FakeDetector())) as client:
            hub = client.app.state.hub
            wait_state(client, lambda state: state["fusion"] is not None)
            hub.settings.fusion_interval_s = 10  # Freeze: the next tick will not come during the check.
            time.sleep(0.6)
            client.post("/api/config/profile", json={"profile": "reduced_visibility"}).raise_for_status()
            state = client.get("/api/state").json()
            self.assertIsNone(state["fusion"])
            self.assertFalse(state["assessment"]["fusion_enabled"])
            self.assertEqual(hub.fuse_once()["profile"], "reduced_visibility")
            self.assertEqual(client.get("/api/state").json()["fusion"]["profile"], "reduced_visibility")

    def test_esp32_result_travels_with_its_frame_and_is_not_fused(self):
        headers = {"x-ares-person-status": "ok", "x-ares-person-score": "0.812",
                   "x-ares-person-infer-ms": "57", "x-ares-person-prep-ms": "4",
                   "x-ares-person-model": "tflm-person-detect-int8-96"}
        with TestClient(self.app(FakeDetector(), headers)) as client:
            state = wait_state(client, lambda state: state["edge_detection"]["status"] == "READY")
            edge = state["edge_detection"]
            self.assertEqual(edge["inference_location"], "ESP32")
            self.assertEqual(edge["frame_id"], state["camera"]["frame"]["frame_id"])
            self.assertEqual((edge["score"], edge["person"], edge["infer_ms"]), (0.812, True, 57))
            self.assertEqual(edge["output"], "PERSON_SCORE_ONLY")
            self.assertFalse(edge["fused"])
            fusion = wait_state(client, lambda state: state["fusion"] is not None)["fusion"]
            self.assertEqual(set(fusion["contributions"]), {"camera", "radar"})

    def test_esp32_result_states_for_old_firmware_failure_and_test_pattern(self):
        cases = [({}, "NOT_REPORTED"),
                 ({"x-ares-person-status": "unavailable"}, "UNAVAILABLE"),
                 ({"x-ares-person-status": "ok", "x-ares-person-score": "1.7"}, "UNAVAILABLE"),
                 ({"x-ares-person-status": "ok", "x-ares-person-score": "0.9", "x-ares-test-pattern": "1"},
                  "TEST_PATTERN")]
        for headers, expected in cases:
            with self.subTest(expected=expected), TestClient(self.app(FakeDetector(), headers)) as client:
                state = wait_state(client, lambda state: state["camera"]["available"])
                self.assertEqual(state["edge_detection"]["status"], expected)
                self.assertIsNone(state["edge_detection"]["score"])

    def test_sensor_test_pattern_is_never_run_through_the_detector(self):
        detector = FakeDetector()
        with TestClient(self.app(detector, {"x-ares-test-pattern": "1"})) as client:
            state = wait_state(client, lambda state: state["camera"]["available"])
            time.sleep(0.2)
            state = client.get("/api/state").json()
            self.assertEqual(state["camera"]["frame"]["content"], "SENSOR_TEST_PATTERN")
            self.assertEqual(state["detection"]["status"], "TEST_PATTERN")
            self.assertIsNone(state["assessment"]["person_count"])
            self.assertEqual(detector.calls, 0)

    def test_stale_camera_withdraws_the_detection(self):
        with TestClient(self.app(FakeDetector())) as client:
            wait_state(client, lambda state: state["detection"]["status"] == "READY")
            hub = client.app.state.hub
            hub.settings.camera_url = None  # Stop new frames without resetting state.
            hub.frame["received_mono"] -= 10
            hub.detection["frame_received_mono"] -= 10
            state = client.get("/api/state").json()
            self.assertEqual(state["detection"]["status"], "CAMERA_UNAVAILABLE")
            self.assertIsNone(state["assessment"]["person_count"])

    def test_missing_model_file_reports_load_failure(self):
        settings = Settings(recording_dir=Path(self.temp.name), ir_interval_s=0.03,
                            detector_model=Path(self.temp.name) / "missing.onnx")
        with TestClient(create_app(settings)) as client:
            state = wait_state(client, lambda state: state["detection"]["status"] == "LOAD_FAILED")
            self.assertEqual(state["detection"]["inference_location"], "NONE")
            self.assertIsNone(state["assessment"]["person_count"])


class CameraGenerationTests(unittest.IsolatedAsyncioTestCase):
    async def test_reconfiguration_discards_an_old_inflight_response(self):
        entered, release = asyncio.Event(), asyncio.Event()

        async def camera(_):
            entered.set()
            await release.wait()
            return httpx.Response(200, content=jpeg_fixture(), headers={"content-type": "image/jpeg"})

        hub = Hub(Settings(camera_url="http://old.test/capture"))
        hub.client = httpx.AsyncClient(transport=httpx.MockTransport(camera))
        try:
            task = asyncio.create_task(hub.fetch_camera())
            await entered.wait()
            hub.configure_camera(None)
            release.set()
            await task
            self.assertIsNone(hub.frame)
            self.assertEqual(hub.camera_state, "NOT_CONFIGURED")
        finally:
            await hub.client.aclose()
