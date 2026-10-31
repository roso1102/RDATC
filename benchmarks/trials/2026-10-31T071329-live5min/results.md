# ARES live trial results — 2026-10-31T071329-live5min

Session `5f567b455d4642b5a91f46e269b9c9fe`; live fusion profile `clear`. Ground truth = protocol timing (person inside the marked zone); settle windows excluded. All weights/thresholds are provisional or literature priors; synthetic IR has zero applied weight and is excluded.

## Detection performance (per observation)

| Source | n | Precision | Recall | F1 | Specificity | False-alert rate | Accuracy | ROC-AUC |
|---|---|---|---|---|---|---|---|---|
| ESP32 on-device (TFLM, 96×96, score ≥ 0.5) | 257 | 0.969 | 0.735 | 0.836 | 0.954 | 0.046 | 0.809 | 0.837 |
| Laptop YOLOX-Nano (≥ 1 box) | 257 | 0.964 | 0.776 | 0.86 | 0.943 | 0.057 | 0.833 | 0.879 |
| Radar presence flag | 2481 | 0.702 | 1 | 0.825 | 0 | 1 | 0.702 | — |
| Fused decision (live, 1 Hz) | 248 | 0.966 | 0.805 | 0.878 | 0.932 | 0.068 | 0.843 | — |

ESP32 vs laptop on the same frames: 257 frames, agreement 0.922, Cohen's κ 0.844.

## Positive rate by condition

| Condition | Person | ESP32 on-device | Laptop YOLOX-Nano | Radar presence flag | Fused decision |
|---|---|---|---|---|---|
| 1. Empty scene | no | 0 | 0 | 1 | 0 |
| 2. Walking | yes | 0.714 | 0.714 | 1 | 0.68 |
| 3. Standing, frontal | yes | 0.625 | 1 | 1 | 1 |
| 4. Standing, far | yes | 0.667 | 0.75 | 1 | 0.84 |
| 5. Standing, side view | yes | 1 | 1 | 1 | 1 |
| 6. Sitting or crouching | yes | 1 | 0.933 | 1 | 0.96 |
| 7. Partly occluded | yes | 1 | 0.897 | 1 | 0.92 |
| 8. Camera covered | yes | 0.125 | 0.083 | 1 | 0.136 |
| 9. Object, no person | no | 0.16 | 0.2 | 1 | 0.227 |
| 10. Empty scene | no | 0 | 0 | 1 | 0 |

Positive rate = share of observations reporting a person. For person-present rows this is the detection rate; for empty/object rows it is the false-alert rate.

## Fusion under each condition profile (offline replay of recorded evidence, 0.5 s ticks)

| Profile | Applied camera/radar | Status | Precision | Recall | F1 | False-alert rate | Decision changes |
|---|---|---|---|---|---|---|---|
| clear | 0.70 / 0.30 | PROVISIONAL_NOT_CALIBRATED | 0.969 | 0.802 | 0.878 | 0.06 | 16 |
| reduced_visibility | 0.20 / 0.80 | PROVISIONAL_NOT_CALIBRATED | 0.7 | 1 | 0.824 | 1 | 1 |
| fire_no_smoke | 0.56 / 0.44 | LITERATURE_PRIOR_UNCALIBRATED | 0.773 | 0.957 | 0.855 | 0.658 | 1 |
| fire_smoke | 0.11 / 0.89 | LITERATURE_PRIOR_UNCALIBRATED | 0.7 | 1 | 0.824 | 1 | 1 |
| flood | 0.75 / 0.25 | LITERATURE_PRIOR_UNCALIBRATED | 0.969 | 0.802 | 0.878 | 0.06 | 16 |
| earthquake | 0.16 / 0.84 | LITERATURE_PRIOR_UNCALIBRATED | 0.7 | 1 | 0.824 | 1 | 1 |
| camera_only | 1.00 / 0.00 | BASELINE | 0.962 | 0.655 | 0.779 | 0.06 | 15 |
| radar_only | 0.00 / 1.00 | BASELINE | 0.7 | 1 | 0.824 | 1 | 1 |

## Delays (seconds after the cue; includes the operator's movement time)

| Source | First detection after entry cue | Last positive after exit cue |
|---|---|---|
| esp32_tflm | 12.37 | 12.44 |
| laptop_yolox | 12.37 | 12.44 |
| radar | 0.08 | 29.93 |
| fusion_live | 13.2 | 13.69 |
| fusion_replay_clear | 12.92 | 13.27 |

## Latency and throughput

| Measure | n | p50 | p95 | max |
|---|---|---|---|---|
| esp32 inference (ms) | 341 | 58 | 59 | 60 |
| esp32 preprocess (ms) | 341 | 24 | 25 | 25 |
| laptop inference (ms) | 341 | 18.7 | 30.4 | 65 |
| node fetch incl capture inference jpeg (ms) | 341 | 328 | 531 | 907 |

Duration 300.8 s; camera 1.05 fps; radar 10.0 Hz; ESP32 result present on 1 of frames.
Backend frame age p50/p95: 438/812 ms; camera available 0.907 of polls; outages 1.

## Limitations

- One participant, one room, one ~5-minute session: results are a pilot, not a generalisable accuracy claim.
- Ground truth is protocol timing, not frame-by-frame annotation; transitions are excluded via settle windows.
- Fusion profile weights are provisional/literature priors and were not tuned on this session; the replay applies the live rules to the same recorded evidence.
- Disaster profiles are exercised on a lab scene, not on fire, smoke, flood or rubble.
- Radar presence covers a wider area than the camera; spatial alignment is unverified.
