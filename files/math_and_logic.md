# Math & Logic Reference — 22EEP69_02
## All Formulas, Parameter Derivations, and Calculation Basis

---

## TC1 — Communication Link Model

### Formula: Free-Space Path Loss (FSPL)

```
FSPL (dB) = 20·log₁₀(d) + 20·log₁₀(f) + 20·log₁₀(4π/c)
```

Where:
- `d` = 3D distance in metres = √(horizontal² + altitude²)
- `f` = 868 MHz (LoRa EU ISM band — matches SX1276 module used in PoC)
- `c` = 3 × 10⁸ m/s

### Received Power:

```
P_rx (dBm) = P_tx + G_tx + G_rx - FSPL
```

| Parameter       | Value    | Justification                                      |
|-----------------|----------|----------------------------------------------------|
| P_tx            | 20 dBm   | LoRa SX1276 maximum output power                   |
| G_tx            | 2 dBi    | Simple whip antenna on aerial node                 |
| G_rx            | 2 dBi    | Ground station antenna                             |
| Sensitivity     | −137 dBm | LoRa SF12, BW=125kHz — per SX1276 datasheet        |
| Frequency       | 868 MHz  | LoRa EU 863–870 MHz ISM band                       |

### Link Decision:
```
Link ACTIVE  ←→  P_rx > Sensitivity
Link MARGIN       = P_rx − Sensitivity   (positive = safe)
```

### Why FSPL is valid here:
The aerial node operates at 30–150m altitude in an open or semi-open disaster zone.
FSPL is the correct model for line-of-sight (LoS) radio propagation.
Obstruction effects are captured in the Limitations analysis with a separate terrain factor.

---

## TC2-A — Thermal Detection Model

### Formula: Inverse Square Law (Radiative Heat Transfer)

```
I(d) = P_human / (4π · d²)    [W/m²]
```

Where:
- `P_human` = 100 W  — total metabolic heat emission of a human body at rest
  (Stefan-Boltzmann: σ·ε·A·T⁴ with T=310K, ε=0.98, A=1.8m²  ≈ 100W)
- `d` = distance from sensor to human (m)

### Background and Threshold:

```
Background mean  μ_bg = 3 × 10⁻⁴  W/m²   (ambient IR floor, outdoor)
Background σ         = 5 × 10⁻⁵  W/m²   (natural thermal variation)
Detection threshold  = μ_bg + 3σ          (3-sigma rule, 99.7% confidence)
```

### SNR:
```
SNR (dB) = 10·log₁₀(I_signal / μ_bg)
Detection  ←→  SNR > 0 dB
```

### Sensor: MLX90640 (Melexis)
- Array: 32×24 pixels
- FOV: 55°×35°
- Thermal resolution: 0.1°C
- At 50m altitude, ground coverage cone ≈ 7m radius

---

## TC2-B — Acoustic Detection Model

### Formula: Sound Pressure Level with Geometric Spreading

```
SPL(d)  =  Lw  −  20·log₁₀(d)  −  11    [dB]
```

Where:
- `Lw` = 70 dB  — human voice sound power level (normal speech, ISO standard)
- `d`  = distance (m)
- `−11` = correction for free-field hemispherical radiation (point source)

### Detection Rule:
```
Background noise floor  = 40 dB   (moderate outdoor, post-disaster)
Required SNR margin     =  6 dB   (MEMS microphone standard: SNR > 6dB for detection)
Detection threshold     = 46 dB

Detection  ←→  SPL(d) > threshold
```

### Why 6 dB margin?
A 6 dB SNR gives approximately 75% detection probability for a single
microphone. In the fused system, acoustic is weighted 0.3 — even a weaker
detection contributes meaningfully when combined with thermal/RF.

### Sensor: MEMS microphone (built into Seeed XIAO ESP32-S3 Sense)
- Sensitivity: −26 dBFS
- SNR: 61 dB
- Frequency response: 50 Hz – 16 kHz (covers human speech 300 Hz – 3.4 kHz)

---

## TC2-C — RF Signal Detection Model

### Formula: Log-Distance Path Loss (LDPL)

```
RSSI(d)  =  A  −  10·n·log₁₀(d)    [dBm]
```

Where:
- `A` = −40 dBm  — reference RSSI measured at d = 1m (typical smartphone Wi-Fi)
- `n` = path loss exponent:

| Environment         | n value | Basis                          |
|---------------------|---------|-------------------------------|
| Open air / LoS      | 2.0     | Free-space theoretical value   |
| Indoor / office     | 2.5–3.0 | IEEE 802.11 standard tables    |
| Rubble / debris     | 3.2     | NIST disaster environment study|

### Detection Threshold:
```
Threshold = −80 dBm   (minimum usable Wi-Fi RSSI, IEEE 802.11 standard)
```

### Detection Probability (Sigmoid):
```
P_det(RSSI) = 1 / (1 + exp(−k · (RSSI − threshold)))
```
With `k = 0.3` (sharpness parameter), giving a soft transition from 0 to 1
probability around the threshold, modelling real-world scanning uncertainty.

---

## TC3 — Multi-Modal Fusion Logic

### Weighted Majority Voting:

```
Confidence = w_T · T_flag + w_A · A_flag + w_RF · RF_flag
```

