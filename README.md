# ARES — current interactive demonstration

**Aerial Reconnaissance Emergency Support System:** an ESP32-S3/OV7670 camera node and laptop ground station. IR hardware is nonworking, so temperature values are explicitly synthetic. Radar is a separate app/web system, not connected to the ESP32.

Start with [TEAM_HANDOFF.md](TEAM_HANDOFF.md) for the original vision, decision history, component roles and verified implementation status. Follow [ACTION_PLAN.md](ACTION_PLAN.md) for the ordered phases, validation gates, evidence requirements and fallback decisions.

## Current status

- USB identification confirmed an ESP32-S3 with 8 MB flash and 8 MB embedded PSRAM. The camera working sketch compiles with the recorded settings.
- FastAPI, the React viewer, source-labelled recording/export and synthetic IR are implemented. A direct BLE connection authenticated and decoded 58 real radar reports; the backend subsequently streamed real radar into the dashboard.
- Camera runtime/address, person detection, calibrated fusion and the 3D scene remain pending. No automatic fused person result is fabricated while the detector is absent.
- The imminent camera setup is frontal and interactive; overhead aerial validation is deferred. LoRa, GPS, Raspberry Pi and multiple nodes are outside this demo.
- Operator-selected condition profiles are planned. Numerical weights require labelled development/validation trials and separate held-out evaluation.
- Synthetic IR retains persistent source labels and zero live human-presence weight. Actual radar reports are shown separately; presence-model/fusion calibration still require labelled real-data trials. RSSI/CSI and pose animation follow the core live pipeline.

See [ground-station setup](ground_station/README.md), [the source contract](docs/synthetic-ir-demo.md) and [backend validation](docs/validation/backend-2026-10-31.md). Use the project .venv and start-backend.cmd, then open http://127.0.0.1:8000. Build web/ first for a fresh checkout. No radar GPIO wiring or IR repair is required.

## Working firmware and setup

Use [firmware/ares_node/ares_node.ino](firmware/ares_node/ares_node.ino). Copy [wifi_secrets.example.h](firmware/ares_node/wifi_secrets.example.h) to `wifi_secrets.h` in that folder and edit the copy locally. Populated credentials, local CLI configuration, tool downloads and build outputs are ignored.

See [CLI setup](docs/setup/arduino-cli.md), [identified board settings](docs/hardware/board-config.md) and [camera compile validation](docs/validation/camera-build-2026-10-31.md). The [supplied circuit image](docs/hardware/wiring-2026-10-31.png) is historical: it includes excluded LoRa and radar wiring that does not describe the current separate radar setup.

The remaining design documents are [PLAN.md](PLAN.md) and [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md). Planned models, performance targets and illustrative 3D views must not be presented as measured execution, accuracy or reconstructed geometry.

## Historical simulation material

The existing `app.py`, `files/`, `output_figures/` and `ARES_Firmware/` material is retained as prior work. The simulation description below uses earlier component assumptions and synthetic results; it does not establish the current hardware's detection accuracy or deployment performance. Its old Streamlit viewer is not the planned React interface.

---

# Design of a Rapidly Deployable All-Terrain Communication and Human-Presence Detection System for Disaster Response
## Simulation & Testing Suite

**NMIT | Dept. of EEE | Guide: Ms. Smitha B**
**Authors:**
- ROHIT SONI - 1NT23EE044
- ROUNAK VYAS - 1NT23EE045
- SAMARTH G - 1NT23EE046
- JAYATEERTH P. - 1NT23EE022

---

## Overview

Since the physical prototype is in Phase-1 (proof-of-concept), this simulation suite
mathematically models all subsystems using real engineering formulas, producing plots
that directly back each test case in the project report.

---

## File Structure

```
project/
├── simulation.py             ← Main simulation (run this)
├── math_and_logic.md         ← All formulas, derivations, parameter justifications
├── implementation_notes.md   ← How to connect to real hardware in Phase-2
├── README.md                 ← This file
└── output_figures/
    ├── TC1_communication_link.png
    ├── TC2A_thermal_sensor.png
    ├── TC2B_acoustic_sensor.png
    ├── TC2C_rf_sensor.png
    ├── TC3_alert_fusion.png
    ├── Latency_pipeline.png
    └── Limitations_analysis.png
```

---

## Quick Start

```bash
# Install dependencies (one-time)
pip install numpy matplotlib scipy

# Run all simulations
python simulation.py
```

Output figures are saved to `./output_figures/`.

---

## What Each Simulation Does

### TC1 — Communication Link (FR1)
Models the LoRa radio link between the aerial node and ground station.
- **Plot 1:** Received signal power (dBm) vs horizontal distance at 4 altitudes.
  Shows where link is maintained and where it drops below the sensitivity floor.
- **Plot 2:** Link margin heatmap over altitude × distance space.
  Green = healthy link; red contour = link boundary.

### TC2-A — Thermal Sensor (FR2)
Models the MLX90640 IR sensor detecting human body heat.
- Inverse-square law propagation of 100W human heat emission.
- Detection using the 3σ rule over ambient IR background.
- **Plot 1:** Signal vs background with threshold line.
- **Plot 2:** SNR vs distance showing detection zone.

### TC2-B — Acoustic Sensor (FR2)
Models MEMS microphone detecting human voice in outdoor noise.
- SPL formula with geometric spreading.
- Background noise floor + required SNR margin.
- **Plot 1:** SPL vs distance with noise floor.
- **Plot 2:** SNR margin and detection zone.

### TC2-C — RF Signal Sensor (FR2)
Models Wi-Fi RSSI-based device scanning (detecting survivor's mobile phone).
- Log-distance path loss for open air vs disaster rubble environments.
- Sigmoid detection probability model.
- **Plot 1:** RSSI vs distance in two environments.
- **Plot 2:** Detection probability vs distance.

### TC3 — Alert Fusion & Logic (FR3)
Simulates 60 seconds of multi-sensor operation with a "person present" window.
- Weighted majority voting fusion (Thermal 40%, Acoustic 30%, RF 30%).
- Four alert levels: None / LOW / MEDIUM / HIGH.
- **Plot 1:** Per-second sensor flags.
- **Plot 2:** Fusion confidence score timeline.
- **Plot 3:** Alert level bar chart.
- **Plot 4:** Confusion matrix — Precision and Recall computed.

### Latency Pipeline
End-to-end delay from sensor trigger to ground station alert.
- Breaks down all 5 pipeline stages.
- Shows total latency vs LoRa Spreading Factor.
- All SF values (SF7–SF12) remain below the 500ms life-critical threshold.

### Limitations Analysis
Three engineering tradeoff analyses:
1. **Battery life** — tethered balloon vs drone platform.
2. **Detection accuracy** — degradation under environmental noise.
3. **Communication range** — terrain obstruction, mitigated by altitude.

---

## Dependencies

| Package    | Version  | Purpose                        |
|------------|----------|--------------------------------|
| numpy      | ≥ 1.21   | Numerical computation          |
| matplotlib | ≥ 3.5    | All plotting and visualisation |
| scipy      | ≥ 1.7    | (Available for Phase-2 extensions) |

---

## Notes for Phase-2

In Phase-2, replace the simulated data arrays with live sensor readings:
- `T_flag` ← MLX90640 frame data via I2C
- `A_flag` ← MEMS microphone via ADC/PDM on ESP32-S3
- `RF_flag` ← Wi-Fi scan RSSI via `esp_wifi_sta_get_ap_info()`
- LoRa transmission ← SX1276 via SPI

See `implementation_notes.md` for hardware-to-code mapping.
