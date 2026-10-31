# ARES — results guide for the paper and report

Updated: 31 October 2026. For teammates writing the conference paper and report.
Rule: report only measured values, say how they were measured, and keep MEASURED,
LITERATURE, SYNTHETIC and EMULATED numbers in separate columns or tables.

## 1. Where the numbers come from

| Source | Location | What is in it |
|---|---|---|
| Recorded sessions | `benchmarks/sessions/<id>/events.jsonl` + `manifest.json` | Every camera frame (JPEG + metadata), radar reports, detections, 1 Hz telemetry, config changes |
| Session download | Dashboard → "Download session JSONL" | Same as above |
| Node health | `http://ares.local/health` or `http://<ESP32-IP>/health` | Uptime, frames served, capture failures, RSSI, free heap/PSRAM |
| Frame headers | `X-Ares-Frame-Seq`, `X-Ares-Uptime-Ms`, `X-Ares-Rssi-Dbm` (+ `X-Ares-Person-*` once on-node inference lands) | Per-frame node values, stored in camera frame metadata |
| Validation notes | `docs/validation/*.md` | Build sizes, SCCB probe, detector timing, backend checks |
| Plan | `ACTION_PLAN.md` (phases 0–7, edge items E1–E4) | Status and pass criteria |

Each JSONL line is `{"event_id", "kind", "recorded_at_utc", "data"}`. Useful kinds:
`camera_frame`, `radar_report`, `detection`, `telemetry`, `profile_applied`, `ir_scenario`.
Load with pandas: `pd.read_json(path, lines=True)`, then `pd.json_normalize(df["data"])`.

## 2. Values already measured (31 October 2026)

| Value | Result | Status |
|---|---|---|
| ESP32-S3 flash / PSRAM | 8 MB / 8 MB (runtime PSRAM report 8,388,608 bytes) | MEASURED |
| Firmware ares-node-0.2 size | 1,030,775 B program (30%); 66,256 B globals (20%) | BUILD FIGURE, not runtime memory |
| Camera frame | 320×240 RGB565 = 153,600 B raw → ~27–30 KB JPEG (q80), ≈5.5× smaller | MEASURED (3 frames; repeat) |
| Frame fetch time | 0.27–0.46 s per frame (3 frames) | MEASURED (small sample; repeat) |
| Wi-Fi RSSI | −18 to −19 dBm at short range, channel 5, WPA2 | MEASURED |
| YOLOX-Nano on laptop | median 21.4 ms, p95 42.3 ms (one ESP32 frame) | MEASURED, see `docs/validation/detector-2026-10-31.md` |
| "Pi-5" profile | median 24.0 ms, p95 32.3 ms | EMULATED (4 threads on laptop) — never present as Pi data |
| Radar BLE | Authenticated; 58-report probe, then dashboard streaming | MEASURED (rate/accuracy still to do) |

Camera images are currently corrupted (data lines D2/D4 stuck low). **No accuracy
number may be computed until the wiring fix and a clean colour-bar test.**

## 3. Values to collect (and the chart for each)

| # | Measurement | How | Chart |
|---|---|---|---|
| 1 | Frame rate and frame age (median/p95) | 10-min session, from `camera_frame` timestamps | Histogram of frame age; line of fps over time |
| 2 | RSSI vs distance | `/health` at 1, 3, 5, 10 m | Line: RSSI vs distance |
| 3 | 1-hour reliability | Long session; count failures, reconnects, heap | Timeline of availability; heap over time |
| 4 | Radar distance error | Stand at taped marks 0.5–5 m | Scatter measured vs true + y=x; error bars |
| 5 | Radar detection table | Empty / walking / standing / sitting trials | Confusion matrix |
| 6 | Detector precision/recall | Labelled held-out frames, per condition | PR curve; grouped bars per condition |
| 7 | Camera vs radar vs fused | Synchronised sessions, held-out test | Grouped bar: recall & false alerts per condition |
| 8 | Edge latency (E3) | Stage timestamps | Stacked bar of pipeline stages; box plot ESP32 vs laptop |
| 9 | Bandwidth saving (E1) | Bytes/min always-send vs event-triggered | Bar chart, log scale |
| 10 | Radar filtering (E2) | Raw vs filtered on same data | Before/after error + false alerts/hour |
| 11 | Offline buffering (E4) | Timed Wi-Fi outages | Events kept vs lost per outage length |

Always report trial counts, participants, session counts and unavailable time.

## 4. Disaster conditions and sensor weights

We cannot run real fires, floods or collapses. The paper should therefore separate:

1. **Literature-informed prior weights** (below) — justified by cited physics/studies.
2. **Lab-proxy experiments** we actually run (section 5).
3. **Calibrated weights** — only for conditions where we collect our own data (Phase 5).

Sensors here: camera = OV7670 visible; radar = 24 GHz presence/distance (HLK);
IR = MLX90614 single-spot thermometer (currently SYNTHETIC). Thermal-camera papers do
**not** transfer directly to a single-spot thermometer: it has no image and cannot localise
a person. While IR is synthetic its live weight stays 0.

