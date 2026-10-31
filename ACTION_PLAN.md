# ARES demo action plan

Updated: 31 October 2026, Asia/Calcutta.

**Current scope:** real ESP32 camera, laptop-generated synthetic IR, and a separate radar app/web system. Radar is not wired to the ESP32. Automatic radar integration depends on identifying a supported data feed.

**Verified:** board/compile checks, 15 backend/protocol tests, React production build, direct radar BLE authentication and real reports, and a browser-operated source-labelled recording. Camera runtime, person detection, calibration, spatial alignment and the complete end-to-end phase gates remain pending. See [backend validation](docs/validation/backend-2026-10-31.md).

Read [PLAN.md](PLAN.md), [TEAM_HANDOFF.md](TEAM_HANDOFF.md) and [the source contract](docs/synthetic-ir-demo.md).

## Source rules

- Camera frames are real or unavailable; no synthetic placeholder silently replaces a failed feed.
- IR hardware is nonworking. Generate IR on the laptop and retain SYNTHETIC/source/version/scenario labels everywhere.
- IR weight is zero in live person assessment. Synthetic IR is excluded from physical sensor/fusion accuracy and weight fitting.
- Radar is EXTERNAL / NOT INTEGRATED until the documented BLE stream is verified on the physical unit. Use direct laptop BLE; no ESP32 UART/GPIO driver or invented radar readings.
- A radar app open beside the dashboard does not establish automatic fusion. Until integration works, person assessment is CAMERA ONLY.
- Operator condition/profile and synthetic temperature scenario are independent controls.
- Laptop inference/fusion and illustrative 3D content carry truthful labels. Onboard inference is a separate future measured gate.

## Tracking

Use NOT STARTED, IN PROGRESS, PASS, PARTIAL or BLOCKED. A reduced demo does not pass an absent physical-sensor/automatic-fusion gate.

| Phase | Deliverable | Status |
|---|---|---|
| 0 | Camera hardware/settings/network verification | IN PROGRESS |
| 1 | Real camera bring-up and synthetic IR provider | IN PROGRESS |
| 2 | FastAPI ingestion, health, recording and minimum viewer | IN PROGRESS — live camera/radar measured (1.22 fps at 0.5 s interval, p95 age bound ≤1.3 s, reboot recovery 10.2 s); Wi-Fi-loss and long-run checks pending |
| 3 | Frontal detector and execution decision | IN PROGRESS — laptop YOLOX-Nano plus on-ESP32 TFLM person classifier (58 ms on device) running side by side; agreement seen live, accuracy not evaluated |
| 4 | External radar adapter and conditional fusion | IN PROGRESS — BLE stream works; provisional fusion implemented and tested; live fusion and scene trials pending |
| 5 | Eligible real-data pilot and profile selection | NOT STARTED |
| 6 | Complete React evidence display and illustrative avatar | IN PROGRESS — light redesign, range-only radar view, ESP32/laptop tiles, disaster conditions and illustrative 3D figure (perspective/overhead) done; calibration-dependent placement pending |
| 7 | Rehearsal, failures and frozen demo | NOT STARTED |

Provider creation alone does not pass phase 1: real camera operation is also required. Backend/frontend work can proceed while radar access is investigated.

## Phase 0 — Verify camera setup

**Wi-Fi prerequisite:** the user confirmed no antenna is attached to the
ESP32-S3-WROOM-1U. Connect a compatible external 2.4 GHz antenna with power off,
then validate the link. Laptop WLAN SSID matches the configured hotspot; this
does not establish the ESP32 connection. See
[Wi-Fi diagnostics](docs/hardware/camera-wifi-troubleshooting.md).

**Actions**

- Preserve original firmware/history; use firmware/ares_node as the working sketch. Record identified board/flash/PSRAM settings and current COM port.
- Confirm camera signal/power wiring and the demo Wi-Fi credentials in the ignored local header. Keep secrets out of logs/Git.
- Keep nonworking IR out of active acquisition. IR repair/pin confirmation and radar UART wiring are not demo prerequisites.
- Documentation is now identified: Seeed SKU 101010001 and HLKRadarTool; linked manuals describe direct BLE reports. Verify actual device/firmware/GATT before implementation claims; [integration notes](docs/hardware/radar-integration.md).

