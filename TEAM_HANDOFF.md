# ARES — team context and current demo plan

Updated: 31 October 2026. This is the current team handoff, not a claim that every planned feature has been implemented.

## 1. What we are building

**ARES: Aerial Reconnaissance Emergency Support System.**

The long-term idea is a rapidly deployable aerial sensing node that provides early observations of a disaster area before first responders arrive. Intended outputs include possible human presence, visible openings/unobstructed approaches, and scene context for responders. Several deployed nodes and a ground station are future extensions.

The current project demonstration uses **one ESP32-S3 node and one laptop**. For interaction with visitors, the camera will face people from the front. This demonstrates the sensing, communications and assessment pipeline; it does not validate overhead disaster deployment.

**Current architecture:** IR hardware is not working, so laptop values are labelled SYNTHETIC. Radar is separate from the ESP32 and now streams directly to the laptop over Bluetooth. Camera runtime and a person detector are still missing, so no automatic person/fusion score is produced. See [the source contract](docs/synthetic-ir-demo.md).

Implementation update: direct radar-to-laptop Bluetooth now authenticates and streams actual reports, with the phone app disconnected during laptop use. FastAPI, React, synthetic IR and source-labelled recording/export work. Actual camera address/runtime, person detection, calibrated fusion and 3D remain pending; [validation](docs/validation/backend-2026-10-31.md).

## 2. How the plan evolved

| Earlier idea | Current decision | Reason or consequence |
|---|---|---|
| Multiple aerial nodes and mesh/star networking | One node for the demonstration | Establish one working pipeline before multi-node integration |
| Raspberry Pi ground station; Arduino Uno also considered | Laptop ground station | Reduce integration time; Pi migration can follow |
| LoRa included in the supplied circuit drawing | No LoRa in the current demo; use ESP32 Wi-Fi and USB | Real camera frames use local Wi-Fi; USB supports programming/debugging |
| GPS in the original hardware list | No GPS in the current demo | Any scene position must be configured or calibrated, not presented as a live GPS fix |
| Node infers disaster type and changes weights | Operator explicitly selects a condition/profile | Keep the condition choice explainable and controllable |
| Nearly vertical overhead camera | Frontal camera for the imminent interactive demo | Let visitors participate; overhead data/training/validation remain separate work |
| Thermal readings identify human heat signatures spatially | MLX90614 provides aggregate spot-temperature context | It is a thermometer, not a thermal imaging array; its human-presence contribution needs evidence |
| Working physical IR assumed | IR hardware unavailable; laptop synthetic provider | Label simulation and exclude it from physical detection claims/weight fitting |
| Radar assumed wired to ESP32 | Separate app/web system | Inspect supported external data access; no GPIO/UART integration |
| All three sensors receive assumed human-detection weights | Camera-only initially; camera/radar fusion only after real external integration | IR stays zero-weight while synthetic; missing radar is explicit |
| Example weights such as 70/30 and 20/80 | Numerical settings remain provisional until trial-based selection | Earlier examples explained arithmetic, not established accuracy |
| Satellite/terrain views and 3D reconstruction | Simple illustrative scene with a generic avatar first | A single frontal camera does not measure an overhead scene or complete wreckage geometry |
| Streamlit-style viewer considered in older code | React/TypeScript/Vite frontend plus Python FastAPI backend | Current interface preference; the older simulated application is not the current live system |
| ESP32 antenna used only for communication | Optional RSSI/CSI sensing experiment may be added later | Acquisition, environmental confounds and held-out benefit must be tested before giving it a presence weight |

## 3. Components and intended roles

| Component | Role in this demo | Important limit |
|---|---|---|
| ESP32-S3-WROOM-1U, Espressif | Real camera acquisition/streaming; possible later onboard person inference | USB query identified 8 MB flash and 8 MB embedded PSRAM; runtime remains to be tested |
| OV7670 camera | Real frontal images, person detections and image locations | Actual viewpoint, image quality and preprocessing determine detection performance |
| Separate radar system | Direct BLE presence/distance reports into the laptop and dashboard | Not wired to ESP32; stream verified, labelled accuracy and scene alignment pending |
| MLX90614 / synthetic replacement | Physical hardware unavailable; laptop fixtures drive labelled thermal-context demonstrations | No physical IR sensing, spatial heatmap or human-thermal accuracy claim |
| ESP32 Wi-Fi antenna | Camera/data communication; optional later channel-sensing experiments | It is not an additional human detector just because the link exists |
| Laptop | Camera worker, synthetic IR, actual radar, recording/export and API | Detector/fusion remain unimplemented; any later laptop inference must retain its execution label |
| React + Three.js browser view | Display live evidence and an illustrative/estimated 3D avatar with perspective/overhead viewing | A rotated avatar is not a measured top-view camera image or accurate body reconstruction |

