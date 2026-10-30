# ARES first hardware implementation

Updated: 31 October 2026, Asia/Calcutta. Proposed implementation and acceptance targets. The camera baseline now compiles with the identified hardware configuration; no application firmware has been uploaded and no runtime performance has been measured. See [compile validation](docs/validation/camera-build-2026-10-31.md).

## Confirmed inputs and information still needed

- User has the sensors connected to an ESP32-S3. The reference Arduino camera code has been inspected; IR/radar GPIOs and live operation still need confirmation.
- Supplied circuit image: [wiring-2026-10-31.png](docs/hardware/wiring-2026-10-31.png).
- Diagram labels: OV7670, MLX90614, LD2410, and SX1262 with its own antenna.
- User explicitly excludes LoRa/SX1262 from the current demo. Active sensors are camera, IR and radar; use ESP32 Wi-Fi for communication.
- Confirmed communication: local Wi-Fi for real camera frames; USB for programming and debugging.
- Ground station is the laptop; Raspberry Pi is deferred and GPS is omitted.
- Need the actual board/module marking, flash/PSRAM configuration, exact active sensor variants, IR/radar pin and power wiring, selected Arduino board/core version, COM port, and current live-camera status/address.
- The circuit image alone does not establish GPIO assignments or power correctness. Reference camera definitions are documented in PLAN.md.
- Reference code is under `ARES_Firmware/OV7670/` in RDATC branch `rounak-vyas`, inspected commit `e2e770a8ebfbef6a6824544be477ca15c3299e1c`. No current ground-station app or trained custom model was found. During initial inspection Arduino CLI was not found on PATH and no serial port was identified; the following setup and hardware updates supersede those initial limitations.
- Setup update, 31 October 2026: portable Arduino CLI 1.5.1 is installed locally; use the root `arduino-cli.cmd` launcher. Verification reused installed ESP32 core 3.3.7 and found an ESP32 Family Device at COM3. See [portable setup instructions](docs/setup/arduino-cli.md) and the subsequent hardware identification below.
- Hardware update, 31 October 2026: read-only esptool identification on COM3 confirmed ESP32-S3 with 8 MB flash and 8 MB embedded PSRAM (AP_3v3). Selected compile settings and remaining runtime checks are in [docs/hardware/board-config.md](docs/hardware/board-config.md). The reference sketch's N16R8 assumption is superseded by this observation.

## Imminent interactive demo priority

The camera will face visitors from the front. Overhead mounting, dataset collection and evaluation are a later, separate milestone. Follow the current acquisition-first checklist in PLAN.md before the longer-term candidate pipeline below.

Must-have: real camera frames and sensor readings; a React/FastAPI viewer; frontal person detection with an explicit inference-location label; operator-selected profiles; recorded, explainable evidence; invalid/stale states; and a rehearsed reduced-visibility experiment. Weights are selected using a labelled pilot, not assumed correct.

Proposed deadline fallback: if the on-board detector cannot be integrated and measured in time, run the frontal detector and necessary provisional fusion on the laptop, clearly report LAPTOP execution, and retain ESP32 inference/fusion as pending work. Do not claim this fallback proves edge-AI performance. The normal target remains on-board acquisition, inference and fusion.

A generic 3D avatar with overhead/perspective viewing follows the live pipeline. Pose-driven avatar animation is optional and uses the same camera evidence. Position requires floor calibration; uncalibrated positions are schematic. Lost visual tracking must not become a continuously confirmed avatar location.

Reduced visibility can be demonstrated using a removable translucent sheet in front of only the camera. Label this optical degradation, not real smoke validation. Keep real raw readings visible when the operator changes profiles. An opaque cover is a separate unavailable-vision test. Optional digital degradation must affect the detector input and be explicitly labelled.

Use empty scenes, people, idle/warm phones, and warm nonhuman objects as labelled trials. IR initially provides thermal context with zero human-presence weight until a held-out benefit is demonstrated. RSSI is initially diagnostic; CSI and any Wi-Fi fusion contribution are optional experimental work after the core pipeline is stable.

## Proposed repository layout