**Validation**

- The baseline build already passed; retain [build evidence](docs/validation/camera-build-2026-10-31.md).
- Verify wiring/power and [board options](docs/hardware/board-config.md) before runtime tests. Recheck COM after reconnecting.
- Record unknowns instead of inventing pin maps or connection states.

**Exit gate and evidence**

- Pass: reproducible camera setup/network configuration and documented external-input limitations.
- Evidence: board/power/pin/settings record and build log. If prerequisites are missing, keep this gate incomplete while independent software work continues.

## Phase 1 — Real camera and synthetic IR

**Antenna update:** with the external antenna fitted, the node joins the hotspot (RSSI -18 dBm), serves `/capture` JPEGs to the laptop and the backend reports the camera READY. Image content is corrupted (magenta speckle, weak green), consistent with the earlier D2-low report; wiring and colour-bar checks are next. See [Wi-Fi diagnostics](docs/hardware/camera-wifi-troubleshooting.md).

**Earlier runtime:** the viewer now reaches Wi-Fi connection and buffer-bit
diagnostics after the SCCB fix. Camera initialisation and a returned buffer are
supported by that code path; valid image content and network delivery remain
unverified. The startup Wi-Fi helper now replaces infinite dots with a scan,
disconnect reasons and a 30-second connection wait; antenna/re-upload checks
remain required.

**SCCB probe result:** user-run reads consistently identify OV7670 PID 0x76 /
VER 0x73 with STOP/START; repeated START fails at 8 and 20 MHz. Runtime PSRAM
reports 8 MB. A project-local viewer fix is prepared; full camera initialisation,
real frames and Wi-Fi still require a new upload and validation. See
[SCCB evidence](docs/validation/camera-sccb-2026-10-31.md).

**Runtime update (31 October):** user-confirmed IDE verification and a successful
firmware boot; camera initialisation fails during SCCB identification at address
0x21 before Wi-Fi starts. No real frame is verified. Follow the
[camera troubleshooting and separate probe](docs/hardware/camera-sccb-troubleshooting.md)
to check control wiring and compare register-read methods before changing drivers.

**Actions**

- Add/verify boot/usable-PSRAM diagnostics, camera errors and bounded Wi-Fi failure/retry reporting. Replace the current endless connect loop before unattended use.
- Upload the configured camera baseline and obtain changing OV7670 images through /capture. Measure dimensions, corruption, orientation, FPS and age.
- Implement standard-library IR scenarios baseline, warm_target, hot_background and unavailable; retain provenance, version/seed/sequence and simulation time.

**Validation**

- Move a target and verify actual pixels change. Inspect image colour/orientation and boot memory diagnostics.
- Run an initial five-minute camera check; record rates, resets and errors. Compilation alone cannot pass this gate.
- Check synthetic replay determinism, fixed source/hardware/exclusion flags, null faults and rejection of invalid/regressing simulation times.
- Verify generation does not require IR hardware or derive its scenario from a fire profile/person occupancy.

**Exit gate and evidence**

- Pass for reduced scope: actual frames and a tested, clearly synthetic provider. No physical IR gate is claimed.
- Evidence: real frames, boot/rate logs, provider check output and labelled fixtures.
- If camera fails, mark unavailable; continue software work without fake live frames. Repaired IR requires its own later real-sensor validation.

## Phase 2 — FastAPI, recording and minimum viewer

**Actions**

- Add FastAPI configuration for the ESP32 URL, one acquisition worker and bounded latest-frame storage.
- Publish synthetic IR with actual backend publication/receive times, keeping simulation elapsed time separate.
- Publish camera disconnected/stale and radar NOT INTEGRATED states. Add recordings/replay with per-input metadata.
- Add the minimum React live preview/evidence/status view before decorative 3D.

**Validation**

