# ARES current implementation plan

Updated: 31 October 2026, Asia/Calcutta. Camera compilation passed; runtime acquisition and the application remain unvalidated. This revision incorporates nonworking IR hardware and the separate radar app/web system.

## Architecture and actual status

| Part | Role | Status |
|---|---|---|
| ESP32-S3 / OV7670 | Real image acquisition, health and Wi-Fi preview | Compiles; runtime camera/PSRAM/network checks pending |
| MLX90614 hardware | Deferred physical repair/evaluation | User reports not working |
| Laptop IR provider | Explicit seeded synthetic fixtures | Integrated into API, UI and recordings with persistent labels |
| Separate radar / BLE | Direct laptop receiver using documented characteristics/reports | Authentication/report stream verified; labelled accuracy/zone/outage trials pending |
| Laptop processing | Camera worker/cache, recording, external radar and source/status API | Implemented; actual camera URL, detector and fusion pending |
| React / Three.js | Evidence/provenance and illustrative avatar | React dashboard implemented; 3D/pose pending |

No LoRa, GPS, Raspberry Pi or radar UART work is part of this demo. Onboard camera inference is a separate future benchmarked milestone. Current external-source fusion belongs on the laptop; onboard fusion would require an additional return-data protocol and is deferred.

## Working layout

- firmware/ares_node/: camera sketch and local ignored credentials.
- ground_station/ares/: source providers, later API/inference/recording.
- ground_station/tests/: initial provider checks, later integration tests.
- web/: planned React/TypeScript/Vite app.
- models/ and benchmarks/: planned manifests, labelled sessions and results.
- docs/: plans, source contracts and verification evidence.

FastAPI, the camera worker, BLE receiver/parser, synthetic provider, recorder/export and React source/status controls now exist. Models and labelled calibration datasets remain planned. See [current validation](docs/validation/backend-2026-10-31.md).

## Initial implemented batch and next work

1. Implemented/tested the IR provider and source contract.
2. Implemented FastAPI lifecycle/configuration, one bounded camera worker/cache, health and honest missing-camera states; actual node endpoint remains unavailable.
3. Implemented synthetic IR publication and verified real radar BLE authentication/reporting; no guessed UART driver or default radar simulator.
4. Implemented local source-labelled recordings, JPEG storage, manifests and REPLAY-marked JSONL export.
5. Built and inspected React controls with independent scenario/profile settings and no fake detector score.
6. Next: actual camera capture, frontal detector, real scene/outage tests, eligible calibration and the illustrative avatar. See [integration notes](docs/hardware/radar-integration.md) and [validation](docs/validation/backend-2026-10-31.md).

## Real camera path

- Start with compiled QVGA/RGB565 and software JPEG conversion; measure actual throughput, frame age, corruption, memory and recovery.
- Add boot/usable-PSRAM diagnostics and bounded Wi-Fi retries. Replace the existing indefinite connection loop before relying on unattended operation.
- Use one acquisition owner. Laptop polling of /capture is the initial path; independent onboard scheduling is needed if later running inference on the ESP32.
- Match inference to frame IDs and preserve resize/crop/letterbox coordinate transforms. Draw actual box/centroid semantics.
- Keep node and laptop clocks explicit. Report local durations/receive-to-display delay separately until offsets support capture-to-display measurements.
- Benchmark a frontal detector on actual OV7670 frames and label execution LAPTOP unless verified otherwise. Model selection is pending.
- A future edge gate requires static-buffer export/board comparisons, node-originated outputs, runtime headroom and integrated camera/inference/Wi-Fi tests with laptop inference disabled.

## Synthetic IR component