```text
firmware/ares_node/ares_node.ino   # User sketch, reviewed and extended in place
firmware/ares_node/               # Sensor drivers, profile/fusion, transport, metrics
ground_station/                  # Python API, ingestion, capture storage, benchmark reports
web/                             # Small React + Vite viewer, built and served locally
models/                          # Model version, input/preprocessing definition, export manifest
benchmarks/                      # Labels, evaluation scripts, and recorded test manifests
docs/hardware/                   # Circuit diagram and verified pin table
```

Python FastAPI plus a small React/Vite viewer is the proposed stack. No remote deployment is required. These folders are an implementation layout, not a claim that their applications have been created.

## Live data path

1. ESP32 captures a real camera frame and assigns a frame ID and monotonic capture timestamp.
2. It processes a reduced image for local inference and sends a preview copy at a bounded independent rate over Wi-Fi.
3. Laptop receives telemetry through a local API; preview frames are served to the browser by the Python backend. Start with individual JPEG frames or a low-rate MJPEG preview after capture is proven stable.
4. If the camera remains OV7670, it does not produce native JPEG; software JPEG conversion consumes CPU and extra memory. Start at a low resolution and rate and measure this cost. Do not configure the sensor as a JPEG-native camera.
5. Telemetry carries the frame ID, sensor timestamps, selected profile/configuration version, evidence scores, validity flags, coverage, result, and timing/memory metrics.
6. Browser overlays only results matched to the displayed frame. Old frames retain their true timestamps and receive an explicit stale/disconnected indication.
7. Laptop clock synchronisation or measured clock-offset estimation is needed for capture-to-display latency. Keep node-local durations separate from receive-to-display durations until clocks are aligned.
8. Use bounded queues: discard outdated preview frames rather than accumulate lag. Sensor acquisition and assessment take priority over preview throughput.

## Candidate edge algorithms

These are proposed target edge algorithms, not implemented or validated results. Custom model training must not block the explicitly labelled laptop fallback for the imminent demo.

### Camera

- Candidate Arduino-oriented model: **FOMO using a small MobileNetV2 backbone, full INT8 quantisation**, initially 96x96 RGB input. Benchmark the smallest usable backbone and increase resolution only if needed and affordable.
- Train/adapt using labelled frames from the actual camera, viewpoint, distances, illumination, and poses. No suitable custom model or labelled dataset exists in the workspace yet.
- Use frontal recordings for the current demo. Real overhead data and held-out overhead tests are needed before claiming aerial-view performance; rotating the rendered avatar does not supply that validation.
- FOMO returns object centroids rather than measured object extent. The UI should show point markers/centres; do not present drawn heat-map cells as accurate body bounding boxes or 3D coordinates.
- Preprocessing: fixed crop/letterbox policy, resize and model-specific quantisation. Export the preprocessing definition and preserve the coordinate mapping to the source frame.
- Basic image-quality features: mean luminance, clipped-pixel fraction, and sharpness. Report these diagnostically; do not automatically alter the selected disaster profile or its valid-sensor weights.
- Frame differencing is a diagnostic/motion baseline, not proof of a human. Stationary people must be represented in validation.
- FOMO needs training. A separate pre-trained baseline to investigate is Espressif's pedestrian detector, but its ESP-IDF component integration is not a drop-in Arduino replacement; do not introduce both inference stacks in the first build.

### Radar and temperature

- Parse the radar's actual UART protocol, validate complete frames, timestamp reports, and apply bounded temporal debounce. No raw-radar or micro-Doppler learning claim for a module exposing processed presence results.
- For MLX90614, read object and sensor temperature; apply validity checks and a short median filter to isolated spikes. The sensor-temperature value is not remote ground ambient air temperature.
- Temperature contrast is supporting evidence over the sensor's field of view. Its human-presence mapping must be established experimentally; report it as unavailable/unvalidated until then rather than fabricate a calibrated human probability.

### Fusion

- Apply only the explicitly operator-selected profile. Keep the valid-input weights fixed within that profile.
- Map measurements to documented comparable evidence scores before fusion. Temperature, radar energy, and camera scores must not be averaged in their raw units.
- Compute the weighted score from valid, sufficiently aligned observations; output evidence coverage and disagreement separately. Do not let one remaining input become certain merely by renormalisation.
- Apply a two-threshold hysteresis state machine and a configurable persistence period to reduce flicker. Include PRESENT_EVIDENCE, NO_DETECTION, UNCERTAIN, and INSUFFICIENT_EVIDENCE semantics; NO_DETECTION is not a guarantee of absence.
- Fuse at a calibrated common scene/zone level initially. Do not assign broad radar or temperature evidence independently to every camera centroid.
- Synthetic tests validate arithmetic, profile switching, timeouts, hysteresis, and serialisation. Real labelled data establishes detection performance.

