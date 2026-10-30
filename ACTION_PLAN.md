# ARES demo action plan

Updated: 31 October 2026, Asia/Calcutta.

**Purpose:** deliver an interactive frontal-view demonstration with real camera frames, actual sensor readings, explainable profile-based fusion, and an illustrative 3D view. Validate each phase before relying on it in the next.

**Status:** initial tooling and hardware identification have started; no complete phase gate is passed yet. Arduino CLI 1.5.1 runs, and an esptool query on COM3 confirmed ESP32-S3 with 8 MB flash and 8 MB embedded PSRAM. Camera/sensor runtime operation, the application and model execution remain unverified here. See [docs/hardware/board-config.md](docs/hardware/board-config.md) for the selected build configuration.

Phase 0 build check: camera working sketch compiled successfully, including the camera-configuration initialisation fix. Evidence: [camera build validation](docs/validation/camera-build-2026-10-31.md). Remaining phase 0 requirements include actual IR/radar pin/power verification and the complete reproducible setup record.

## Scope and priorities

- Hardware: one ESP32-S3, OV7670, MLX90614 and LD2410; laptop ground station.
- Communication: local Wi-Fi for images/data; USB for programming and debugging. No LoRa, GPS or Raspberry Pi in this demo.
- Software: Python FastAPI backend and React + TypeScript + Vite frontend. Three.js for the illustrative scene; no Streamlit.
- Operator selects the condition. The system does not infer or silently switch disaster profiles.
- Camera supplies visual person evidence; radar supplies zone-presence evidence; IR initially supplies thermal context. IR human-presence weight starts at zero until experiments justify a contribution.
- ESP32 inference and fusion are the target. A deadline fallback may run inference/fusion on the laptop, with explicit execution labels and onboard work marked pending.
- Must-have: real acquisition, frontal person detection, live evidence, profile switching, experimental weight methodology, stale/fault states and a rehearsed demonstration.
- Presentation milestone: generic avatar and overhead/perspective toggle. Pose-driven animation is optional after the core pipeline works.
- Optional research: RSSI trace and CSI sensing. Neither blocks the core demo or starts with an assumed human-presence weight.
- Deferred: validated overhead detection, aerial mapping, reconstructed wreckage, safe-route claims, multi-node networking and disaster-field validation.

## Phase order and tracking

Use `NOT STARTED`, `IN PROGRESS`, `PASS`, `PARTIAL` or `BLOCKED`. A fallback does not turn the original gate into a pass; record the reduced scope separately.

| Phase | Deliverable | Initial status |
|---|---|---|
| 0 | Verified hardware and reproducible starting sketch | IN PROGRESS |
| 1 | Real camera, IR and radar acquisition | NOT STARTED |
| 2 | Laptop ingestion, recording and minimum live viewer | NOT STARTED |
| 3 | Frontal person detector and execution decision | NOT STARTED |
| 4 | Profile/fusion logic and fault handling | NOT STARTED |
| 5 | Labelled pilot, selected weights and held-out results | NOT STARTED |
| 6 | Complete React dashboard and illustrative 3D scene | NOT STARTED |
| 7 | Integrated rehearsal, stability check and frozen build | NOT STARTED |

Phases 1–5 define the critical path. The minimum viewer is built in phase 2 and extended in phase 6. Optional visual work can proceed once its data contract is stable, without bypassing the sensing gates.

## Phase 0 — Verify the connected hardware

### Actions

- Preserve the original `ARES_Firmware/` sketches/history as the inspected reference; use `firmware/ares_node/` as the current working copy.
- Record exact ESP32-S3 board/module marking, Arduino board/core version, flash/PSRAM settings and COM port.
- Confirm physical camera wiring against the existing sketch; record IR SDA/SCL, radar TX/RX, supply connections and common ground. Check module supply and logic-level compatibility before changing connections.
- Record full MLX90614 suffix and LD2410 variant. Do not infer optical FOV or UART protocol solely from a generic module name.
- Record current camera IP/endpoint, power source and any already-working sketch/output. Keep Wi-Fi credentials out of shared logs.

### Validation

- Build the preserved starting sketch with the recorded settings; save the build output.
- Check boot diagnostics, camera initialisation and reported PSRAM availability. A successful build is not a successful hardware test.
- Check the pin table for conflicts and compare it with actual connections; do not invent missing IR/radar GPIOs.

