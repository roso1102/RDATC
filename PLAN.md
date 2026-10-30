# ARES demonstration plan

Updated: 31 October 2026 (Asia/Calcutta).

Execution checklist and validation gates: [ACTION_PLAN.md](ACTION_PLAN.md).

Team entry point and decision history: [TEAM_HANDOFF.md](TEAM_HANDOFF.md).

## Confirmed demonstration scope

- One ESP32-S3 sensing node. For the imminent interactive demo, the camera faces people from the front; overhead aerial operation remains the intended later use and needs separate validation.
- One laptop ground station. The laptop performs the software tasks previously assigned to a Raspberry Pi; Raspberry Pi integration is deferred.
- Active sensors: OV7670 camera, MLX90614 IR temperature sensor, and LD2410 presence radar. Exact sensor variants and IR/radar GPIOs still need confirmation from the actual connected hardware.
- LoRa/SX1262 is excluded from this demo despite its inclusion in the supplied circuit drawing. Use the ESP32 Wi-Fi antenna for communication; it is not an extra independent human-presence sensor.
- NEO-6M GPS is excluded from the current demonstration following the updated hardware list. Use a clearly labelled configured test-scene position if a location is needed.
- Connected chip/memory identified over USB: ESP32-S3, 8 MB flash and 8 MB embedded PSRAM; user reports ESP32-S3-WROOM-1U. Selected build settings are recorded in [docs/hardware/board-config.md](docs/hardware/board-config.md). Sensor breakouts, power budget and physical demo arrangement still need confirmation; usable PSRAM and images require runtime tests.
- User confirmed Wi-Fi between ESP32-S3 and laptop for frames, with USB for programming/debugging.
- Future multiple-node networking is outside the first demonstration.

## Current implementation evidence

- Original firmware source: RDATC branch `rounak-vyas`, inspected commit `e2e770a8ebfbef6a6824544be477ca15c3299e1c`, under `ARES_Firmware/OV7670/`. Current working firmware is under `firmware/ares_node/`.
- Its `Frame_Capture_2_FPS` sketch configures OV7670 RGB565 at 320x240 and serves software-converted JPEGs through `/capture`. The sketch name is not a measured frame-rate result.
- Reference camera GPIOs: SIOD=4, SIOC=5, XCLK=15, VSYNC=6, HREF=7, PCLK=13; D0..D7=8,9,10,11,12,18,17,16. These are code definitions, not proof of physical wiring.
- No current MLX90614 or LD2410 acquisition code/pin definitions were found in that checkout. Its older simulated application is not the current implementation.
- No ARES ground-station application, custom trained model, or measured integrated performance has been established in this workspace. Board flashing and actual live camera/sensor operation remain unverified here.
- Camera baseline compile passed with the USB-identified 8 MB flash / 8 MB PSRAM configuration; the working copy now zero-initialises its camera configuration. No application upload or live camera validation has occurred. See [compile validation](docs/validation/camera-build-2026-10-31.md).

## Immediate demo milestones, in order

1. **Verify the connected hardware.** Confirm Arduino board/core settings, PSRAM configuration, COM port, camera stream address/status, IR SDA/SCL, radar TX/RX, module variants, and actual power connections. Preserve the existing reference sketch.
2. **Establish real acquisition.** Obtain repeatable camera frames plus independent timestamped IR and radar readings. Add timeouts and explicit invalid/stale flags before integration. Exit criterion: frames and both sensor readings update without synthetic substitution or unexplained resets.
3. **Create the minimum live viewer.** Python FastAPI backend plus React/TypeScript/Vite frontend: real preview, evidence panels, timestamps, profile selector, connection status, and recording. Use one camera acquisition owner and bounded latest-frame caching.
4. **Integrate frontal person detection.** First benchmark a suitable model on real OV7670 frames; verify actual inference location. ESP32 inference remains a target, not an achieved capability. If an on-board model cannot be integrated in time, a laptop-inference fallback must be explicitly labelled and its edge-inference work marked pending. Record any temporary departure from the planned on-board fusion path.
5. **Collect a small labelled pilot and select weights.** Record clear and physically degraded visibility, people moving/stationary, empty scenes, idle/warm phone, and warm nonhuman objects. Separate development and final test recording sessions. Fit evidence mappings on development data, tune weights and thresholds on validation sessions, freeze, and report results on untouched trials.
6. **Add the explanatory scene.** Render a generic avatar and overhead/perspective toggle. Pose-driven animation is an optional enhancement after detection is stable. Only map avatar floor position after calibration; otherwise show a schematic zone. Fade or mark the avatar last-seen when visual tracking is lost.
7. **Rehearse and freeze.** Exercise profile changes, degraded/blocked camera, no-human warm-object cases, Wi-Fi loss, stale sensor data, and recovery. Keep a clearly labelled recorded replay as backup, separate from live operation. The existing one-hour integrated stability target remains desirable if time permits; report the actual duration tested.