LoRa/SX1262, NEO-6M GPS, Raspberry Pi and multi-node networking are not part of the current live demonstration.

## 4. Processing and display plan

### Target execution

1. ESP32 supplies real camera images and health/timestamps over Wi-Fi.
2. Laptop generates independent synthetic IR with fixed provenance and no invented physical timestamp.
3. The implemented BLE adapter supplies authenticated actual radar reports. Disconnected/stale inputs remain unavailable.
4. FastAPI records/serves sources and React displays them. Person detection and fused assessment remain pending rather than being fabricated from raw inputs.

### Deadline fallback

The first frontal detector can run on the laptop with explicit execution labels. Onboard camera inference remains a separate benchmarked milestone. Fusion will be implemented on the laptop because radar is external; returning other sources to the ESP32 for onboard fusion is deferred.

Model choice, export and measured onboard performance are not settled. Preset weights and thresholds are rule-based processing; they are not themselves a trained AI model.

### Interface

- Actual OV7670 frames with model-appropriate detections: boxes if the model outputs boxes, centroids if it outputs centroids.
- External radar status/data only if verified; synthetic IR values with unavailable hardware, plus source/age/connection labels.
- Selected profile, acknowledged active profile, weights, evidence contributions and assessment.
- Separate presence assessment and thermal context.
- Clearly distinguished MIXED (real plus synthetic), REPLAY and SIMULATION states, with per-input provenance.
- Generic avatar and overhead/perspective toggle; optional laptop pose estimation can animate the avatar after the live pipeline is stable.
- Schematic zone placement initially. Meaningful floor position requires a fixed camera, known floor points and a calibrated visible foot-contact estimate.
- Last-seen/uncertain avatar when vision is lost. Radar-only presence cannot maintain a newly confirmed precise pose/location.

Person detection and pose estimation share the same camera; they are not two independent sensing votes.

## 5. How we will justify the weights

The operator selects the condition; that choice loads a frozen, versioned configuration. It does not change raw observations or prove that fire/smoke actually exists.

1. Define the task as presence of at least one person in a marked common sensing zone. Keep camera localisation separate from zone-level fusion.
2. Record synchronised actual observations and independent ground truth for empty scenes, walking/stationary people and nonhuman warm objects under clear and degraded visibility.
3. Separate fitting, validation and final test sessions; where possible hold out people/backgrounds. Do not randomly split adjacent video frames between them.
4. Fit documented evidence mappings using fitting data. Raw Celsius, dBm and radar energy must not be averaged directly with model scores.
5. Search nonnegative weights summing to one, allowing zero, together with decision/persistence thresholds. Predeclare the recall/false-alert/delay objective and select settings using validation data.
6. Freeze and evaluate on untouched test sessions. Compare real camera/radar baselines and weighting only after actual radar integration. Exclude synthetic IR from physical weight fitting and accuracy.
7. Report per-condition counts, precision, recall, false-alert exposure, delay, trial/participant counts, unavailable time and limitations. Retuning after seeing final results requires new final-test data.

IR has zero weight while synthetic. Fixtures can check displays, transport and separate software logic, not real thermal detection benefit. Without a verified radar feed, automatic multi-sensor calibration remains pending. RSSI is diagnostic and CSI experimental; weighted indices are not automatically calibrated probabilities.

Missing/stale evidence means reduced coverage or insufficient evidence. It must not become proof that nobody is present, or silently turn a surviving sensor into certainty.

## 6. Interactive experiments

### Reduced visibility

- Place a removable translucent sheet in front of only the camera. Radar is a separate system; IR is simulated.
- First observe actual detector behaviour. Demonstrate changed camera/radar weighting only if a real external radar adapter works; otherwise label the assessment camera-only.
- Label this optical degradation, not real-smoke or fire validation. Detection may remain confident through mild obstruction; rehearse rather than force the expected result.
- An opaque cover is a separate unavailable-vision/fault experiment.
- Any optional software haze must affect detector input, not only the displayed image, and be labelled simulated degradation.

### Human versus phone/other warm object

- Physical IR comparison is deferred while the sensor is not working. Synthetic scenarios do not measure a person, phone or mug.
- Nonhuman-object cases can still challenge camera or actual integrated radar. Step away after placing objects so the tester is not the presence signal.
- Thermal scenario controls are independent from the selected disaster profile and real occupancy.