| Sensor   | Weight | Justification                                                   |
|----------|--------|-----------------------------------------------------------------|
| Thermal  | 0.40   | Most reliable in darkness; not affected by noise; body-specific |
| Acoustic | 0.30   | Useful for conscious survivors; affected by wind/debris noise   |
| RF       | 0.30   | Passive detection of devices; higher false-positive rate        |

Weights sum to 1.0. Thermal is highest weight per sensor reliability literature
(Park et al., Sensors 2026 — referenced in Review 2 slides).

### Alert Level Mapping:

```
Confidence < 0.3   →  No alert         (log only)
0.3 ≤ C < 0.6      →  LOW alert        (log to ground station)
0.6 ≤ C < 0.9      →  MEDIUM alert     (transmit via LoRa)
C ≥ 0.9            →  HIGH/PRIORITY    (immediate LoRa burst)
```

### Performance Metrics:

```
Precision  = TP / (TP + FP)    — of all alerts sent, how many were correct
Recall     = TP / (TP + FN)    — of all actual presences, how many were caught
F1-score   = 2 × (P × R) / (P + R)
```

---

## Latency Pipeline Model

### Formula from Slide 10:

```
L_total = 1/f_sensor + C_model/P_MCU + Σ(t_overhead) + T_packet
```

### Component Breakdown:

| Component            | Formula                            | Value  | Basis                            |
|----------------------|------------------------------------|--------|----------------------------------|
| Sensor acquisition   | 1 / f_sensor = 1/30fps             | 33 ms  | MLX90640 max frame rate 30fps    |
| Edge AI inference    | C_model / P_MCU                    | 56 ms  | TFLite Micro on ESP32-S3 @ 240MHz|
| MCU serial/SPI       | t_overhead                         | 10 ms  | SPI @ 10 MHz, typical overhead   |
| LoRa Time-on-Air     | T_packet (see below)               | 80 ms  | SF7, BW=125kHz, 20-byte payload  |
| RF propagation       | altitude / c = 50 / 3×10⁸         | 0.17µs | Negligible                       |
| **Total**            |                                    |**179ms**| **< 500ms threshold ✓**         |

### LoRa Time-on-Air (ToA):

```
T_symbol  = 2^SF / BW
n_payload = 8 + max(⌈(8·PL − 4·SF + 28 + 16) / (4·SF)⌉ · (CR+4), 0)
ToA       = (n_preamble + 4.25 + n_payload) × T_symbol
```

Where:
- `SF` = Spreading Factor (7–12)
- `BW` = 125,000 Hz (125 kHz)
- `PL` = payload bytes = 20 (alert packet)
- `CR` = coding rate denominator = 1 (4/5 coding rate)

SF7 gives minimal ToA (~80ms) at the cost of shorter range.
SF12 gives maximum range (~2000m) but ToA ~2600ms — above threshold.
**Recommended: SF7 for close range (<500m), SF9 for extended range.**

---

## Limitations — Mathematical Basis

### 1. Battery Life:
```
T_operational = Capacity (Wh) / Power_draw (W)

Tethered balloon:   P = P_MCU + P_sensors + P_LoRa  ≈ 2.0 W
Drone-mounted:      P = P_hover + P_electronics      ≈ 82 W
```

At 55.5 Wh (3S 5000mAh LiPo):
- Balloon: ~27.75 hours of sensor operation
- Drone:   ~0.68 hours (~40 minutes) — dominated by hover power

### 2. Detection Accuracy vs Noise:
```
Acc(noise) = Acc_ideal × exp(−k · noise_level)
```
Where `noise_level` is normalized [0, 1] and `k` is sensor-specific:
- Thermal: k = 1.2 (robust, slower degradation)
- RF:      k = 1.8
- Acoustic: k = 2.5 (most sensitive to environmental noise)

### 3. Communication Range vs Terrain:
```
R_effective = R_free × exp(−2.3 × obstruction) × alt_bonus
alt_bonus   = 1 + 0.3 × log₁₀(altitude/10 + 1)
```
Higher altitude improves LoS probability, partially compensating terrain loss.
At 100m altitude, range in moderate rubble ≈ 480m (just above 500m minimum).

---

## Summary Table: All Parameters

| Parameter                 | Value         | Source                         |
|---------------------------|---------------|-------------------------------|
| LoRa frequency            | 868 MHz       | SX1276 datasheet               |
| LoRa Tx power             | 20 dBm        | SX1276 max                     |
| LoRa sensitivity (SF12)   | −137 dBm      | SX1276 datasheet               |
| Human heat emission       | 100 W         | Stefan-Boltzmann (37°C, 1.8m²) |
| Human voice Lw            | 70 dB         | ISO 9921                       |
| Outdoor noise floor       | 40 dB         | Standard acoustic reference    |
| WiFi reference RSSI@1m    | −40 dBm       | Empirical measurement          |
| Path loss exponent (open) | 2.0           | Theoretical free-space         |
| Path loss exponent (rubble)| 3.2          | NIST emergency comms study     |
| Detection threshold (WiFi)| −80 dBm       | IEEE 802.11 standard           |
| Fusion weight (thermal)   | 0.40          | Reliability ranking            |
| Fusion weight (acoustic)  | 0.30          | Reliability ranking            |
| Fusion weight (RF)        | 0.30          | Reliability ranking            |
| Total latency target      | < 500 ms      | Life-critical system standard  |
| Simulated total latency   | ~179 ms       | Computed pipeline sum          |
| Battery (LiPo)            | 3S 5000mAh    | Selected component             |