### Exit gate and evidence

- **Pass:** reproducible baseline build, verified connection table and required module/settings information recorded.
- **Evidence:** hardware manifest, pin table, baseline build log and serial boot log.
- **If blocked:** resolve the specific missing pin, power or board setting before integrating that device. Independent laptop scaffolding can continue.

## Phase 1 — Acquire real camera and sensor data

### Actions

- Start from the reference OV7670 QVGA/RGB565 path and software JPEG preview. Measure actual throughput; the sketch's `2_FPS` name is not a measurement.
- Add MLX90614 object and sensor-temperature reads with error checks. Sensor temperature is not remote background temperature.
- Parse the correct radar UART protocol; expose presence/moving/stationary status and distance fields only when supported by the actual module.
- Attach monotonic timestamps, sequence IDs, validity and timeout flags. Keep acquisition schedules bounded and independent of an open browser.

### Validation

- Camera: move a hand/object in view and confirm the returned image changes; inspect colour, corruption, orientation and measured dimensions.
- IR: record an empty-scene baseline, then a nearer target and a warm object. Log repeatability and geometry; plausible numbers alone do not establish temperature accuracy or human classification.
- Radar: test an empty zone, walking person, stationary person and departure. Establish the actual useful zone and account for bystanders.
- Run all three together for an initial five-minute check. Record timeouts, resets, frame rate and update intervals.
- Inject a read timeout for each sensor and confirm it becomes invalid/stale rather than retaining an apparently fresh value. Perform physical wiring changes with power removed.

### Exit gate and evidence

- **Pass:** real images and actual readings from all three devices update with valid timestamps, and errors are explicit. No unexplained resets during the initial check.
- **Evidence:** sample frames, raw sensor log, measured update rates and observed coverage/limitations.
- **If blocked:** retain working inputs, mark the failed input unavailable and record a partial gate. Any synthetic diagnostic input stays explicitly labelled and cannot satisfy this gate.

## Phase 2 — Connect the laptop and record the evidence

### Actions

- Create `ground_station/` for FastAPI ingestion/storage and `web/` for the minimum React viewer.
- Use one camera acquisition owner and a bounded latest-frame cache; multiple browser clients must not independently compete for camera capture.
- Define records containing session ID, source/mode, frame or sample ID, capture/sample timestamp, receive timestamp, validity, model/configuration versions and execution location.
- Show the real image, IR readings, radar status, connection state and age. Add session start/stop and recording controls.
- Keep `LIVE`, `REPLAY` and `SIMULATION` distinguishable. Label each input individually if a development session mixes real and synthetic sources.

### Validation

- Open the viewer and verify values against the serial/source log. Confirm a moving target changes the actual preview.
- Record and replay a short session, preserving order, IDs, source labels and configuration changes.
- Open a second client; check that capture does not duplicate and queues do not accumulate increasing lag.
- Interrupt Wi-Fi, then restore it. Confirm stale/disconnected indications, bounded retries and recovery without disguising old frames as live.
- Overlay results only on their matching frame IDs. Until clocks are aligned, distinguish laptop receive-to-display delay from true capture-to-display latency.

### Exit gate and evidence

- **Pass:** the laptop displays and records all available real inputs, identifies stale inputs and recovers from the tested connection interruption.
- **Evidence:** recorded session with manifest, preview/rate measurements and outage/recovery log.
- **If blocked:** keep acquisition/recording working through a simpler transport or USB telemetry, document the deviation, and retain truthful source labels.

## Phase 3 — Establish frontal person detection

### Actions

- Evaluate a suitable frontal-view detector on real OV7670 frames, including stationary people. Record the model, licence, input size, preprocessing and output semantics.
- Distinguish a model's boxes from FOMO-style centroids; draw only what the model actually estimates.
- Benchmark an onboard candidate using a fixed input buffer, then live capture, then concurrent camera/IR/radar/Wi-Fi operation.
- Make the execution decision before optional graphics work: measured ESP32 inference, or explicitly labelled laptop inference for the deadline fallback. Do not commit to custom training as a prerequisite for tomorrow's live demo.

### Validation

