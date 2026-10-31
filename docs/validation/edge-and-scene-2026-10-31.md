# On-node (ESP32) person inference and illustrative 3D scene — 31 October 2026

## On-node person inference (firmware `ares-node-0.3`)

Requested: run person detection on the ESP32 **alongside** the image, not instead of it, and show it
next to the laptop result.

| Item | Value |
|---|---|
| Model | TFLite Micro `person_detect` (int8, 96x96 grayscale, classes [no person, person]) |
| Source | `github.com/tensorflow/tflite-micro` `tensorflow/lite/micro/models/person_detect.tflite` |
| Licence | Apache-2.0 |
| Size / SHA-256 | 300,568 bytes, `808cfdfc0cf3a6fa6f6fa26bfa379ea97c16d5db7334637766e39c3408502e9d` |
| Firmware files | `edge_person.cpp/.h`, generated `person_detect_model.cpp/.h`, `build_opt.h` |
| Runtime | Arduino library `ESP_TF` 2.1.1 (TFLM with Espressif ESP-NN), built with `-DESP_NN -DCONFIG_NN_OPTIMIZED -DARCH_ESP32_S3` |
| Ops | AveragePool2D, Conv2D, DepthwiseConv2D, Reshape, Softmax |
| Tensor arena | 140 KB, internal RAM preferred, PSRAM fallback (reported in `/health`) |
| Input | Centre square crop of the 320x240 RGB565 frame (240x240), box-averaged to 96x96 luminance, quantised with the model's input parameters |
| Output | One person score per frame (no boxes, no count) |

Flow: `/capture` grabs a frame, runs the model on that exact frame, then JPEG-encodes and sends it.
The result travels on the same response as headers: `X-Ares-Person-Status`, `-Score`, `-Infer-Ms`,
`-Prep-Ms`, `-Model`. `/health` adds an `edge` object (status, arena location/used, runs, last
inference time). Boot prints the model's quantisation parameters and a first-frame score.

Backend: `state.edge_detection` (`inference_location: ESP32`, `output: PERSON_SCORE_ONLY`, provisional
threshold 0.5, `fused: false`). It is tied to the current frame's `frame_id`, withdrawn when the
camera is stale, and ignored on test-pattern frames. It is **not** added to fusion: it sees the same
camera frame as the laptop detector, so it is not an independent source. Older firmware reports
`NOT_REPORTED`. The ESP32 result is recorded with each `camera_frame` event.

Dashboard: two tiles under the image, **On ESP32 · TFLite Micro** (score bar, on-device ms) and
**On laptop · YOLOX-Nano** (count, best score, laptop ms), plus a dashed square on the image marking
the ESP32's crop.

Tests: 45 backend tests pass, including header parsing, frame matching, not-fused, and the
`NOT_REPORTED` / `UNAVAILABLE` (bad status or out-of-range score) / `TEST_PATTERN` states.

## Illustrative 3D scene

Three.js 0.170.0 (`three`, `@types/three`; installed with npm, 0 vulnerabilities reported).
`web/src/Scene3D.tsx`:

- Floor with the radar fan (1-6 m rings) and the camera's assumed ±25° field of view; the node at
  the origin.
- A generic figure (capsule + sphere), not a body reconstruction. It appears when the fused decision is
  `POSSIBLE_PERSON`, glides to new positions, pulses a ring, and fades to a grey "last seen" ghost for
  15 s after the decision drops.
- Placement: distance from the radar (moving distance if moving, else stationary); left/right from the
  best laptop box centre assuming a 50° lens; 2.5 m and "distance unknown" when the radar gives no range.
  Uncalibrated and labelled "Illustrative".
- Perspective / Overhead toggle with an animated camera; reduced-motion respected.

Browser check (1280 px): with the low-visibility profile briefly selected (radar target present,
camera none) the figure appeared at ≈ 2.4 m with the green label; overhead view showed it at ≈ 2.7 m
inside the camera wedge. Profile restored to clear afterwards. Bundle grows to ~740 KB (local serving).

## Hardware results (firmware `ares-node-0.3`)

First compile of the library took ~38 min (Arduino's sequential library detection over 226 files,
then compilation); later builds reuse the cache (75 s). Program 1,405,299 bytes (42% of 3.34 MB),
globals 66,760 bytes (20%). Uploaded over COM3, hash verified.

Boot log: arena in **internal RAM, 122,572 of 143,360 bytes used**; model input scale 0.00784, zero
point -1 (real range -1..1); output scale 0.00391, zero point -128. `/health` free heap dropped to
~56 KB with the arena allocated (Wi-Fi and HTTP ran normally during these checks).

Two bugs found and fixed on hardware:
1. **Input scaling:** the first build fed raw 0-255 luminance; the model expects pixel/127.5 - 1.
   Its first-frame score (0.383) was invalid. Fixed in `edge_person.cpp`.
2. **Missing headers:** the ESP32 HTTP server's default `max_resp_headers` is 8, so the score,
   timing and model headers were silently dropped after `X-Ares-Person-Status`. The backend correctly
   reported `UNAVAILABLE`. Raised to 16.

After the fixes, consecutive `/capture` responses: **inference 58-59 ms, preparation 24-25 ms** on
the ESP32-S3. With a person close in front of the camera (natural-colour frame), ESP32 scores were
0.52-0.90; the laptop detector found 1 person at 0.80-0.81, and fusion read `POSSIBLE_PERSON`. The
dashboard showed both tiles green ("Person · 58 ms on device" and "1 person · laptop"). One short
session, not an accuracy evaluation. Boot still reported D2 stuck low, while frames minutes later had
natural colour: the wire remains intermittent.

## Disaster-condition profiles

Added at the user's request (forwarded from the other session), from `docs/RESULTS_GUIDE.md`
section 4: `fire_no_smoke` 0.50/0.40/0.10, `fire_smoke` 0.10/0.80/0.10, `flood` 0.60/0.20/0.20,
`earthquake` 0.15/0.80/0.05 (camera/radar/IR), status `LITERATURE_PRIOR_UNCALIBRATED`; `clear` and
`reduced_visibility` unchanged (`PROVISIONAL_NOT_CALIBRATED`). While IR is synthetic the applied IR
weight is 0 and camera/radar are renormalised (ratio kept): e.g. earthquake applies 0.158/0.842,
fire with smoke 0.111/0.889. The API returns `prior_weights`, applied `weights` and an `ir_rule`
note; the dashboard shows a six-way condition picker and "IR x% prior, applied 0 (simulated)".
Selecting a condition never changes the synthetic IR scenario. Live check: earthquake and fire-with-
smoke fused camera/radar only with the expected weights; IR scenario stayed `baseline`; profile
restored to clear. 47 backend tests pass.