- Missing configuration/network means unavailable; no silent camera/radar simulation.
- Multiple clients must not duplicate camera acquisition or create increasing lag.
- Verify MIXED and per-input source labels survive API/storage/replay/UI. A valid synthetic number cannot make physical IR healthy.
- Test Wi-Fi loss/recovery, stale records and matching frame IDs. Keep unknown clock offsets explicit.

**Exit gate and evidence**

- Pass: actual preview, synthetic IR and honest external-input status display/record correctly with tested recovery.
- Evidence: mixed-source session manifest, UI states, rates and recovery log. Partial progress is not a full live-sensing claim.

## Phase 3 — Frontal detector

**Actions**

- Select/benchmark a frontal detector on actual OV7670 frames. Record licence/version, input/preprocessing and actual execution location.
- Start with a laptop baseline. Attempt onboard deployment only with static-buffer comparison and subsequent integrated measurement.
- Preserve coordinate transforms and the model's actual box/centroid semantics.

**Validation**

- Test empty scenes, moving/stationary people, varied clothing, occlusion and nonhuman objects on sessions separate from fitting data.
- Measure counts, recall/precision, alert delay and throughput; match results to displayed frame IDs.
- An ESP32 claim requires node-originated predictions/timings with laptop inference disabled. Otherwise label LAPTOP.

**Exit gate and evidence**

- Pass: real-frame detection in the declared scene with measured limitations and correct execution labels.
- Evidence: model/preprocessing manifest, labelled examples and timing/results. If no detector works adequately, leave detection incomplete; graphics cannot substitute for it.

## Phase 4 — External radar and conditional fusion

**Actions**

- Build against the documented BLE characteristics and framed reports, verifying the actual GATT profile and authentication first. Disconnect the phone app: the manual allows one BLE client at a time.
- Verify fields/units, refresh rate, capture/receive timing, access and loss/recovery. Offline exports are replay data, not automatically live.
- Test overlap with the camera's marked scene and bystander effects.
- If a usable live feed exists, implement a real external adapter and laptop camera/radar fusion with versioned operator profiles/acknowledgement.
- Synthetic IR stays ineligible. Any later manual input is MANUAL and excluded from automatic evaluation.

**Validation**

- Compare received records against the radar app during empty, walking/stationary and departure trials; test disconnect/stale/recovery.
- Profiles change weights, not raw observations. Check arithmetic, persistence, coverage, disagreement, invalid settings and all-input failure using separate deterministic fixtures.
- Missing radar cannot become no-person evidence or silent fully covered single-input fusion. Show camera evidence separately.

**Exit gate and evidence**

- Automatic-fusion pass requires verified real radar data, aligned observations and tested source/fusion rules.
- Evidence: interface notes, sample records, scene/timing and logic/fault results.
- If no usable feed exists, deliver camera-only assessment plus synthetic thermal context beside the separate radar app. Automatic integration remains pending; invented radar readings cannot pass the gate.

## Phase 5 — Eligible pilot and weight selection

**Actions**

- Define presence in a common marked zone with independent ground truth. Predeclare metric units, recall/false-alert/delay objectives and missing-input policy.
- Collect clear/degraded camera trials: empty, moving/stationary people and nonhuman objects. Use a translucent sheet over only the camera; an opaque cover is an unavailable-vision test.
- Collect synchronised radar only after its real adapter works. Otherwise evaluate camera only and defer automatic fusion calibration.
- Split complete fitting/validation/final sessions, preferably people/backgrounds too. Never split adjacent video frames randomly across sets.
- Fit evidence mappings on fitting data, tune nonnegative camera/radar weights and decision/persistence thresholds on validation data, then freeze before untouched tests.

**Validation**

- Compare only actually available real-source baselines: camera, radar, equal weights, global and condition-specific sets.
- Exclude synthetic IR, simulation and manual input from physical accuracy/weight fitting. Record software fixture checks separately.
- Report TP/FP/FN, precision/recall, unoccupied exposure/false alerts, delay, participants/sessions and unavailable time by condition.
- Physical human-versus-phone thermal comparison is deferred. Synthetic chart values cannot establish human thermal discrimination or sensor benefit.

