# ARES — team context and current demo plan

Updated: 31 October 2026. This is the current team handoff, not a claim that every planned feature has been implemented.

## 1. What we are building

**ARES: Aerial Reconnaissance Emergency Support System.**

The long-term idea is a rapidly deployable aerial sensing node that provides early observations of a disaster area before first responders arrive. Intended outputs include possible human presence, visible openings/unobstructed approaches, and scene context for responders. Several deployed nodes and a ground station are future extensions.

The current project demonstration uses **one ESP32-S3 node and one laptop**. For interaction with visitors, the camera will face people from the front. This demonstrates the sensing, communications and assessment pipeline; it does not validate overhead disaster deployment.

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
| All three sensors receive assumed human-detection weights | Start with camera/radar presence evidence; test whether IR adds value | Three inputs are not automatically better than two; zero weight is an acceptable experimental result |
| Example weights such as 70/30 and 20/80 | Numerical settings remain provisional until trial-based selection | Earlier examples explained arithmetic, not established accuracy |
| Satellite/terrain views and 3D reconstruction | Simple illustrative scene with a generic avatar first | A single frontal camera does not measure an overhead scene or complete wreckage geometry |
| Streamlit-style viewer considered in older code | React/TypeScript/Vite frontend plus Python FastAPI backend | Current interface preference; the older simulated application is not the current live system |
| ESP32 antenna used only for communication | Optional RSSI/CSI sensing experiment may be added later | Acquisition, environmental confounds and held-out benefit must be tested before giving it a presence weight |

## 3. Components and intended roles

| Component | Role in this demo | Important limit |
|---|---|---|
| ESP32-S3-WROOM-1U, Espressif | Acquire/timestamp sensor data, stream camera frames, and ultimately run lightweight inference/fusion | USB query identified 8 MB flash and 8 MB embedded PSRAM; usable runtime memory still needs testing |
| OV7670 camera | Real frontal images, person detections and image locations | Actual viewpoint, image quality and preprocessing determine detection performance |
| LD2410-family mmWave radar | Corroborate presence/motion in a tested zone | Exact variant/GPIOs need confirmation; do not infer individual camera-person identities, count or bearing from broad presence output |
| MLX90614 IR thermometer | Object-area temperature, changes from a measured baseline and elevated-temperature context | No spatial heatmap; warm phones/mugs/backgrounds can overlap human surface readings |
| ESP32 Wi-Fi antenna | Camera/data communication; optional later channel-sensing experiments | It is not an additional human detector just because the link exists |
| Laptop | Ground-station ingestion, recording, evaluation, API and any explicitly declared inference fallback | Laptop inference must not be called ESP32 edge inference |
| React + Three.js browser view | Display live evidence and an illustrative/estimated 3D avatar with perspective/overhead viewing | A rotated avatar is not a measured top-view camera image or accurate body reconstruction |

LoRa/SX1262, NEO-6M GPS, Raspberry Pi and multi-node networking are not part of the current live demonstration.

## 4. Processing and display plan

### Target execution

1. ESP32 acquires camera/radar/IR observations with IDs, timestamps and health flags.
2. A benchmarked small person model and lightweight fusion ultimately run on the ESP32.
3. Wi-Fi transports real preview frames and telemetry to the laptop.
4. FastAPI ingests, records and serves the current evidence; React renders the interface.

### Deadline fallback

If the onboard detector cannot be integrated and measured in time, the laptop can run frontal person detection and necessary provisional fusion. The UI and report must state the actual inference/fusion execution location. Onboard AI/fusion remains pending in this configuration.

Model choice, export and measured onboard performance are not settled. Preset weights and thresholds are rule-based processing; they are not themselves a trained AI model.

### Interface

- Actual OV7670 frames with model-appropriate detections: boxes if the model outputs boxes, centroids if it outputs centroids.
- Radar presence, IR readings, measurement ages and connection/validity status.
- Selected profile, acknowledged active profile, weights, evidence contributions and assessment.
- Separate presence assessment and thermal context.
- Clearly distinguished LIVE, REPLAY and SIMULATION states.
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
6. Freeze and evaluate on untouched test sessions. Compare individual sensors, equal weights, one global weight set, condition-specific sets, and with/without IR or any eligible Wi-Fi feature.
7. Report per-condition counts, precision, recall, false-alert exposure, delay, trial/participant counts, unavailable time and limitations. Retuning after seeing final results requires new final-test data.

IR starts with zero human-presence weight until its benefit is demonstrated, while its actual temperature observations remain visible. RSSI is initially diagnostic and CSI experimental. A weighted fusion score is not automatically a calibrated probability.

Missing/stale evidence means reduced coverage or insufficient evidence. It must not become proof that nobody is present, or silently turn a surviving sensor into certainty.

## 6. Interactive experiments

### Reduced visibility

- Place a removable translucent sheet in front of only the camera; leave IR and radar unobstructed.
- First observe actual detector behaviour without changing the profile, then select the reduced-visibility profile to explain the changed weighting.
- Label this optical degradation, not real-smoke or fire validation. Detection may remain confident through mild obstruction; rehearse rather than force the expected result.
- An opaque cover is a separate unavailable-vision/fault experiment.
- Any optional software haze must affect detector input, not only the displayed image, and be labelled simulated degradation.

### Human versus phone/other warm object

- Compare empty background, a person, an idle phone, a warm phone after normal use, and a warm mug.
- Record distance, target orientation, background and sensor variant; step away after placing nonhuman objects.
- Treat overlapping readings as evidence about limits, not an experiment failure to hide. Close-range differences do not validate the aerial sensing footprint.

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
| IR/radar | Active hardware intended, but actual GPIO/power confirmation and current acquisition code remain pending |
| Person detector / trained model | Not selected/deployed/validated yet |
| React/FastAPI application and 3D scene | Planned; not implemented yet |
| Profile values / detection accuracy | Not experimentally validated |
| CSI sensing | Not implemented or validated |

A compiled camera sketch is not a completed sensing or AI system. Build/linker RAM statistics are not measured runtime memory or power consumption.

## 8. Immediate execution plan and team coordination

Use [ACTION_PLAN.md](ACTION_PLAN.md) for phase-by-phase checks and pass criteria.

1. Finish hardware/power/GPIO verification and confirm demo Wi-Fi configuration.
2. Upload/test the camera baseline and obtain actual independent IR/radar readings.
3. Establish timestamped recording and a minimum live React/FastAPI viewer.
4. Integrate frontal detection and record the measured onboard-versus-laptop execution decision.
5. Verify profile/fusion logic, gather a labelled pilot, select/freeze settings and evaluate held-out sessions.
6. Add the illustrative avatar, then optional pose animation.
7. Rehearse degraded visibility, thermal false-positive cases, connection loss, stale inputs and recovery; freeze a repeatable build.

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
