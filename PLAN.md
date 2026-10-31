# ARES demonstration plan

Updated: 31 October 2026, Asia/Calcutta.

Execution gates: [ACTION_PLAN.md](ACTION_PLAN.md). Team context: [TEAM_HANDOFF.md](TEAM_HANDOFF.md). Source contract: [synthetic IR and external radar](docs/synthetic-ir-demo.md).

## Current decisions

- One ESP32-S3 camera node and one laptop. The interactive demo uses a frontal camera; overhead deployment/validation are later work.
- USB identification confirmed 8 MB flash and 8 MB embedded PSRAM on COM3. The camera baseline compiles; usable PSRAM, frames and Wi-Fi runtime remain unverified here.
- OV7670 frames are the real onboard input. Wi-Fi transports images and USB supports programming/debugging.
- **IR hardware is reported nonworking.** Use a laptop-side synthetic IR provider, explicitly labelled SYNTHETIC. IR repair/pin confirmation is not a demo prerequisite.
- **Radar is separate and not connected to the ESP32.** Its linked manufacturer manuals document direct Bluetooth reports. Use a BLE-first laptop receiver, pending actual-device/GATT/stream validation; no ESP32 radar GPIO work is planned. See [radar integration](docs/hardware/radar-integration.md).
- FastAPI plus a React/TypeScript/Vite dashboard are implemented and running locally. Direct radar BLE authentication/reporting and source-labelled recording/export were verified. Three.js/pose, person detection and calibrated fusion remain pending.
- No LoRa, GPS, Raspberry Pi or multi-node networking in this demo. Positions remain schematic until calibrated.
- Operator selects a condition/profile. The system does not infer or silently change disaster type.

## Revised processing path

1. ESP32 captures real camera frames. One laptop acquisition worker maintains a bounded latest-frame cache.
2. Laptop generates independent, seeded synthetic IR records. Valid numeric fixtures do not mean the physical sensor works.
3. The laptop will authenticate/subscribe directly to the documented radar BLE interface. Disconnect the phone app first because the manual allows one BLE client. Radar stays EXTERNAL / NOT INTEGRATED until actual streaming is verified; no invented readings fill this gap.
4. Frontal person detection uses real images and reports its actual execution location. A laptop baseline can establish the interactive pipeline; onboard inference is a future measured milestone.
5. Current external-data fusion is planned on the laptop. Returning radar/IR inputs to the ESP32 for onboard fusion is a separate deferred extension.
6. The radar adapter now works, but person detection/fused assessment remain unimplemented. Show sources separately and no person score. Do not silently renormalise a missing input into fully covered fusion.
7. React shows frames, per-input source/age/health, profiles and synthetic thermal context. The avatar and overhead toggle are illustrative; pose animation follows the stable live path.

## Synthetic IR and provenance

- Provider: ground_station/ares/ir_simulator.py. API/UI transport, scenario controls and recorded provenance now work; the physical sensor remains unavailable.
- Scenarios: baseline, warm_target, hot_background and unavailable. Seed/version/sequence/simulation elapsed time allow repeatable fixtures.
- Every record has source=SYNTHETIC, producer=LAPTOP, hardware_status=UNAVAILABLE and eligible_for_live_fusion=false. No physical sample timestamp is invented.
- Label real-camera-plus-synthetic-IR sessions MIXED and preserve per-input labels in transport, recordings, replay and display.
- Scenario selection is separate from disaster-profile selection and actual occupancy. Selecting fire must not manufacture corroborating temperature evidence.
- IR weight stays zero in the live person assessment. Synthetic values exercise displays/transport and separately labelled software logic, not real sensor accuracy or thermal benefit.
- Physical human-versus-phone/mug thermal comparison is deferred. Nonhuman-object trials remain useful for real connected sources, without claiming synthetic temperatures came from those objects.

## Evidence-based profiles

- Earlier 70/30 and 20/80 values were illustrative, not validated settings.
- Operator selection loads a frozen versioned configuration at the actual executor, currently the laptop. Display selected versus acknowledged active profile.
- Define presence in a common marked scene/zone. Keep camera locations separate from broad external radar presence.
- Fit comparable evidence mappings using labelled development data. Raw Celsius, dBm and radar energy are not averaged with model scores.
- With a verified real radar adapter, tune nonnegative camera/radar weights and thresholds on validation sessions under a predeclared recall/false-alert/delay objective.
- Compare actual eligible inputs: camera-only, radar-only, equal weights, global weights and condition-specific sets. Freeze before untouched test sessions; never randomly split adjacent frames across sets.
- No radar feed means automatic fusion calibration remains pending. Manual input, if explicitly chosen later, is labelled MANUAL and excluded from automatic sensor-performance claims.
- Synthetic IR is excluded from physical weight fitting/accuracy. Revisit IR only after repair and real-data evaluation.
- Missing/stale evidence means reduced coverage/unavailable, never an all-clear or fabricated location. A weighted index is not automatically a calibrated probability.

## Current execution order

1. Completed initial slice: project .venv, FastAPI, bounded camera worker, synthetic IR, direct radar BLE, React controls and local recording/export. Software and brief physical radar checks are recorded below.
2. Obtain the actual camera endpoint and verify Wi-Fi/boot/PSRAM/real capture. Keep unavailable status until that passes; add bounded node connection failure reporting before unattended use.
3. Select/benchmark and integrate frontal person detection on actual OV7670 images, with honest execution labels.
4. Run real radar empty/moving/stationary/scene-alignment and outage/reconnect trials. Add fusion only after its source/scene requirements pass.
5. Collect eligible labelled trials, select/freeze profiles and compare held-out baselines. Current 70/30 and 20/80 configuration examples remain provisional and produce no automatic person score.
6. Add the illustrative avatar and optional pose animation; then longer combined stability/rehearsal checks. CSI remains optional.

## Evidence and pending work

- Original firmware source: RDATC rounak-vyas at e2e770a8ebfbef6a6824544be477ca15c3299e1c. Working sketch: firmware/ares_node/ares_node.ino.
- Camera definitions: SIOD=4, SIOC=5, XCLK=15, VSYNC=6, HREF=7, PCLK=13; D0..D7=8,9,10,11,12,18,17,16. These are definitions, not physical wiring proof.
- Baseline uses 320x240 RGB565 and software JPEGs through /capture. The older 2_FPS sketch name is not a measured rate.
- Configuration was zero-initialised and credentials moved into an ignored header. Compilation passed; application upload/live capture has not been validated during this work.
- Arduino CLI 1.5.1 and existing ESP32 core 3.3.7 are available. See [board settings](docs/hardware/board-config.md) and [build evidence](docs/validation/camera-build-2026-10-31.md).
- Backend, React viewer, synthetic IR, radar receiver and recording/export now exist. A short probe decoded 58 actual radar reports; browser recording preserved 885 radar reports plus 88 telemetry records. See [backend validation](docs/validation/backend-2026-10-31.md). Camera runtime, detector, calibrated profiles and 3D remain pending.
- CSI/RSSI is optional after the core works; a varying channel is not established human detection. Pose and person detection share one camera and are not independent sensing votes.
- Satellite context, wreckage reconstruction, safe-route claims and overhead detection validation remain deferred. Rendered overhead avatars do not replace real overhead data.

## Conference context

Earlier venue research remains in [CONFERENCE_RESEARCH_2026-10-30.md](CONFERENCE_RESEARCH_2026-10-30.md). Those dated recommendations are not submission commitments; verify current calls separately before submission.