- File: ground_station/ares/ir_simulator.py; [usage](ground_station/README.md) and [source contract](docs/synthetic-ir-demo.md).
- Scenarios: baseline, warm_target, hot_background and unavailable. Values/noise are illustrative fixtures, not a calibrated heat model or human classifier.
- Fixed metadata: SYNTHETIC source, LAPTOP producer, UNAVAILABLE hardware, false live-fusion eligibility and null hardware timestamp.
- Numeric validity differs from physical availability. Fault fixtures carry null temperatures and valid=false.
- Seed/version/sequence/simulation elapsed time allow reproducibility; backend publication timestamps remain a separate clock domain.
- Generate on the laptop, with no pretend ESP32 IR driver. Scenario selection is independent of person occupancy and operator-selected disaster/visibility profile.
- Checks: deterministic replay, synthetic/exclusion labels, missing-data semantics and invalid/regressing simulation times. API/storage/UI provenance tests follow when those pieces exist.
- Keep IR weight zero in the live person path and exclude synthetic IR from real weight fitting/accuracy. Defer physical human-versus-phone thermal tests until hardware repair.

## External radar gate

- The uploaded product sheet links manuals documenting BLE notifications, write characteristic and authentication. Verify actual device identity/GATT, disconnect the phone app and implement a direct laptop receiver; only one BLE client is documented.
- Verify units, presence semantics, refresh rate, capture/receive timing, access, loss and recovery. Offline CSV is replay data, not automatically a live feed.
- Verify overlap with the camera's marked scene and bystander effects; do not attach broad radar presence independently to every camera person.
- After validation, label records as real external data and preserve true timing. Unknown capture age stays unknown.
- Before integration: EXTERNAL / NOT INTEGRATED, camera-only assessment, multi-sensor fusion unavailable.
- If no usable interface exists, keep a side-by-side external radar demonstration. Manual entry, if later chosen, is explicitly MANUAL and excluded from automatic sensing evaluation.

## Profiles and fusion

- Operator selection applies versioned settings at the laptop executor. Show selected versus acknowledged active profile.
- Fuse only eligible, temporally aligned actual camera/radar observations in a shared zone once the radar gate passes.
- Fit feature/evidence mappings and tune weights/thresholds/persistence on development/validation sessions; freeze before final held-out evaluation.
- Missing/stale inputs do not become no-person evidence or trigger silent renormalisation into full certainty. Show coverage/insufficient evidence and retain separate camera detections.
- Synthetic IR remains ineligible even when its values are valid. Any manual radar inputs remain outside automatic evaluation.
- Compare camera-only, radar-only, equal/global/condition-specific weighting only with real available data. Do not call an uncalibrated weighted score a probability.
- Synthetic records separately check software arithmetic, acknowledgement, persistence, timeout and replay; they do not establish sensing accuracy.

## Validation and delivery

Use [ACTION_PLAN.md](ACTION_PLAN.md) for phases and exit gates. Record detection counts/precision/recall, false-alert exposure, delays, throughput/frame age, unavailable time, provenance, resets and recovery. Linker globals do not establish runtime frame-buffer/model headroom.

Provisional usability targets: at least one fresh image/assessment per second, p95 frame age at most two seconds where measurable, and a predeclared recall/false-alert/delay objective. Higher-rate and 500 ms onboard-processing goals apply only to a built and measured onboard path.

Use a translucent sheet over only the camera for optical degradation; claim no real-smoke validation. Show synthetic thermal scenarios explicitly. Human-versus-phone thermal discrimination is not physically demonstrated while IR is nonworking.

Real camera plus synthetic IR is MIXED. A separate radar window is not automatic fusion, and a rotated avatar is not measured aerial reconstruction. CSI and pose animation follow a stable core.

## Primary references and evidence

- [ESP32 camera driver](https://github.com/espressif/esp32-camera): sensor formats and capture constraints.
- [FOMO](https://docs.edgeimpulse.com/studio/projects/learning-blocks/blocks/object-detection/fomo): possible future custom centroid detector, not deployed here.
- [Espressif pedestrian model](https://github.com/espressif/esp-dl/blob/master/models/pedestrian_detect/README.md): candidate to benchmark, not a completed Arduino integration.
- [Board configuration](docs/hardware/board-config.md) and [compile evidence](docs/validation/camera-build-2026-10-31.md).
