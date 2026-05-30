"""
=============================================================================
PROJECT: Rapidly Deployable All-Terrain Communication and
         Human-Presence Detection System for Disaster Response
PROJECT ID: 22EEP69_02
NMIT, Dept. of EEE

SIMULATION FILE: simulation.py
Description:
    Simulates TC1 (Communication Link), TC2 (Sensor Detection — Thermal,
    Acoustic, RF), TC3 (Alert Fusion), Latency Pipeline, and Limitations.

Run: python simulation.py
Outputs: 6 PNG figures saved to ./output_figures/
=============================================================================
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyArrowPatch
import os

# ── Output folder ────────────────────────────────────────────────────────────
os.makedirs("output_figures", exist_ok=True)

# ── Global Style ─────────────────────────────────────────────────────────────
plt.rcParams.update({
    'figure.facecolor': '#0d1117',
    'axes.facecolor':   '#161b22',
    'axes.edgecolor':   '#30363d',
    'axes.labelcolor':  '#e6edf3',
    'xtick.color':      '#8b949e',
    'ytick.color':      '#8b949e',
    'text.color':       '#e6edf3',
    'grid.color':       '#21262d',
    'grid.linestyle':   '--',
    'grid.alpha':       0.6,
    'font.family':      'monospace',
    'axes.titlesize':   13,
    'axes.labelsize':   11,
})

TEAL    = '#00d4aa'
ORANGE  = '#ff7b2c'
BLUE    = '#3d9bff'
RED     = '#ff4757'
YELLOW  = '#ffd700'
PURPLE  = '#b48eff'
GREEN   = '#4ade80'
GRAY    = '#8b949e'

# =============================================================================
# TC1 — COMMUNICATION LINK (LoRa Free-Space Path Loss)
# =============================================================================
def simulate_tc1():
    """
    Model: Free-Space Path Loss (FSPL)
    FSPL(dB) = 20*log10(d) + 20*log10(f) + 20*log10(4π/c)

    LoRa Link Budget:
        Tx Power      = 20 dBm
        Antenna Gain  = 2 dBi (each end)
        Sensitivity   = -137 dBm (LoRa SF12)
        Frequency     = 868 MHz (LoRa EU band)

    Received Power:
        Prx = Ptx + Gtx + Grx - FSPL
    Link is ACTIVE if Prx > Sensitivity threshold.
    """
    f   = 868e6          # Hz  — LoRa 868 MHz
    c   = 3e8            # m/s
    Ptx = 20             # dBm  — LoRa SX1276 max Tx power
    Gtx = 2              # dBi
    Grx = 2              # dBi
    sensitivity = -137   # dBm  — LoRa SF12 sensitivity

    altitudes  = [30, 50, 100, 150]          # metres (drone height)
    h_dist     = np.linspace(1, 3000, 500)   # horizontal distance (m)

    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    fig.suptitle("TC1 — LoRa Communication Link Simulation\n"
                 "Frequency: 868 MHz | Tx Power: 20 dBm | SF12 Sensitivity: −137 dBm",
                 fontsize=13, color=TEAL, y=1.02)

    colors = [TEAL, BLUE, ORANGE, PURPLE]

    # --- Plot 1: Received Power vs Horizontal Distance ---
    ax1 = axes[0]
    for i, alt in enumerate(altitudes):
        d3d  = np.sqrt(h_dist**2 + alt**2)
        FSPL = 20*np.log10(d3d) + 20*np.log10(f) + 20*np.log10(4*np.pi/c)
        Prx  = Ptx + Gtx + Grx - FSPL
        ax1.plot(h_dist, Prx, color=colors[i], lw=2, label=f"Alt = {alt}m")

    ax1.axhline(sensitivity, color=RED, lw=2, ls='--', label=f"Sensitivity ({sensitivity} dBm)")
    ax1.fill_between(h_dist, sensitivity, -160,
                     alpha=0.12, color=RED, label="Link LOST zone")
    ax1.fill_between(h_dist, sensitivity, 0,
                     where=np.ones_like(h_dist, dtype=bool),
                     alpha=0.04, color=GREEN)
    ax1.set_xlabel("Horizontal Distance (m)")
    ax1.set_ylabel("Received Signal Power (dBm)")
    ax1.set_title("Received Power vs Distance")
    ax1.legend(fontsize=9)
    ax1.grid(True)
    ax1.set_ylim(-165, -60)

    # Annotate max range at 50m altitude
    alt = 50
    d3d  = np.sqrt(h_dist**2 + alt**2)
    FSPL = 20*np.log10(d3d) + 20*np.log10(f) + 20*np.log10(4*np.pi/c)
    Prx  = Ptx + Gtx + Grx - FSPL
    crossings = np.where(np.diff(np.sign(Prx - sensitivity)))[0]
    if len(crossings):
        max_range = h_dist[crossings[0]]
        ax1.annotate(f"Max range ≈ {max_range:.0f}m\n(Alt=50m)",
                     xy=(max_range, sensitivity),
                     xytext=(max_range-700, sensitivity+15),
                     arrowprops=dict(arrowstyle='->', color=YELLOW),
                     color=YELLOW, fontsize=9)

    # --- Plot 2: Link Quality Heatmap ---
    ax2 = axes[1]
    h_range = np.linspace(10, 2500, 200)
    alts    = np.linspace(10, 200, 200)
    H, A    = np.meshgrid(h_range, alts)
    D3D     = np.sqrt(H**2 + A**2)
    FSPL2D  = 20*np.log10(D3D) + 20*np.log10(f) + 20*np.log10(4*np.pi/c)
    Prx2D   = Ptx + Gtx + Grx - FSPL2D
    margin  = Prx2D - sensitivity   # link margin (positive = OK)

    cmap = plt.cm.RdYlGn
    im = ax2.contourf(H, A, margin, levels=20, cmap=cmap, alpha=0.9)
    ax2.contour(H, A, margin, levels=[0], colors=[RED], linewidths=2)
    cbar = fig.colorbar(im, ax=ax2)
    cbar.set_label("Link Margin (dB)", color='#e6edf3')
    cbar.ax.yaxis.set_tick_params(color='#e6edf3')
    ax2.set_xlabel("Horizontal Distance (m)")
    ax2.set_ylabel("Drone Altitude (m)")
    ax2.set_title("Link Margin Heatmap\n(Red contour = Link Boundary)")
    ax2.plot([], [], color=RED, lw=2, label="Link boundary")
    ax2.legend(fontsize=9)

    plt.tight_layout()
    plt.savefig("output_figures/TC1_communication_link.png",
                dpi=150, bbox_inches='tight', facecolor='#0d1117')
    plt.close()
    print("[TC1] Communication link simulation saved.")


# =============================================================================
# TC2 — SENSOR DETECTION (Thermal, Acoustic, RF)
# =============================================================================
def simulate_tc2_thermal():
    """
    Model: Inverse Square Law for IR radiation intensity
        I(d) = P / (4 * π * d²)  [W/m²]

    Human heat: ~100W (Stefan-Boltzmann, 37°C body)
    Ambient background: 3e-4 W/m² with Gaussian noise σ = 5e-5
    Detection: I > background_mean + 3σ
    MLX90640 sensor: range ~7m at 50m altitude (cone angle ~8°)
    """
    np.random.seed(42)
    P_human   = 100          # W  — human body heat emission
    distances = np.linspace(0.5, 25, 400)

    I_signal  = P_human / (4 * np.pi * distances**2)   # W/m²
    bg_mean   = 3e-4         # W/m²  — ambient IR floor
    bg_sigma  = 5e-5
    noise     = np.random.normal(0, bg_sigma, len(distances))
    I_bg      = bg_mean + noise
    threshold = bg_mean + 3 * bg_sigma                  # 3σ detection rule

    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    fig.suptitle("TC2-A — Thermal Sensor Simulation (MLX90640)\n"
                 "Human heat: 100W | Inverse-square propagation | 3σ detection rule",
                 fontsize=13, color=ORANGE)

    # Plot 1: Signal vs distance
    ax1 = axes[0]
    ax1.semilogy(distances, I_signal, color=ORANGE, lw=2.5, label="Human IR signal")
    ax1.semilogy(distances, I_bg,     color=GRAY,   lw=1.5, alpha=0.7, label="Background noise")
    ax1.axhline(threshold, color=RED, lw=2, ls='--',
                label=f"Detection threshold (3σ = {threshold:.2e} W/m²)")
    detected = I_signal > threshold
    if np.any(detected):
        det_range = distances[detected][-1]
        ax1.axvline(det_range, color=GREEN, lw=2, ls=':',
                    label=f"Max detection: {det_range:.1f}m")
    ax1.set_xlabel("Sensor-to-Target Distance (m)")
    ax1.set_ylabel("IR Intensity (W/m²) — log scale")
    ax1.set_title("IR Intensity vs Distance")
    ax1.legend(fontsize=9)
    ax1.grid(True)

    # Plot 2: SNR vs distance
    ax2 = axes[1]
    SNR_dB = 10 * np.log10(I_signal / (bg_mean + 1e-10))
    ax2.plot(distances, SNR_dB, color=ORANGE, lw=2.5)
    ax2.axhline(0, color=RED, lw=2, ls='--', label="SNR = 0 dB (detection floor)")
    ax2.fill_between(distances, SNR_dB, 0,
                     where=(SNR_dB > 0), alpha=0.2, color=GREEN, label="Detection zone")
    ax2.fill_between(distances, SNR_dB, 0,
                     where=(SNR_dB <= 0), alpha=0.2, color=RED, label="Below threshold")
    ax2.set_xlabel("Distance (m)")
    ax2.set_ylabel("Signal-to-Noise Ratio (dB)")
    ax2.set_title("Thermal SNR vs Distance")
    ax2.legend(fontsize=9)
    ax2.grid(True)

    plt.tight_layout()
    plt.savefig("output_figures/TC2A_thermal_sensor.png",
                dpi=150, bbox_inches='tight', facecolor='#0d1117')
    plt.close()
    print("[TC2-A] Thermal sensor simulation saved.")


def simulate_tc2_acoustic():
    """
    Model: Sound Pressure Level (SPL) with geometric spreading
        SPL(d) = Lw - 20*log10(d) - 11  [dB]

    Human voice Lw ≈ 70 dB (sound power level)
    Background noise floor: 40 dB (moderate outdoor)
    Detection margin needed: 6 dB SNR
    MEMS microphone floor: -26 dBFS ≈ 30 dB SPL
    """
    Lw        = 70           # dB  — human voice sound power level
    bg_noise  = 40           # dB  — outdoor ambient SPL
    margin    = 6            # dB  — required SNR margin
    threshold = bg_noise + margin

    distances = np.linspace(0.5, 50, 400)
    SPL       = Lw - 20 * np.log10(distances) - 11

    np.random.seed(7)
    noise     = np.random.normal(0, 1.5, len(distances))   # ±1.5 dB variation

    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    fig.suptitle("TC2-B — Acoustic Sensor Simulation (MEMS Microphone)\n"
                 "Human voice Lw=70dB | Outdoor noise floor=40dB | Required margin=6dB",
                 fontsize=13, color=BLUE)

    ax1 = axes[0]
    ax1.plot(distances, SPL + noise, color=BLUE,  lw=2.5, label="Received SPL (with noise)")
    ax1.plot(distances, SPL,         color=PURPLE, lw=1.5, ls='--', alpha=0.7, label="Theoretical SPL")
    ax1.axhline(threshold, color=RED, lw=2, ls='--',
                label=f"Detection threshold ({threshold} dB)")
    ax1.axhline(bg_noise,  color=GRAY, lw=1.5, ls=':',
                label=f"Noise floor ({bg_noise} dB)")

    cross_idx = np.where(SPL < threshold)[0]
    if len(cross_idx):
        det_range = distances[cross_idx[0]]
        ax1.axvline(det_range, color=GREEN, lw=2, ls=':',
                    label=f"Max detection: {det_range:.1f}m")

    ax1.set_xlabel("Distance (m)")
    ax1.set_ylabel("Sound Pressure Level (dB)")
    ax1.set_title("SPL vs Distance")
    ax1.legend(fontsize=9)
    ax1.grid(True)

    # Plot 2: SNR margin
    ax2 = axes[1]
    SNR = SPL - bg_noise
    ax2.plot(distances, SNR, color=BLUE, lw=2.5, label="Acoustic SNR")
    ax2.axhline(margin, color=RED, lw=2, ls='--',
                label=f"Min required SNR ({margin} dB)")
    ax2.fill_between(distances, SNR, margin,
                     where=(SNR >= margin), alpha=0.2, color=GREEN, label="Detection zone")
    ax2.fill_between(distances, SNR, margin,
                     where=(SNR < margin), alpha=0.2, color=RED, label="Below threshold")
    ax2.set_xlabel("Distance (m)")
    ax2.set_ylabel("SNR (dB)")
    ax2.set_title("Acoustic SNR vs Distance")
    ax2.legend(fontsize=9)
    ax2.grid(True)

    plt.tight_layout()
    plt.savefig("output_figures/TC2B_acoustic_sensor.png",
                dpi=150, bbox_inches='tight', facecolor='#0d1117')
    plt.close()
    print("[TC2-B] Acoustic sensor simulation saved.")


def simulate_tc2_rf():
    """
    Model: Log-Distance Path Loss (LDPL) for WiFi/BT RSSI
        RSSI(d) = A - 10*n*log10(d)

    A  = RSSI at 1m reference = -40 dBm (typical BT/WiFi)
    n  = path loss exponent = 2.7 (semi-open / disaster rubble)
    Detection threshold = -80 dBm (WiFi scan minimum)

    Environmental penalty: +10 dB attenuation for rubble/debris
    """
    A           = -40      # dBm  — reference RSSI at 1m
    n_open      = 2.0      # path loss exponent — open air
    n_debris    = 3.2      # path loss exponent — rubble/debris
    threshold   = -80      # dBm  — detection threshold

    distances = np.linspace(1, 100, 400)
    RSSI_open   = A - 10 * n_open   * np.log10(distances)
    RSSI_debris = A - 10 * n_debris * np.log10(distances)

    np.random.seed(99)
    shadow_open   = np.random.normal(0, 3, len(distances))
    shadow_debris = np.random.normal(0, 5, len(distances))

    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    fig.suptitle("TC2-C — RF Signal Sensor Simulation (Wi-Fi RSSI Scanning)\n"
                 "Reference RSSI@1m: −40 dBm | n_open=2.0, n_debris=3.2 | Threshold: −80 dBm",
                 fontsize=13, color=TEAL)

    ax1 = axes[0]
    ax1.plot(distances, RSSI_open   + shadow_open,   color=TEAL,   lw=2.5,
             label="Open air (n=2.0)")
    ax1.plot(distances, RSSI_debris + shadow_debris, color=ORANGE, lw=2.5,
             label="Debris/rubble (n=3.2)")
    ax1.axhline(threshold, color=RED, lw=2, ls='--',
                label=f"Detection limit ({threshold} dBm)")

    for rssi, col, label in [(RSSI_open, TEAL, "open"), (RSSI_debris, ORANGE, "debris")]:
        idx = np.where(rssi < threshold)[0]
        if len(idx):
            ax1.axvline(distances[idx[0]], color=col, lw=1.5, ls=':',
                        label=f"Max range ({label}): {distances[idx[0]]:.0f}m")

    ax1.set_xlabel("Distance (m)")
    ax1.set_ylabel("RSSI (dBm)")
    ax1.set_title("RSSI vs Distance — Environment Comparison")
    ax1.legend(fontsize=9)
    ax1.grid(True)

    # Plot 2: Detection probability (sigmoid model)
    ax2 = axes[1]
    def det_prob(rssi, thr=-80, k=0.3):
        return 1 / (1 + np.exp(-k * (rssi - thr)))

    Pdet_open   = det_prob(RSSI_open)
    Pdet_debris = det_prob(RSSI_debris)
    ax2.plot(distances, Pdet_open,   color=TEAL,   lw=2.5, label="Open air")
    ax2.plot(distances, Pdet_debris, color=ORANGE, lw=2.5, label="Debris/rubble")
    ax2.axhline(0.5, color=RED, lw=1.5, ls='--', label="50% detection probability")
    ax2.set_xlabel("Distance (m)")
    ax2.set_ylabel("Detection Probability")
    ax2.set_title("RF Detection Probability vs Distance")
    ax2.set_ylim(0, 1.05)
    ax2.legend(fontsize=9)
    ax2.grid(True)

    plt.tight_layout()
    plt.savefig("output_figures/TC2C_rf_sensor.png",
                dpi=150, bbox_inches='tight', facecolor='#0d1117')
    plt.close()
    print("[TC2-C] RF sensor simulation saved.")


# =============================================================================
# TC3 — MULTI-MODAL FUSION & ALERT LOGIC
# =============================================================================
def simulate_tc3():
    """
    Fusion Rule (Weighted Majority Voting):
        confidence = w_T * T_flag + w_A * A_flag + w_RF * RF_flag
        w_T=0.4, w_A=0.3, w_RF=0.3 (thermal most reliable)

    Alert levels:
        confidence < 0.3  → No alert
        0.3 ≤ confidence < 0.6 → LOW alert (log only)
        0.6 ≤ confidence < 0.9 → MEDIUM alert (transmit)
        confidence ≥ 0.9        → HIGH alert (priority transmit)

    Simulated over 60 time steps (1 per second).
    """
    np.random.seed(21)
    t = np.arange(60)  # 60 seconds

    # Simulate sensor flags (binary detect/not-detect per second)
    # Presence event: t=15 to t=45 (person detected in zone)
    def sensor_stream(presence_start, presence_end, det_prob_on, det_prob_off, n):
        flags = np.zeros(n)
        for i in range(n):
            if presence_start <= i <= presence_end:
                flags[i] = 1 if np.random.rand() < det_prob_on else 0
            else:
                flags[i] = 1 if np.random.rand() < det_prob_off else 0
        return flags

    T_flag  = sensor_stream(15, 45, 0.90, 0.05, 60)   # thermal: high accuracy
    A_flag  = sensor_stream(18, 42, 0.75, 0.10, 60)   # acoustic: moderate
    RF_flag = sensor_stream(10, 50, 0.80, 0.15, 60)   # RF: wider range, more FP

    w_T, w_A, w_RF = 0.4, 0.3, 0.3
    confidence = w_T * T_flag + w_A * A_flag + w_RF * RF_flag

    alert_level = np.zeros(60)    # 0=none, 1=low, 2=medium, 3=high
    alert_level[confidence >= 0.3] = 1
    alert_level[confidence >= 0.6] = 2
    alert_level[confidence >= 0.9] = 3

    fig = plt.figure(figsize=(16, 10))
    fig.suptitle("TC3 — Multi-Modal Fusion & Alert System Simulation\n"
                 "Weights: Thermal=0.4, Acoustic=0.3, RF=0.3 | 60-second timeline",
                 fontsize=13, color=YELLOW)

    gs = gridspec.GridSpec(3, 2, figure=fig, hspace=0.45, wspace=0.35)

    # --- Sensor flags ---
    ax1 = fig.add_subplot(gs[0, :])
    ax1.step(t, T_flag  + 0.1, color=ORANGE, lw=2, label="Thermal",  where='post')
    ax1.step(t, A_flag  + 2.2, color=BLUE,   lw=2, label="Acoustic", where='post')
    ax1.step(t, RF_flag + 4.3, color=TEAL,   lw=2, label="RF/WiFi",  where='post')
    ax1.axvspan(15, 45, alpha=0.08, color=GREEN, label="True presence window")
    ax1.set_yticks([0.6, 2.7, 4.8])
    ax1.set_yticklabels(["Thermal", "Acoustic", "RF"])
    ax1.set_xlabel("Time (s)")
    ax1.set_title("Sensor Detection Flags over Time")
    ax1.legend(loc='upper right', fontsize=9)
    ax1.grid(True)
    ax1.set_ylim(-0.2, 5.8)

    # --- Fusion confidence ---
    ax2 = fig.add_subplot(gs[1, :])
    ax2.fill_between(t, confidence, alpha=0.25, color=YELLOW)
    ax2.plot(t, confidence, color=YELLOW, lw=2.5, label="Fusion confidence")
    ax2.axhline(0.3, color=GRAY,   lw=1.5, ls='--', label="Low alert (0.3)")
    ax2.axhline(0.6, color=ORANGE, lw=1.5, ls='--', label="Medium alert (0.6)")
    ax2.axhline(0.9, color=RED,    lw=1.5, ls='--', label="High alert (0.9)")
    ax2.axvspan(15, 45, alpha=0.08, color=GREEN)
    ax2.set_ylabel("Confidence Score")
    ax2.set_xlabel("Time (s)")
    ax2.set_title("Weighted Fusion Confidence Score")
    ax2.legend(fontsize=9, loc='upper right')
    ax2.set_ylim(-0.05, 1.15)
    ax2.grid(True)

    # --- Alert level bar ---
    ax3 = fig.add_subplot(gs[2, 0])
    colors_map = {0: GRAY, 1: BLUE, 2: ORANGE, 3: RED}
    bar_colors = [colors_map[int(a)] for a in alert_level]
    ax3.bar(t, alert_level + 0.05, color=bar_colors, width=0.8)
    ax3.set_yticks([0, 1, 2, 3])
    ax3.set_yticklabels(["None", "LOW", "MEDIUM", "HIGH"])
    ax3.set_xlabel("Time (s)")
    ax3.set_title("Alert Level per Second")
    handles = [mpatches.Patch(color=GRAY,   label="No Alert"),
               mpatches.Patch(color=BLUE,   label="LOW"),
               mpatches.Patch(color=ORANGE, label="MEDIUM"),
               mpatches.Patch(color=RED,    label="HIGH")]
    ax3.legend(handles=handles, fontsize=8)
    ax3.grid(True, axis='y')

    # --- Confusion matrix style summary ---
    ax4 = fig.add_subplot(gs[2, 1])
    true_presence = (t >= 15) & (t <= 45)
    detected      = alert_level >= 2    # medium or high = "alert transmitted"

    TP = np.sum( true_presence  &  detected)
    FP = np.sum(~true_presence  &  detected)
    TN = np.sum(~true_presence  & ~detected)
    FN = np.sum( true_presence  & ~detected)

    matrix = np.array([[TP, FP], [FN, TN]])
    labels = [["TP", "FP"], ["FN", "TN"]]
    im = ax4.imshow(matrix, cmap='RdYlGn', vmin=0, vmax=35)
    for i in range(2):
        for j in range(2):
            ax4.text(j, i, f"{labels[i][j]}\n{matrix[i,j]}",
                     ha='center', va='center', fontsize=14,
                     color='black', fontweight='bold')
    ax4.set_xticks([0, 1])
    ax4.set_yticks([0, 1])
    ax4.set_xticklabels(["Alert Sent", "No Alert"])
    ax4.set_yticklabels(["Person Present", "No Person"])
    ax4.set_title(f"Detection Summary\nPrecision={TP/(TP+FP+1e-9):.2f}  Recall={TP/(TP+FN+1e-9):.2f}")
    fig.colorbar(im, ax=ax4, fraction=0.04)

    plt.savefig("output_figures/TC3_alert_fusion.png",
                dpi=150, bbox_inches='tight', facecolor='#0d1117')
    plt.close()
    print("[TC3] Alert fusion simulation saved.")


# =============================================================================
# LATENCY PIPELINE (from slide 10)
# =============================================================================
def simulate_latency():
    """
    End-to-end latency model from slide 10:
    L_total = 1/f_sensor + C_model/P_MCU + Σ(t_overhead) + T_packet

    Breakdown:
        Sensor acquisition   = 1/30fps         ≈ 33 ms
        Edge AI inference    = C_model/P_MCU   ≈ 56 ms  (TFLite Micro on ESP32-S3)
        MCU serial/SPI       = overhead        ≈ 10 ms
        LoRa Time-on-Air     = ToA @ SF7       ≈ 80 ms
        RF propagation       = alt/c           ≈ 0.17 µs (negligible)

    Total ≈ 179 ms  (target < 500 ms)

    We also vary SF (Spreading Factor) to show its effect on ToA.
    """
    # LoRa ToA formula: T_s = 2^SF / BW
    BW      = 125e3     # Hz
    payload = 20        # bytes
    preamble_symbols = 8

    def lora_toa_ms(SF):
        T_s = (2**SF) / BW * 1000    # ms per symbol
        # Payload symbols (simplified Semtech formula)
        n_payload = 8 + max(np.ceil((8*payload - 4*SF + 28 + 16) /
                                    (4*(SF))) * (1), 0)
        return (preamble_symbols + 4.25 + n_payload) * T_s

    SFs   = np.arange(7, 13)
    ToAs  = np.array([lora_toa_ms(sf) for sf in SFs])

    # Fixed components
    t_sensor  = 33    # ms
    t_edge_ai = 56    # ms
    t_mcu     = 10    # ms
    t_prop    = 0.00017  # ms (negligible)

    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    fig.suptitle("End-to-End Latency Pipeline Simulation\n"
                 "L_total = 1/f_sensor + C_model/P_MCU + Σ(t_overhead) + T_packet",
                 fontsize=13, color=PURPLE)

    # Plot 1: Stacked bar at SF7 (nominal) with all components
    ax1 = axes[0]
    components = ['Sensor\nAcquisition', 'Edge AI\nInference\n(TFLite)', 'MCU\nOverhead',
                  'LoRa\nTime-on-Air\n(SF7)', 'RF\nPropagation']
    values     = [t_sensor, t_edge_ai, t_mcu, lora_toa_ms(7), t_prop]
    bar_colors = [TEAL, PURPLE, BLUE, ORANGE, GRAY]

    bars = ax1.bar(components, values, color=bar_colors, edgecolor='#0d1117', lw=1.5)
    for bar, val in zip(bars, values):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                 f'{val:.1f}ms', ha='center', color='white', fontsize=10, fontweight='bold')

    total = sum(values)
    ax1.axhline(500, color=RED, lw=2, ls='--', label="Threshold: 500ms")
    ax1.axhline(total, color=GREEN, lw=2, ls=':', label=f"Total: {total:.1f}ms")
    ax1.set_ylabel("Latency (ms)")
    ax1.set_title(f"Latency Breakdown (SF7)\nTotal ≈ {total:.0f}ms — Well below 500ms threshold")
    ax1.legend(fontsize=9)
    ax1.grid(True, axis='y')

    # Plot 2: Total latency vs SF
    ax2 = axes[1]
    total_latency = t_sensor + t_edge_ai + t_mcu + ToAs
    ax2.plot(SFs, total_latency, color=PURPLE, lw=2.5, marker='o',
             markersize=8, label="Total end-to-end latency")
    ax2.fill_between(SFs, total_latency, alpha=0.2, color=PURPLE)
    ax2.axhline(500, color=RED, lw=2, ls='--', label="500ms life-critical threshold")
    ax2.fill_between(SFs, 500, max(total_latency)*1.1,
                     alpha=0.1, color=RED, label="Above threshold")
    ax2.fill_between(SFs, 0, 500,
                     alpha=0.05, color=GREEN, label="Safe zone")

    for sf, lat in zip(SFs, total_latency):
        ax2.annotate(f"{lat:.0f}ms", xy=(sf, lat), xytext=(sf, lat+40),
                     ha='center', fontsize=9, color=PURPLE)

    ax2.set_xlabel("LoRa Spreading Factor (SF)")
    ax2.set_ylabel("Total Latency (ms)")
    ax2.set_title("Total Latency vs Spreading Factor\n(Higher SF = longer range but slower)")
    ax2.legend(fontsize=9)
    ax2.grid(True)
    ax2.set_xticks(SFs)

    plt.tight_layout()
    plt.savefig("output_figures/Latency_pipeline.png",
                dpi=150, bbox_inches='tight', facecolor='#0d1117')
    plt.close()
    print("[LATENCY] Pipeline simulation saved.")


# =============================================================================
# LIMITATIONS ANALYSIS
# =============================================================================
def simulate_limitations():
    """
    Three limitation analyses:
    1. Battery life vs payload — affects deployment duration
    2. Detection accuracy vs environmental noise level
    3. Communication range vs terrain obstruction factor
    """
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle("System Limitations Analysis\n"
                 "Battery Endurance | Environmental Noise Impact | Terrain Obstruction",
                 fontsize=13, color=RED)

    # --- 1. Battery life ---
    ax1 = axes[0]
    # LiPo 3S 5000mAh = 55.5 Wh
    # Idle power: MCU(0.5W) + Sensors(1W) + LoRa(0.5W) = 2W
    # Active hover (balloon, no drone): 0W extra — but if drone: ~80W
    # We model a tethered balloon: only electronics
    capacity_Wh = np.linspace(10, 100, 200)     # Wh
    P_electronics = 2.0   # W — ESP32 + sensors + LoRa
    P_drone_hover = 80.0  # W — typical quadrotor hover

    life_balloon = capacity_Wh / P_electronics
    life_drone   = capacity_Wh / (P_electronics + P_drone_hover)

    ax1.plot(capacity_Wh, life_balloon, color=TEAL,   lw=2.5, label="Tethered balloon (electronics only)")
    ax1.plot(capacity_Wh, life_drone,   color=ORANGE, lw=2.5, label="Drone-mounted (hover + electronics)")
    ax1.axhline(6, color=GREEN, lw=1.5, ls='--', label="6-hour operational target")
    ax1.axvline(55.5, color=GRAY, lw=1.5, ls=':', label="3S 5000mAh LiPo (55.5 Wh)")
    ax1.set_xlabel("Battery Capacity (Wh)")
    ax1.set_ylabel("Operational Duration (hours)")
    ax1.set_title("Battery Life vs Capacity\nPlatform Comparison")
    ax1.legend(fontsize=8)
    ax1.grid(True)

    # --- 2. Detection accuracy vs noise ---
    ax2 = axes[1]
    noise_levels = np.linspace(0, 1, 200)   # normalized noise (0=ideal, 1=extreme)

    # Accuracy degrades: thermal most robust, acoustic least
    acc_thermal  = 0.97 * np.exp(-1.2 * noise_levels)
    acc_acoustic = 0.90 * np.exp(-2.5 * noise_levels)
    acc_rf       = 0.85 * np.exp(-1.8 * noise_levels)
    acc_fusion   = np.clip(0.4*acc_thermal + 0.3*acc_acoustic + 0.3*acc_rf, 0, 1)

    ax2.plot(noise_levels, acc_thermal  * 100, color=ORANGE, lw=2.5, label="Thermal")
    ax2.plot(noise_levels, acc_acoustic * 100, color=BLUE,   lw=2.5, label="Acoustic")
    ax2.plot(noise_levels, acc_rf       * 100, color=TEAL,   lw=2.5, label="RF")
    ax2.plot(noise_levels, acc_fusion   * 100, color=YELLOW, lw=2.5,
             ls='--', label="Fused (weighted)")
    ax2.axhline(70, color=RED, lw=1.5, ls='--', label="Min acceptable accuracy (70%)")
    ax2.set_xlabel("Normalized Environmental Noise Level")
    ax2.set_ylabel("Detection Accuracy (%)")
    ax2.set_title("Accuracy vs Environmental Noise\n(0=Ideal, 1=Extreme Conditions)")
    ax2.legend(fontsize=8)
    ax2.grid(True)
    ax2.set_ylim(0, 105)

    # --- 3. Communication range vs terrain obstruction ---
    ax3 = axes[2]
    obstruction = np.linspace(0, 1, 200)   # 0=open field, 1=dense urban rubble

    # Effective range model: R(obs) = R_free * (1 - 0.7*obs)^n_factor
    # n_factor accounts for LoRa's link margin being eroded by shadowing
    R_free = 2000   # m — LoRa open-field range at SF12
    R_eff  = R_free * np.exp(-2.3 * obstruction)

    # Altitude benefit: higher altitude partially compensates obstruction
    def range_at_alt(alt, obs):
        # Partial line-of-sight improvement from altitude
        alt_bonus = 1 + 0.3 * np.log10(alt / 10 + 1)
        return R_free * np.exp(-2.3 * obs) * alt_bonus

    for alt, col in [(30, GRAY), (50, BLUE), (100, TEAL), (150, GREEN)]:
        R = range_at_alt(alt, obstruction)
        ax3.plot(obstruction, R, color=col, lw=2, label=f"Alt = {alt}m")

    ax3.axhline(500, color=RED, lw=1.5, ls='--', label="Min useful range (500m)")
    ax3.set_xlabel("Terrain Obstruction Factor\n(0=Open, 1=Dense Rubble)")
    ax3.set_ylabel("Effective Communication Range (m)")
    ax3.set_title("Comm Range vs Terrain\nAltitude as Mitigation")
    ax3.legend(fontsize=8)
    ax3.grid(True)

    plt.tight_layout()
    plt.savefig("output_figures/Limitations_analysis.png",
                dpi=150, bbox_inches='tight', facecolor='#0d1117')
    plt.close()
    print("[LIMITATIONS] Analysis saved.")


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("  22EEP69_02 — Disaster Response System Simulation")
    print("  NMIT, Dept. of EEE")
    print("=" * 60)

    simulate_tc1()
    simulate_tc2_thermal()
    simulate_tc2_acoustic()
    simulate_tc2_rf()
    simulate_tc3()
    simulate_latency()
    simulate_limitations()

    print("\n✓ All simulations complete.")
    print("  Figures saved in: ./output_figures/")
    print("  Files:")
    for f in os.listdir("output_figures"):
        print(f"    → {f}")