- Test empty scenes, standing/walking/stationary people, varied clothes and warm nonhuman objects. Use sessions not used for fitting the detector where applicable.
- Match overlays to source frames; check coordinate mapping after resize/crop/letterboxing.
- Measure inference time, delivered assessment rate, detection/false-positive counts and alert delay. Include camera conversion/network overhead in the integrated benchmark.
- For an **ESP32 execution claim**, save node-originated model outputs and timing/memory logs, disable laptop inference, and verify assessments continue with the browser closed. Compare fixed-buffer outputs with the exported reference using a documented tolerance.
- For a **laptop fallback**, verify detection uses the received real OV7670 frames and the UI labels inference as `LAPTOP`.

### Exit gate and evidence

- **Pass for frontal demo:** detections work on the intended live scene, their limitations and measured performance are recorded, and execution location is truthful.
- **Separate edge gate:** full onboard model fits with runtime memory headroom and passes integrated operation without allocation failures or unexplained resets. A laptop fallback does not pass this gate.
- **Evidence:** model/preprocessing manifest, labelled evaluation examples, timing report and execution-location decision.
- **If blocked:** use the explicitly labelled laptop fallback if viable. If no detector works adequately, mark person detection incomplete rather than substitute pose graphics or synthetic predictions.

## Phase 4 — Implement profiles, fusion and unavailable states

### Actions

- Start with clear and reduced-visibility profiles; represent elevated thermal context separately. A fire label alone does not prove camera degradation.
- Keep configuration versions, selected profile and actually active profile distinct until the fusion executor acknowledges application. The executor is the ESP32 in the target path or the laptop in the declared fallback.
- Map measurements to documented comparable evidence scores before weighting. Do not average raw degrees Celsius, dBm or radar energy with detector scores.
- Keep IR human-presence weight zero and Wi-Fi contribution disabled until phase 5 justifies them. Temperature remains visible as context.
- Implement fixed profile weights, validity/freshness checks, evidence coverage, disagreement and explicit insufficient-evidence states. Do not silently renormalise a surviving sensor into certainty.
- Implement persistence/hysteresis with logged parameters. Keep presence assessment separate from the camera's person locations.

### Validation

- Use deterministic synthetic records to check weighted arithmetic, invalid weights, unknown profiles, profile transitions, stale readings, conflicting evidence and all-input failure.
- Confirm synthetic tests are labelled and are not counted as physical detection evidence.
- Confirm profile selection changes weights, not raw observations, and a failed command does not appear applied.
- Confirm unavailable camera data does not become proof of an empty scene; radar-only evidence cannot produce a newly confirmed camera location.
- Confirm pose and person detection are not counted as independent sensor votes.

### Exit gate and evidence

- **Pass:** configuration and fusion behaviour match documented cases; every assessment records its evidence ages, coverage, active configuration and execution source.
- **Evidence:** reproducible logic checks, expected/observed outputs and versioned provisional profile file.
- **If blocked:** show independent sensor evidence and mark fused assessment unavailable. Do not present hand-picked percentages as validated settings.

## Phase 5 — Select weights through a labelled pilot

### Actions

1. Define ground truth as at least one person present in a marked common sensing zone. Use the trial schedule and independent annotation, not the detector being evaluated, to assign labels.
2. Before tuning, record the desired recall/false-alert/delay objective, event/window definition, freshness limits and persistence policy. Thresholds are design choices until tested.
3. Record clear and reduced-visibility sessions covering empty scene, walking person, stationary person, idle phone alone, warm phone alone and warm mug alone. Add elevated-background trials only if actually performed.
4. Use a removable translucent sheet in front of **only the camera** for the optical-degradation experiment; label it accordingly. An opaque cover is a separate unavailable-vision experiment. No actual smoke is required.
5. Remove the person after placing a nonhuman test object. Record IR distance, target orientation and sensor variant; a close-range thermal result cannot establish usefulness at the demo distance.
6. Separate fitting, validation and final test sessions, preferably with held-out people/backgrounds. A small pilot can use three distinct recording sessions, but must report its limited sample size. Never randomly divide adjacent video frames across the sets.
7. Fit sensor evidence mappings on fitting data only. Search nonnegative weights summing to one, including zero, and tune decision/persistence thresholds on validation data. No automatic environmental reweighting is added without its own validation.
8. Freeze the complete pipeline and run the untouched test sessions. If final results cause retuning, those sessions become development data and a new final test is needed.