Must-have demo: live camera, actual radar and temperature readings, frontal person detection with truthful execution labels, operator-selected profiles, explainable evidence contributions, and unavailable/stale states. A basic avatar follows these milestones; pose animation and CSI must not block them.

## Decision: operator-selected disaster profiles

This decision supersedes the earlier proposal to infer the disaster type automatically.

1. The operator explicitly selects a disaster profile.
2. The selected profile loads a predefined set of sensor weights for human-presence assessment.
3. The system does not infer or automatically change the selected disaster profile.
4. Weights for valid observations remain those of the selected profile. Further automatic environmental reweighting is deferred unless explicitly agreed later.
5. Missing, invalid, or stale observations are excluded. Reduced evidence coverage must be reported; no usable evidence produces an insufficient-evidence result.
6. Selecting a profile does not itself establish that any sensor can detect people under those conditions.

Initial implementation will accept profile selection over USB serial. Later, the ground-station web interface can send an acknowledged profile-selection command to the node. The dashboard and telemetry should report the profile actually active on the node, with a configuration version.

Profile names and numerical weights have not been finalised. Start evaluation with clear visibility and reduced visibility; hot-background context is a separate condition. Fire with a clear view and fire with smoke must not be assumed to have identical camera reliability. Earlier 70/30 and 20/80 examples are illustrative only, not validated defaults.

Human-presence weighting and environmental-hazard assessment are separate: a temperature observation can be useful for a heat-hazard assessment even when its human-presence weight is low.

Proposed initial allocation: camera locates visible person candidates; radar corroborates zone presence; MLX90614 provides thermal context. Keep IR human-presence weight zero until held-out comparison establishes a repeatable benefit. Allow zero weights during optimisation. A warm phone or mug is a negative test case, not a guaranteed thermal contrast demonstration.

Select nonnegative weights summing to one and decision/persistence thresholds using labelled development/validation trials. Predeclare a recall/false-alert/delay objective. Compare camera-only, radar-only, equal weights, one global set, condition-specific sets, and with/without IR or optional Wi-Fi sensing. Freeze settings before final testing. Report per-condition recall, precision, false alerts with observation duration, delay, trial/participant counts, and limitations. Do not split adjacent video frames randomly across development and test sets or call a weighted index a calibrated probability.

## Optional Wi-Fi sensing experiment

- RSSI can initially be logged for communication health and an experimental signal-variation trace; it has no established human-presence weight.
- CSI acquisition is supported by ESP32-S3 but needs explicit configuration, received traffic, processing, and concurrency testing with the camera. It is an optional experiment after the core demo works.
- Keep transmitter/router/phone hotspot and receiver fixed. If a phone is the transmitter, do not move it as the test reflector in the same trial.
- Compare empty scenes, walking and stationary people, nonhuman movement, and changed traffic/background conditions. A channel disturbance alone is not a human classification.
- Add Wi-Fi features to fusion only after separate held-out comparisons show a benefit. Avoid treating RSSI and CSI from the same link as independent votes.

