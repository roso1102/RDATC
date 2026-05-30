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