### Optional Wi-Fi sensing

- Keep transmitter and receiver fixed and compare empty, walking-person, stationary-person and nonhuman-disturbance sessions.
- If a phone acts as the hotspot/transmitter, do not move that same phone as the reflector in the same trial.
- A varying RSSI/CSI trace initially indicates channel disturbance, not a proven human classification or position.
- Add a Wi-Fi contribution only after held-out comparison shows benefit and concurrent acquisition does not disrupt the camera pipeline.

## 7. What is actually complete

| Item | Verified status |
|---|---|
| Reference firmware | Inspected `rounak-vyas` at `e2e770a8ebfbef6a6824544be477ca15c3299e1c` |
| Arduino tooling | CLI 1.5.1 installed locally; existing ESP32 core 3.3.7 reused |
| USB identification | ESP32-S3 on COM3; 8 MB flash and 8 MB embedded PSRAM identified by esptool |
| Working camera firmware | Copied to `firmware/ares_node/ares_node.ino`; camera configuration zero-initialised |
| Compile | Passed with the recorded ESP32-S3/8 MB flash/OPI PSRAM settings |
| Application firmware upload | Not performed during this work |
| Runtime camera, usable PSRAM and Wi-Fi | Not validated here yet |
| IR | User reports nonworking; standalone synthetic laptop provider created and checked |
| Radar | Direct BLE receiver authenticated and decoded real reports; labelled accuracy/scene/outage trials remain pending |
| Person detector / trained model | Not selected/deployed/validated yet |
| React/FastAPI application | Initial camera/source/status controls, synthetic IR, actual radar and recording/export implemented |
| 3D scene / pose | Not implemented yet |
| Profile values / detection accuracy | Not experimentally validated |
| CSI sensing | Not implemented or validated |

A compiled camera sketch is not a completed sensing or AI system. Build/linker RAM statistics are not measured runtime memory or power consumption.

## 8. Immediate execution plan and team coordination

Use [ACTION_PLAN.md](ACTION_PLAN.md) for phase-by-phase checks and pass criteria.

1. Finish camera wiring/power/network verification; no IR repair or radar UART prerequisites.
2. Validate/upload the real camera baseline and retain the checked synthetic IR provider.
3. Build FastAPI camera ingestion, synthetic IR, health and recording, then the minimal React viewer. Validate the documented direct BLE radar connection in parallel, with its phone app disconnected during laptop access.
4. Integrate frontal detection and record the measured onboard-versus-laptop execution decision.
5. Verify eligible-source logic and run real camera evaluation; add camera/radar fusion calibration only if a verified external feed exists. Synthetic IR is excluded from physical metrics.
6. Add the illustrative avatar, then optional pose animation.
7. Rehearse degraded visibility, labelled synthetic thermal scenarios, connection loss/staleness and recovery; freeze the explicitly reduced demo scope.

Suggested workstreams, with named owners to be agreed by the team:

- **Firmware/hardware:** wiring, power, acquisition, transport, board execution and timing.
- **Perception/evaluation:** model/preprocessing, independent labels, dataset split, weight selection and benchmarks.
- **Backend/integration:** ingestion, bounded buffering, recording/replay, configuration acknowledgements and evidence contracts.
- **Frontend/visualisation:** React evidence display, clear uncertainty/mode labels and the illustrative 3D scene.

Agree the record schema, frame IDs/timestamps, units, stale limits, profile version and inference-location fields together before independently building the parts. Share recordings and test results across workstreams.

## 9. What to share with collaborators

Send this handoff as the entry point, then link:

- [ACTION_PLAN.md](ACTION_PLAN.md): phase order, validation, exit gates and fallbacks.
- [PLAN.md](PLAN.md): current scope and decisions.
- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md): technical target pipeline and measurements.
- [Board configuration](docs/hardware/board-config.md): observed device and build settings.
- [Camera build validation](docs/validation/camera-build-2026-10-31.md): what was actually checked.
- Working firmware and a current labelled circuit/pin table once verified. The supplied drawing still contains excluded LoRa hardware and is a historical reference, not proof of current wiring.

Keep Wi-Fi secrets local. Publish a credential template rather than populated credentials. Downloaded executables/archives, compiler artifacts, machine-specific paths and dependency caches are not the project handoff.

Describe planned features as planned, laptop inference as laptop inference, and illustrative graphics as illustrative. No claim of validated aerial deployment, real-smoke robustness, spatial thermal human identification or guaranteed safe routes has been established.