**Exit gate and evidence**

- Calibration pass requires reproducible eligible data, frozen settings and held-out results; meeting targets is a separate reported outcome.
- Evidence: recordings/labels/splits, versions, objective, baseline table and limits. Retuning after final results requires new final-test data.
- Insufficient data means provisional settings. Short trials with no false alerts cannot establish a long-term zero false-alert rate.

## Phase 6 — Evidence dashboard and avatar

**Actions**

- Complete React source/age/health, selected/active profile, camera-only/fusion state, synthetic temperature chart and recording controls.
- Add independent synthetic-scenario control and persistent SYNTHETIC plus IR hardware unavailable badges.
- Add a generic Three.js avatar/overhead toggle. Optional pose animation reports its actual execution location.
- Keep positions schematic until fixed-camera floor calibration/visible foot estimates are tested.

**Validation**

- No global LIVE badge disguises IR simulation; no separate radar app implies an integrated score.
- Selecting fire must not automatically manufacture temperature evidence.
- Lost vision fades/freezes the avatar with last-seen status; broad radar cannot confirm a newly precise pose/location.
- Test replay labels, missing inputs and unknown ages. If floor mapping is used, measure error at held-out points.

**Exit gate and evidence**

- Pass: UI reflects actual sources/uncertainty and illustrative content is clear.
- Evidence: mixed/replay/fault screen recordings and any calibration report. Drop unstable pose animation before weakening source labels or acquisition.

## Phase 7 — Rehearse and freeze

**Actions**

- Rehearse entry/stationary/departure, optical degradation, operator profiles, labelled synthetic thermal scenarios, camera obstruction and recovery.
- Include integrated radar only if phase 4 passed; otherwise show its app separately and state the limitation.
- Exercise Wi-Fi outage, stale input, restart and replay. Run a measured concurrent stability period; aim for the earlier one-hour goal if feasible and report actual duration.
- Save versions, launch instructions, known issues, a working build and clearly labelled recorded backup.

**Validation**

- Complete two rehearsals without unexplained resets, accumulating lag or synthetic/manual data represented as actual automatic evidence.
- Check actual rates/ages and recovery against declared targets; missing input never means all-clear or fabricated position.
- Verify restart mode/configuration. Later changes repeat affected checks; model/weight changes need new evaluation.

**Exit gate and evidence**

- Pass: the explicitly reduced demo is repeatable and meets declared requirements. Missing real IR/automatic radar remains documented, not silently passed.
- Evidence: rehearsal/duration/fault/metrics logs, frozen manifest and recovery instructions. Remove optional pose/CSI if they destabilise the core.

## Edge-processing benefits (E1–E4)

Added 31 October 2026. Each item must produce a measured before/after result. Claim only what is measured.
Radar reaches the laptop directly, so radar processing is ground-station processing, not on-node processing.

| Item | Deliverable | Status |
|---|---|---|
| E1 | Event-triggered sending + privacy mode | NOT STARTED |
| E2 | Radar outlier filtering, smoothing and debounce | NOT STARTED |
| E3 | ESP32 vs laptop detection latency | IN PROGRESS — first figures: ESP32 58 ms inference + ~24 ms prep; laptop YOLOX ~20-44 ms; structured comparison pending |
| E4 | Offline event buffering on the node | NOT STARTED |

**E1 — Event-triggered sending and privacy mode** (firmware, backend, UI)
- The node sends small heartbeats (person score, sequence, health) by default. It sends the JPEG when the on-node score or a motion check fires, or when the operator requests one. Adaptive rate: idle vs active fps.
- Privacy mode: no image leaves the node unless triggered or requested; the dashboard shows when images are withheld.
- Measure: bytes per minute for always-send vs edge-filtered in empty and occupied scenes; % of time with no image sent; any missed person events caused by filtering.

**E2 — Radar anomaly isolation** (backend)
- Reject physically impossible jumps (Hampel/median filter), smooth distance (moving median or Kalman), learn an empty-room energy baseline, and require N consecutive presence reports before an alert. Forward only state changes and significant moves.
- Keep raw reports recorded alongside filtered ones; filtering must not hide disconnects or staleness.
- Measure against tape-measure ground truth: distance error and variance before vs after; % of readings flagged; false alerts per hour before vs after; added alert delay; % of reports suppressed.

