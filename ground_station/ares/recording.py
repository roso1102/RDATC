"""Local session recording. Credentials and generated recordings stay out of Git."""

from datetime import datetime, timezone
import json
from pathlib import Path
import threading
import uuid


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Recorder:
    def __init__(self, directory: Path):
        self.directory = directory
        self._lock = threading.Lock()
        self._stream = None
        self._manifest = None
        self._path = None
        self.error = None

    def status(self):
        return {
            "active": self._stream is not None,
            "session_id": self._manifest["session_id"] if self._manifest else None,
            "events": self._manifest["events"] if self._manifest else 0,
            "frames": self._manifest["frames"] if self._manifest else 0,
            "error": self.error,
        }

    def start(self, initial_state: dict):
        with self._lock:
            if self._stream:
                raise RuntimeError("Recording is already active")
            session_id = uuid.uuid4().hex
            self._path = self.directory / session_id
            (self._path / "frames").mkdir(parents=True)
            self._manifest = {
                "schema_version": 1, "session_id": session_id,
                "started_at_utc": utc_now(), "stopped_at_utc": None,
                "events": 0, "frames": 0, "mode": "RECORDED_SESSION",
                "initial_state": initial_state,
                "policy": "1Hz telemetry and IR; every acquired frame; BLE reports while recording",
            }
            self._stream = (self._path / "events.jsonl").open("a", encoding="utf-8")
            self.error = None
            self._write_manifest()
            return self.status()

    def _write_manifest(self):
        (self._path / "manifest.json").write_text(
            json.dumps(self._manifest, indent=2, allow_nan=False), encoding="utf-8"
        )

    def record(self, kind: str, data: dict, image: bytes | None = None):
        with self._lock:
            if self._stream is None:
                return
            try:
                payload = dict(data)
                if image is not None:
                    filename = f"frames/{data['frame_id']}.jpg"
                    (self._path / filename).write_bytes(image)
                    payload["image_file"] = filename
                    self._manifest["frames"] += 1
                self._manifest["events"] += 1
                event = {"event_id": self._manifest["events"], "kind": kind,
                         "recorded_at_utc": utc_now(), "data": payload}
                self._stream.write(json.dumps(event, allow_nan=False) + "\n")
                self._stream.flush()
            except OSError:
                self.error = "Recording storage write failed"
                self._stream.close()
                self._stream = None

    def stop(self):
        with self._lock:
            if self._stream:
                self._stream.close()
                self._stream = None
                self._manifest["stopped_at_utc"] = utc_now()
                self._write_manifest()
            return self.status()