## Validation measurements

| Area | Measurements |
|---|---|
| Detection | Precision, recall, F1, false alerts/hour, misses per condition; centroid matching with a declared tolerance and one-to-one matching for localisation |
| Temporal behaviour | Time to first alert, time to clear, p50/p95 latency, missed transitions; report persistence delay |
| Edge execution | Preprocess, inference, postprocess and fusion time separately; complete capture-to-assessment time; throughput under concurrent streaming |
| Memory and build | Flash footprint, model bytes, tensor arena/activations, frame/conversion buffers, internal RAM and PSRAM, minimum free heap, largest free block, task stack high-water marks |
| Live preview | Delivered FPS, corrupted/dropped frames, frame age, queue depth, bytes/sec, reconnection time |
| Faults/stability | Sensor timeouts, stale input exclusion, resets, brownouts, watchdog events, Wi-Fi loss, unavailable evidence, recovery time |
| Power | Measured current/power during capture, inference and concurrent Wi-Fi/radio operation; do not infer physical energy from software timers |
| Quantisation | Compare float and deployed INT8 predictions on the same held-out samples; record accuracy/localisation changes |

Provisional demo engineering targets: two complete assessments/second; p95 capture-to-assessment at most 500 ms; at least three fresh preview frames/second at the chosen low resolution; p95 frame age at most one second; p95 alert delay at most two seconds for the configured persistence policy. These targets may be revised after the initial board benchmark and are not promised capabilities.

Memory acceptance requires a complete firmware fit, no allocation failures, and explicit headroom for runtime/network peaks. A model-only memory estimate does not establish feasibility. Run an initial one-hour simultaneous sensing/inference/streaming soak test with no unexplained resets or progressive memory loss; report observed failures rather than treating the test as proof of universal reliability.

Do not set a claimed detection accuracy before collecting ground truth. Predeclare the test conditions and evaluation criteria. Tune on development sessions and hold out separate sessions/people; avoid splitting adjacent frames from one video between training and testing. Include stationary/lying people, empty scenes, hot non-human objects, poor illumination, occlusion, wrong disaster profiles, sensor faults, and changed backgrounds.

Compare sensor-only methods, equal weights, one global weight set, and operator-selected profiles on the same observations. Keep model and profile versions, thresholds, dataset split, and ground-truth labels with each report.

## Evidence of genuine onboard execution

- Run inference and fusion with laptop-side inference disabled.
- Produce node-originated scores and timing counters through USB.
- Compare a fixed labelled image buffer's output on the laptop export and on the board.
- Benchmark camera-only, model-only, and integrated sensing + inference + Wi-Fi preview builds.
- If inference runs on the laptop temporarily, label the dashboard execution location as LAPTOP; do not describe it as ESP32 edge inference.

## Bring-up order

1. Review the supplied sketch and verify pin allocation, module identity, memory configuration, and power connections.
2. Obtain real camera frames and individual live sensor readings without AI.
3. Show timestamped real frames and telemetry in the laptop viewer.
4. Validate profile commands, fusion/state logic, and missing/stale data handling.
5. Collect and label camera/sensor recordings and deploy a model that passes a static-buffer board test.
6. Run integrated benchmarks and fault tests; then expand the UI/map features.

## Primary references

- [Espressif camera driver](https://github.com/espressif/esp32-camera): OV7670 formats, PSRAM and Wi-Fi/capture constraints.
- [FOMO documentation](https://docs.edgeimpulse.com/studio/projects/learning-blocks/blocks/object-detection/fomo): centroid detection and configurable MobileNetV2 backbone/input.
- [Arduino model-library deployment](https://docs.edgeimpulse.com/hardware/deployments/run-arduino-2-0): export and static-buffer inference verification. Verify compatible core/toolchain versions for the actual build.
- [Espressif heap instrumentation](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/system/heap_debug.html): minimum heap and largest free block measurements.
- [Espressif pedestrian model](https://github.com/espressif/esp-dl/blob/master/models/pedestrian_detect/README.md): alternative model baseline, not a completed Arduino integration.