| Condition | Camera | Radar | IR (if real) | Reasoning (cite) |
|---|---|---|---|---|
| Clear, daylight | 0.70 | 0.30 | 0.00 | Camera gives location and identity; radar adds motion/presence. |
| Fire, no smoke | 0.50 | 0.40 | 0.10 | Hot background confounds temperature (fire = warm everywhere), so IR low; camera still sees. |
| Fire, with smoke | 0.10 | 0.80 | 0.10 | Visible cameras fail in dense smoke; radar and thermal imaging remain usable [1][2][3][4]. Our IR is a spot thermometer, so it stays low. |
| Flood | 0.60 | 0.20 | 0.20 | Water surfaces cause radar reflection/multipath clutter [3]; victims are partly submerged so camera detection drops sharply (39% vs 91% mAP) [6]; thermal contrast against cold water helps if a thermal camera is used [7]. |
| Earthquake / rubble | 0.15 | 0.80 | 0.05 | Occluded victims are invisible to cameras; radar detects breathing micro-motion through debris [5][8][9]. Our 24 GHz presence module is not a bio-radar, so claim "presence through light occlusion" only. |

These are **PRIORS, not calibrated values**. In the dashboard and paper, label them
"literature-informed, uncalibrated". Weights must be non-negative and sum to 1. The
backend currently ships only `clear` (0.7/0.3/0) and `reduced_visibility` (0.2/0.8/0);
adding the other profiles is a backend change (owner: the ground-station session).

## 5. How to show each condition without a real disaster

| Condition | Lab proxy we can run | What it validates | What it does NOT validate |
|---|---|---|---|
| Smoke | Translucent sheet / frosted plastic over the camera only; optionally a fog machine if venue allows | Camera degradation and radar fallback | Real smoke density, heat |
| Fire (no smoke) | Warm objects (heater, hot mug) in scene + synthetic IR "hot_background" | Fusion logic with confounding heat (synthetic IR is labelled) | Real fire temperatures |
| Rubble | Person behind cardboard/plywood/blanket; stationary and breathing | Radar presence with camera occluded | Concrete rubble attenuation, depth |
| Flood | Literature + replay of public images (e.g. FloodNet, RGB aerial) through the detector; operator selects "flood" profile | Profile switching and detector behaviour on flood imagery | Live flood detection, water radar clutter |

Write proxies in the paper as "laboratory proxy", never as the disaster itself.

## 6. Interactive things visitors can do (now / soon)

Now:
- Walk in and out; watch radar state and distance change live.
- Stand still vs move — moving vs stationary radar target.
- Cover the camera with a sheet → switch profile to reduced visibility → radar carries the assessment.
- Pick a synthetic IR scenario (baseline / warm target / hot background) and see it labelled SYNTHETIC.
- Record a session and download the JSONL.
- Toggle the camera test pattern (`/colorbar?on=1`) to show the image pipeline.

Being built (other session): person boxes from YOLOX; ESP32 on-node person score shown beside it
(ESP32 vs LAPTOP); laptop vs "Pi-5 constrained" timing; 3D avatar with overhead/perspective toggle.
Planned (E1–E4): privacy mode, event-triggered sending with a live bandwidth counter, radar
filter on/off, unplug Wi-Fi and watch buffered events arrive on reconnect.

## 7. Do not report as results

Synthetic IR values; provisional or literature weights as if calibrated; emulated Pi timings as
Pi timings; any accuracy from the current corrupted frames; real smoke/fire/flood/rubble performance;
GPS/LoRa/multi-node or overhead-drone performance.

## References

1. Kulhandjian et al., human detection in smoke with IR camera + micro-Doppler radar, IEEE RadarConf 2023. https://zimmer.fresnostate.edu/~hkulhandjian/papers/Kulhandjian_Human_Detection_RardarConf_2023.pdf
2. Ladstaedter et al., multi-sensor (RGB, thermal, LiDAR, 77 GHz radar) hot-smoke tunnel experiment, 2023. https://www.milak.at/fileadmin/milak/InstOWB/UOET/_UOET23_Proceedings/2023_LADSTAEDTER_etal_Multi_Sensor_Experiment_final.pdf
3. Robust human detection under visual degradation via thermal and mmWave radar fusion, arXiv 2307.03623 (EWSN 2023). https://arxiv.org/abs/2307.03623
4. Stereo thermal IR + FMCW radar for firefighting robots in smoke (distance error 1–19% → 1–2% with fusion). https://link.springer.com/article/10.1007/s10694-013-0356-3
5. Shi et al., automatic life detection with ground-penetrating rescue radar, Sensors 2023, DOI 10.3390/s23156771. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10422524/
6. Ummah et al., deep learning aerial flood victim detection. https://avia.ftmd.itb.ac.id/index.php/jav/article/view/73
7. Nasim & Ramaraju, flood survivors via aerial radiometric thermal imaging, IJITEE. https://www.ijitee.org/wp-content/uploads/papers/v8i9/I8135078919.pdf
8. Doppler radar for detecting living people under debris (review), Sensors 2019. https://doaj.org/article/393e5dc327b248279b30e3d85402fd7d
9. MIT Lincoln Laboratory, MURMUR — motion under rubble measured using radar. https://www.ll.mit.edu/partner-us/available-technologies/motion-under-rubble-measured-using-radar-murmur
10. FloodNet aerial post-flood dataset. https://github.com/BinaLab/FloodNet-Supervised_v1.0
11. SmokeBot EU project (radar, thermal, gas in low visibility). https://cordis.europa.eu/project/id/645101

Verify each reference's full text before citing a specific number; several entries above were read
from abstracts or snippets only.