### Validation

- Compare camera alone, radar alone, equal camera/radar weights, one global weight set and operator-selected condition-specific sets on the same trials.
- Compare with/without IR and any eligible Wi-Fi feature. Do not assume three inputs outperform two; retain zero weight when a benefit is not demonstrated.
- Include a mismatched-profile check so the effect of operator selection is visible.
- Report TP/FP/FN counts, precision, recall, false alerts per measured unoccupied minute/hour, alert delay, participant/session counts and sensor-unavailable time, by condition.
- State the metric unit. Example: event recall is the fraction of occupied trials alerted within a predeclared delay; time-window recall measures continued coverage. Do not interchange the two or treat adjacent frames as independent trials.
- Separate detection misses from missing-input intervals, and report both. A short pilot with zero false alerts does not establish a long-term zero false-alert rate.

### Exit gate and evidence

- **Pass for pilot calibration:** settings, selection objective, dataset splits and held-out results are reproducible. Meeting an acceptance target is a separate recorded outcome; do not pass performance merely because optimisation ran.
- **Evidence:** dataset manifest/labels, split assignments, frozen profile/model versions, baseline comparison table and limitations.
- **If data are insufficient or results fail:** retain provisional labels, show observed failures, and restrict claims to a proof of concept. Do not claim validated disaster detection or universally correct weights.

## Phase 6 — Complete the dashboard and explanatory 3D view

### Actions

- Extend the React viewer with camera detections, sensor history, selected/active profile, weights, weighted contributions, assessment, thermal context and health.
- Add a generic avatar and perspective/overhead toggle in Three.js. Label the scene illustrative; avatar rotation does not produce a measured overhead camera image.
- Use schematic zone placement initially. For meaningful floor position, fix the camera, identify four known floor points, and map a visible foot-contact estimate onto that calibrated plane.
- Optional: estimate pose on the laptop and animate the avatar. Record pose execution location and distinguish estimated pose from measured depth or a scanned body.
- Freeze/fade the avatar with a last-seen label when visual tracking is lost; radar-only presence cannot keep a precise live pose/location confirmed.

### Validation

- Confirm all displayed values come from recorded/live records and change with the actual inputs, not presentation-only animations.
- Switch profile and verify acknowledgement/version, contribution bars and assessment against the phase 4 calculation.
- Check lost detections, stale frames, invalid sensors and replay mode visibly alter the correct UI elements.
- If floor calibration is used, test separate marked positions not used for calibration and record position error. Hide or mark location uncertain when feet are not visible or assumptions fail.
- Confirm overhead toggle changes the rendering viewpoint only. Do not count rendered screenshots as real overhead training or validation data.

### Exit gate and evidence

- **Pass:** the interface explains actual evidence, uncertainty and processing location, and its 3D content cannot be mistaken for measured aerial reconstruction.
- **Evidence:** screenshots or screen recording for live, degraded, stale and replay states; calibration report if applicable.
- **If blocked:** keep the working evidence dashboard and a simple labelled avatar/zone. Remove unstable pose animation before sacrificing real acquisition or clear source labels.

## Phase 7 — Rehearse, test stability and freeze

### Actions

- Rehearse: empty scene → person enters → stationary person → translucent screen → operator selects reduced visibility → screen removed → warm object without a person → camera obstruction → recovery.
- Exercise a sensor timeout, Wi-Fi interruption and restart. Record recovery and any manual intervention required.
- Run all enabled features together for a measured stability period. Aim for the existing one-hour soak target if time permits; a shorter run must state its actual duration.
- Record software/model/profile versions, build settings, launch instructions and the tested hardware layout. Save a known working build and a recorded session as separate backups.
- Freeze the demonstration configuration. Changes after the freeze require repeating the affected checks; model/weight/threshold changes also invalidate the prior final evaluation for the new configuration.

### Validation

- Complete the scripted demonstration twice without unexplained resets, growing lag or synthetic data appearing as live observations.
- Verify no-camera and no-input states are truthful; missing observations cannot produce an all-clear message or fabricated position.
- Check integrated frame/assessment rate, available latency measurements, sensor ages, memory where observable, dropped data and fault recovery against the declared targets below.
- Restart the documented system and confirm it opens in the correct mode with the expected configuration. Replay must retain a prominent `REPLAY` label.