## Firmware and synthetic testing

- Synthetic testing is a supporting verification path; immediate hardware bring-up now takes priority. USB-only synthetic tests do not require sensor drivers or radio links.
- Use interchangeable simulated and hardware input providers with a common observation structure.
- Simulate camera detection scores and image quality, radar results, temperatures, timestamps, and sensor health. Do not generate a synthetic GPS fix as though GPS were installed.
- Explicitly label synthetic observations and mock AI outputs.
- Test operator profile selection, correct weight loading, profile changes, missing/stale data, conflicting evidence, and all-input failure.
- Stream structured observations, active profile, weights, evidence coverage, and assessment results over serial.
- Synthetic tests validate firmware behaviour and configuration logic; they do not validate real sensing or AI accuracy.

## Processing and AI

- ESP32-S3: acquisition, timestamps, validity checks, lightweight processing, application of the operator-selected profile, preliminary weighted fusion, and telemetry. A small quantised person-detection model is a target subject to hardware, memory, speed, and accuracy benchmarking.
- Laptop: communication receiver, storage, observation history and disagreement/staleness monitoring, heavier image analysis, calibrated scene mapping, candidate routes, and web backend. The browser renders the 3D display.
- Primary lightweight fusion runs on the ESP32-S3 as specified in the latest processing discussion. The laptop retains the supporting observations for history, evaluation, and explanation; repeated or reprocessed observations are not independent sensor evidence.
- Predefined weights and thresholds are rule-based processing. They must not be described as a trained AI model.
- A concrete candidate edge pipeline and benchmark plan are documented in [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md). The model remains a candidate until compiled and measured on the user's actual board.

## Mapping and interface

- Show a terrain or measured demonstration model with live observation overlays, uncertainty, active profile, weights, sensor health, and observation age.
- Use satellite/elevation data as background context, with source dates and resolution visible.
- Use a calibrated local grid for candidate openings and unobstructed approaches; retain unknown areas.
- Detailed, accurate wreckage reconstruction requires additional geometric information beyond one stationary monocular view.
- For the frontal demo, the 3D avatar/overhead toggle is an illustrative or estimated scene, not a measured overhead image or validated aerial detection. Rendered views do not replace real overhead training/test data. Pose and person detection share the camera and are not independent sensing inputs.
- With no GPS in the current demo, any geographic position is configured/surveyed context rather than a live node GPS measurement. Local mapping still requires camera calibration and known scene geometry.

## Reliability

- Use timeouts, watchdog recovery, sequence numbers, bounded retries, and explicit stale-data handling.
- Test stable power under simultaneous capture, inference, and radio transmission.
- Test sensor disconnection, communication outages, restart recovery, and sustained operation.
- Missing observations must never be presented as proof of no person or a clear route.

## Conference shortlist recovered from earlier discussion

Source: the chat titled "Review project idea and prototype", discussion dated 17 October 2026. These were suggested venues; no confirmed submission or registration decision was found.

- IEEE CONECCT 2027: previously recommended paper target. https://ieee-conecct.org/
- COMSNETS 2027: previously recommended demo/poster candidate. https://www.comsnets.org/demos_exhibits and https://comsnets.org/poster_session
- ICNEWS 2027: embedded systems, edge computing, and experimental prototype candidate. https://icnews.ece.bmsce.in/
- IEEE RadarConf 2027: conditional candidate only for a substantial radar-focused contribution. https://ieee-aess.org/event/conference/2027-ieee-radar-conference

Official pages were checked on 30 October 2026. Submission deadlines and track publication details must be checked for the intended submission; do not carry forward the older discussion's deadlines without verification.

Fresh venue research and proposed paper directions are recorded in [CONFERENCE_RESEARCH_2026-10-30.md](CONFERENCE_RESEARCH_2026-10-30.md). This expands the earlier shortlist with ICEMCSI and ICATIECE, distinguishes imminent demo/poster calls from full-paper calls, and records unresolved publication/date details. Recommendations are not submission commitments.