**E3 — Edge latency** (firmware, backend)
- Timestamp each stage per frame: capture, on-node inference, JPEG, network, laptop YOLOX, dashboard display. Unsynchronised clocks: use node uptime on the node side and backend receive time on the laptop side, and report them separately.
- Measure: median/p95 of time from person appearing to ESP32 flag vs laptop result; on-node inference time; ESP32/laptop agreement rate on matching frames.

**E4 — Offline buffering** (firmware, backend)
- During Wi-Fi loss the node keeps detecting and stores events (node uptime, sequence, score) in a bounded PSRAM ring buffer, then uploads them on reconnect. Uploaded events are labelled BUFFERED with their original node time.
- Measure: events kept vs lost during timed outages; buffer capacity in minutes; upload time after reconnect.

Gates: E1–E4 results need valid camera frames (fix D2/D4 wiring first) except E2, which can start with the radar now. Synthetic IR is excluded from all E-item metrics.

## Targets and records

Provisional usability goals, not measured capabilities or disaster-response requirements: at least one fresh frame/assessment per second, p95 capture age at most two seconds where measurable, and a predeclared recall/false-alert/delay objective before tuning. With unsynchronised clocks, report receive-to-display separately. Higher-rate/onboard timing goals apply only if built and measured.

Record status, tester/date, hardware/software/source configuration, checks, measured results, evidence, failures, fallback and remaining work per phase. NOT RUN differs from PASS. Keep physical, synthetic, manual and replay evaluation separate.

## Immediate coding sequence

- [x] Identify board, install CLI and compile camera baseline.
- [x] Validate the standalone synthetic IR provider: four checks passed; [evidence](docs/validation/synthetic-ir-2026-10-31.md).
- [x] Add FastAPI configuration, camera worker/cache, synthetic IR publication and health/status; software checks passed.
- [x] Add recording/provenance and minimum React view; actual radar/IR session export verified.
- [ ] Validate the actual camera runtime/feed when its address and network configuration are available.
- [x] Identify the radar documentation and candidate BLE interface; [findings](docs/hardware/radar-integration.md).
- [x] Implement BLE authentication/report parsing and verify an actual stream (58-report probe, then dashboard streaming).
- [ ] Run labelled radar/scene alignment and physical disconnect/reconnect checks before automatic fusion.
- [x] Integrate a laptop detector (YOLOX-Nano, Apache-2.0) with frame-matched, camera-only labelled results; [evidence](docs/validation/detector-2026-10-31.md).
- [x] Add node `/health`, `/colorbar`, mDNS and frame headers (`ares-node-0.2`, uploaded and verified).
- [ ] Verify a positive detection, fix camera D2/D4 wiring and measure detection on real OV7670 frames.
- [x] Implement provisional camera/radar fusion with coverage, persistence and disagreement; [evidence](docs/validation/fusion-2026-10-31.md).
- [x] Run live fusion with the real radar (camera + radar, both profiles); [evidence](docs/validation/fusion-2026-10-31.md).
- [x] Measure the live pipeline (rate, age, single-owner acquisition, node reboot recovery); [evidence](docs/validation/pipeline-2026-10-31.md).
- [ ] Secure the intermittent camera D2 wire.
- [x] Add on-ESP32 person inference alongside each image (`ares-node-0.3`, TFLM person_detect) and show ESP32 vs LAPTOP; [evidence](docs/validation/edge-and-scene-2026-10-31.md).
- [x] Add literature-informed disaster conditions (IR prior applied as 0 while synthetic) and the illustrative 3D scene; [evidence](docs/validation/edge-and-scene-2026-10-31.md).
- [ ] Collect eligible data and evaluate both detectors on OV7670 frames.

IR repair and radar GPIO wiring are not immediate prerequisites. CSI remains optional after a stable core and a separate labelled experiment.