### Exit gate and evidence

- **Pass:** the defined reduced-scope demo is repeatable, its required performance gates are met, faults are explicit and limitations are documented. Optional failures are removed or isolated and reported.
- **Evidence:** rehearsal checklist, actual-duration stability log, metrics, frozen version manifest, known issues and launch/recovery instructions.
- **If blocked:** disable optional pose/CSI/graphics features and repeat the relevant checks. Declare any remaining missing capability rather than marking the whole plan complete.

## Proposed engineering targets — not measured results

Confirm these before the integrated run; log revisions and reasons. These are demonstration usability targets, not disaster-response requirements or validated hardware specifications.

| Area | Proposed minimum / check | Stretch target or qualification |
|---|---|---|
| Real preview | At least 1 fresh displayed frame/second without accumulating lag | Existing implementation target: at least 3 FPS if measured feasible |
| Assessment throughput | At least 1 completed assessment/second | Existing implementation target: 2/second |
| Displayed frame age | p95 at most 2 seconds when capture age is measurable | Aim for 1 second; without clock alignment report receive-to-display delay separately |
| Alert timing | Predeclare a target; initial engineering target p95 at most 2 seconds from annotated entry | Include persistence and communication delay; report misses separately |
| Onboard processing | Measure capture, preprocess, inference and fusion separately | Existing target p95 capture-to-assessment at most 500 ms; only applicable to verified onboard execution |
| Detection quality | Record the acceptance recall and false-alert budget before phase 5 tuning | No accuracy percentage is asserted by this plan |
| Freshness | Declare timeout per stream before testing and verify invalidation after it | No repeated old packet may refresh its original measurement time |
| Stability | Two complete rehearsals and a documented concurrent run | Aim for one hour; report actual duration and failures |

## Optional experiment — RSSI/CSI

Run only after the core pipeline works. This is not a requirement for the initial demo pass.

- RSSI: log timestamped received signal strength and variation as communication/experimental data first.
- CSI: verify acquisition support in the chosen firmware build; configure received traffic and move processing out of the Wi-Fi callback into bounded queued work.
- Keep transmitter and receiver fixed. If a phone is the hotspot/transmitter, do not move that same phone as the test reflector. Keep the link's sensing zone distinct from the camera/radar zone unless overlap has been verified.
- Record empty, moving-person, stationary-person and nonhuman-disturbance trials, including camera-streaming load. Check that traffic or packet-rate changes do not become an apparent presence signal.
- **Validation gate:** usable acquisition, repeatable labelled behaviour, held-out improvement and no unacceptable degradation of the core pipeline. RSSI/CSI are not independent votes merely because both are available from one link.
- **If not passed:** keep a labelled diagnostic plot or omit the feature; human-presence weight remains zero. A motion response does not establish stationary human detection or localisation.

## Evidence and completion record

Suggested working layout; these application/evidence directories are deliverables to create, not existing completed software:

```text
firmware/ares_node/             working firmware and configuration
ground_station/                FastAPI ingestion, recording and evaluation
web/                           React dashboard and illustrative 3D scene
models/                        model/export/preprocessing manifests
benchmarks/sessions/            recordings and independent ground truth
benchmarks/results/             metrics, comparisons and timing reports
docs/hardware/                 verified wiring and board/module settings
docs/validation/                gate records, fault checks and rehearsal notes
```

For each phase record: status, executor/tester, date, hardware/software/configuration versions, checks performed, measured outcomes, evidence paths, failures, chosen fallback and remaining work. `NOT RUN` is different from `PASS`.

## Immediate next actions

- [ ] Obtain the current working camera sketch/status, stream IP and Arduino COM port.
- [ ] Confirm actual IR SDA/SCL and radar TX/RX GPIOs and power connections.
- [ ] Record board/PSRAM settings and full MLX90614/radar variant markings.
- [ ] Complete phase 0 and start camera/IR/radar bring-up in phase 1.
- [ ] Establish the common data record and minimum laptop viewer in phase 2.

Related context: [PLAN.md](PLAN.md) and [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md). This action plan defines the current execution order and phase validation; none of the earlier candidate-model or timing targets are completed results.
