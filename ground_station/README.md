# ARES laptop ground station

Implemented: local FastAPI backend, React dashboard, direct radar BLE receiver/parser, explicit synthetic IR, source/status records and local session recording/export. Person detection, calibrated fusion and the 3D avatar are not implemented yet. The real camera path exists but awaits the ESP32 address/runtime validation.

## Python environment

Use a project virtual environment. This workspace uses D:/ARES/.venv with CPython 3.12.14; all backend/Bluetooth/test packages were installed there.

For a fresh checkout, from the project root with CPython 3.12+ installed:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r ground_station\requirements-dev.txt
```

Alternatively, with uv:

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe -r ground_station\requirements-dev.txt
```

The backend does not need a global Python package install. See requirements.txt for runtime dependencies and requirements-dev.txt for tests.

## Build the React viewer

From web/:

```powershell
npm ci
npm run build
```

JavaScript dependencies live in web/node_modules. The production build goes into ignored web/dist and is served by FastAPI. For frontend development, npm run dev uses a local proxy to the backend.

## Run

From the project root:

```powershell
.\start-backend.cmd
```

Open http://127.0.0.1:8000. The backend binds to loopback and runs one worker to keep camera/BLE acquisition single-owner. If port 8000 is already occupied by this app, use the running instance instead of starting another; stop a foreground launch with Ctrl+C.

Enter the actual ESP32 /capture URL in the dashboard when available. Until then the camera shows NOT CONFIGURED and no fake image is displayed. Scan/select or enter the radar's known Bluetooth address, then connect. Disconnect HLKRadarTool from the radar first: the sensor permits only one BLE client.

Optional process environment before launch:

```powershell
$env:ARES_CAMERA_URL = 'http://<actual-ESP32-IP>/capture'
$env:ARES_RADAR_ADDRESS = '<actual-radar-Bluetooth-address>'
$env:ARES_RADAR_ENABLED = '1'
.\start-backend.cmd
```

Leave the camera variable unset when its address is unknown. An altered radar password can be supplied through the local ARES_RADAR_PASSWORD environment variable; never commit it. The manufacturer default is used otherwise. Environment variables are read at process startup; UI configuration is session-local, not a persistent settings file.

## Inputs and outputs

- Camera: one bounded worker requests real JPEGs and caches the newest frame. Preview clients share that cache. Receive age is explicit; physical capture time is unknown with the current firmware endpoint.
- Radar: direct laptop BLE, permission acknowledgement, bounded notification/report parsing, timestamps, stale states and retry. Known-address discovery also works when advertisements omit a name. No threshold or firmware changes are made.
- IR: seeded laptop fixtures with permanent SYNTHETIC source, UNAVAILABLE physical hardware and false live-fusion eligibility. Scenario controls are independent of the selected visibility profile.
- Global mode: MIXED when at least one fresh hardware source exists alongside synthetic IR, otherwise SIMULATION. Individual missing inputs remain unavailable.
- Profiles: provisional example clear/reduced-visibility weights for configuration/transport checks. They are not calibrated and no fused person score is produced while the detector is missing.

## API

- GET /api/health and /api/state: service/source health and current evidence.
- GET /api/camera/frame: latest fresh actual JPEG, or HTTP 503; response includes its frame ID and receive-time basis.
- POST /api/config/camera: camera URL or null.
- POST /api/config/ir: scenario baseline, warm_target, hot_background or unavailable.
- POST /api/config/profile: clear or reduced_visibility; acknowledged local profile/version.
- POST /api/radar/scan and /api/config/radar: discovery and explicit selected-device connection.
- POST /api/recording/start and /stop: capture local sessions.
- GET /api/recordings and /api/recordings/{id}/events: manifests and JSONL download marked REPLAY.
- GET /docs: interactive API schema.

Recordings are under ignored benchmarks/sessions: telemetry/IR at approximately 1 Hz, acquired JPEGs, and BLE reports while recording. Sources, scenario/model/profile metadata and real receive timestamps are retained. They are not automatically labelled human ground truth. Exporting a recording does not inject replay data into the live acquisition path.

## Validate

From the project root:

```powershell
.\run-tests.cmd
```

Or from ground_station/ with the project interpreter:

```powershell
..\.venv\Scripts\python.exe -m pytest tests -q
..\.venv\Scripts\python.exe -m ares.ir_simulator --scenario warm_target --samples 3 --seed 42
..\.venv\Scripts\python.exe -m ares.radar_ble scan --timeout 8
..\.venv\Scripts\python.exe -m ares.radar_ble listen --address <actual-address> --duration 10
```

Do not run the BLE listener and backend connection against the same radar simultaneously. The receiver needs an actual powered sensor and local Bluetooth access; the automated protocol/API tests use declared fixtures and do not establish physical detection accuracy.

See [backend validation](../docs/validation/backend-2026-10-31.md), [source contract](../docs/synthetic-ir-demo.md) and [radar protocol notes](../docs/hardware/radar-integration.md).
