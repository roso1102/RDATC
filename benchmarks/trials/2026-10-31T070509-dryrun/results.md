# ARES live trial results — 2026-10-31T070509-dryrun

Session `2092b6e540e947d48f36183db3bd2dc6`; live fusion profile `clear`. Ground truth = protocol timing (person inside the marked zone); settle windows excluded. All weights/thresholds are provisional or literature priors; synthetic IR has zero applied weight and is excluded.

## Detection performance (per observation)

| Source | n | Precision | Recall | F1 | Specificity | False-alert rate | Accuracy | ROC-AUC |
|---|---|---|---|---|---|---|---|---|
| ESP32 on-device (TFLM, 96×96, score ≥ 0.5) | 30 | 1 | 0.05 | 0.095 | 1 | 0 | 0.367 | 0.55 |
| Laptop YOLOX-Nano (≥ 1 box) | 30 | 0.667 | 0.2 | 0.308 | 0.8 | 0.2 | 0.4 | 0.495 |
| Radar presence flag | 248 | 0.702 | 1 | 0.825 | 0 | 1 | 0.702 | — |
| Fused decision (live, 1 Hz) | 24 | 1 | 0.188 | 0.316 | 1 | 0 | 0.458 | — |

ESP32 vs laptop on the same frames: 30 frames, agreement 0.833, Cohen's κ 0.242.

## Positive rate by condition

| Condition | Person | ESP32 on-device | Laptop YOLOX-Nano | Radar presence flag | Fused decision |
|---|---|---|---|---|---|
| 1. Empty scene | no | 0 | 0.25 | 1 | 0 |
| 2. Walking | yes | 0 | 0 | 1 | 0.333 |
| 3. Standing, frontal | yes | 0.333 | 0.333 | 1 | 0.333 |
| 4. Standing, far | yes | 0 | 0.333 | 1 | 0 |
| 5. Standing, side view | yes | 0 | 0.333 | 1 | 0.5 |
| 6. Sitting or crouching | yes | 0 | 0 | 1 | 0 |
| 7. Partly occluded | yes | 0 | 0 | 1 | 0 |
| 8. Camera covered | yes | 0 | 0.333 | 1 | 0 |
| 9. Object, no person | no | 0 | 0.333 | 1 | 0 |
| 10. Empty scene | no | 0 | 0 | 1 | 0 |

Positive rate = share of observations reporting a person. For person-present rows this is the detection rate; for empty/object rows it is the false-alert rate.

## Fusion under each condition profile (offline replay of recorded evidence, 0.5 s ticks)

| Profile | Applied camera/radar | Status | Precision | Recall | F1 | False-alert rate | Decision changes |
|---|---|---|---|---|---|---|---|
| clear | 0.70 / 0.30 | PROVISIONAL_NOT_CALIBRATED | 0.625 | 0.139 | 0.227 | 0.2 | 9 |
| reduced_visibility | 0.20 / 0.80 | PROVISIONAL_NOT_CALIBRATED | 0.706 | 1 | 0.828 | 1 | 1 |
| fire_no_smoke | 0.56 / 0.44 | LITERATURE_PRIOR_UNCALIBRATED | 0.8 | 1 | 0.889 | 0.6 | 1 |
| fire_smoke | 0.11 / 0.89 | LITERATURE_PRIOR_UNCALIBRATED | 0.706 | 1 | 0.828 | 1 | 1 |
| flood | 0.75 / 0.25 | LITERATURE_PRIOR_UNCALIBRATED | 0.625 | 0.139 | 0.227 | 0.2 | 9 |
| earthquake | 0.16 / 0.84 | LITERATURE_PRIOR_UNCALIBRATED | 0.706 | 1 | 0.828 | 1 | 1 |
| camera_only | 1.00 / 0.00 | BASELINE | 0 | 0 | 0 | 0.133 | 3 |
| radar_only | 0.00 / 1.00 | BASELINE | 0.706 | 1 | 0.828 | 1 | 1 |

## Delays (seconds after the cue; includes the operator's movement time)

| Source | First detection after entry cue | Last positive after exit cue |
|---|---|---|
| esp32_tflm | — | 0 |
| laptop_yolox | — | 1.25 |
| radar | 0.08 | 2.92 |
| fusion_live | 0.67 | 0 |
| fusion_replay_clear | 0.42 | 2.26 |

## Latency and throughput

| Measure | n | p50 | p95 | max |
|---|---|---|---|---|
| esp32 inference (ms) | 37 | 58 | 59 | 60 |
| esp32 preprocess (ms) | 37 | 24 | 25 | 25 |
| laptop inference (ms) | 37 | 20.6 | 43.1 | 108.4 |
| node fetch incl capture inference jpeg (ms) | 37 | 343 | 516 | 532 |

Duration 30.8 s; camera 1.17 fps; radar 9.99 Hz; ESP32 result present on 1 of frames.
Backend frame age p50/p95: 438/782 ms; camera available 1 of polls; outages 0.

## Limitations

- One participant, one room, one ~5-minute session: results are a pilot, not a generalisable accuracy claim.
- Ground truth is protocol timing, not frame-by-frame annotation; transitions are excluded via settle windows.
- Fusion profile weights are provisional/literature priors and were not tuned on this session; the replay applies the live rules to the same recorded evidence.
- Disaster profiles are exercised on a lab scene, not on fire, smoke, flood or rubble.
- Radar presence covers a wider area than the camera; spatial alignment is unverified.
