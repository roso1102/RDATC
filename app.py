import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from mpl_toolkits.mplot3d import Axes3D
import time
import os

# Set page config
st.set_page_config(
    page_title="22EEP69_02 — Disaster Response Live Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium styling override
st.markdown("""
<style>
    .stApp {
        background-color: #0d1117;
        color: #e6edf3;
    }
    .main-title {
        color: #00d4aa;
        font-family: 'monospace';
        font-weight: bold;
        margin-bottom: 2px;
    }
    .subtitle {
        color: #8b949e;
        font-family: 'monospace';
        margin-bottom: 25px;
    }
    .card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
    }
    .live-status {
        background-color: #1f2937;
        border: 1.5px solid #00d4aa;
        border-radius: 6px;
        padding: 15px;
        font-size: 16px;
        font-family: 'monospace';
        margin-bottom: 15px;
    }
    .impact-glow {
        background-color: #27211a;
        border-left: 5px solid #ff7b2c;
        border-radius: 4px;
        padding: 15px;
        margin-bottom: 20px;
        font-size: 15px;
        line-height: 1.6;
    }
    .highlight {
        color: #ffd700;
        font-weight: bold;
    }
    .badge-red { background-color: #7f1d1d; color: #fecaca; padding: 2px 8px; border-radius: 4px; font-weight: bold; }
    .badge-green { background-color: #064e3b; color: #a7f3d0; padding: 2px 8px; border-radius: 4px; font-weight: bold; }
    .badge-blue { background-color: #1e3a8a; color: #bfdbfe; padding: 2px 8px; border-radius: 4px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Matplotlib global styles
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
    'axes.labelsize':   10,
})

TEAL    = '#00d4aa'
ORANGE  = '#ff7b2c'
BLUE    = '#3d9bff'
RED     = '#ff4757'
YELLOW  = '#ffd700'
PURPLE  = '#b48eff'
GREEN   = '#4ade80'
GRAY    = '#8b949e'

st.markdown('<h1 class="main-title">🛰️ Disaster Response System Live Simulation</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Real-time Visualizer: Drone-based All-Terrain Presence Detection & LoRa Communications</p>', unsafe_allow_html=True)

# --- Sidebar ---
st.sidebar.header("⚙️ Simulation Navigator")
section = st.sidebar.radio("Navigate Sections", [
    "🎥 Live Multi-Modal Alert Fusion (TC3)",
    "📡 Live Drone Range Sweep (TC1)",
    "👁️ Live Survivor Detection Scans (TC2)",
    "⏱️ Live Latency & Battery Drains"
])

speed = st.sidebar.slider("Animation Delay Speed", 0.01, 1.0, 0.08, 0.05)

# -----------------------------------------------------------------------------
# TAB 1: Live Alert Fusion (TC3)
# -----------------------------------------------------------------------------
if section == "🎥 Live Multi-Modal Alert Fusion (TC3)":
    st.subheader("🎥 Live Alert Fusion Simulation")
    
    st.markdown("""
    <div class="card">
        <h3>🔍 Concept made simple:</h3>
        A rescue drone flies over a search zone. It collects signals from three sensors:
        <ul>
            <li><strong>Thermal (Heat):</strong> Measures body temperature (~37°C).</li>
            <li><strong>Acoustic (Microphone):</strong> Listens for survivor screams.</li>
            <li><strong>RF Scan (WiFi/Bluetooth):</strong> Scans for wireless signals from cellphones.</li>
        </ul>
        <strong>The Problem:</strong> No sensor is perfect. Dust blocks cameras; wind ruins microphones; rubble shields phone signals. <br>
        <strong>The Solution:</strong> <strong>Sensor Fusion.</strong> The system merges all three signals using a weighted scoring formula to decide if it should send an alert back to the rescue base.
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    w_T = col1.slider("Thermal Weight (Reliability)", 0.0, 1.0, 0.4, 0.05)
    w_A = col2.slider("Acoustic Weight (Reliability)", 0.0, 1.0, 0.3, 0.05)
    w_RF = col3.slider("RF Scan Weight (Reliability)", 0.0, 1.0, 0.3, 0.05)
    
    total_w = w_T + w_A + w_RF
    if total_w > 0:
        w_T /= total_w
        w_A /= total_w
        w_RF /= total_w

    col_btn1, col_btn2 = st.columns([1, 4])
    run_btn = col_btn1.button("▶ Run Live Simulation", use_container_width=True)
    stop_btn = col_btn1.button("Reset", use_container_width=True)
    
    with col_btn2:
        st.markdown("<div style='background-color:#161b22; padding:15px; border-radius:6px; border:1px solid #30363d;'>", unsafe_allow_html=True)
        status_cols = st.columns(5)
        m_thermal = status_cols[0].empty()
        m_acoustic = status_cols[1].empty()
        m_rf = status_cols[2].empty()
        m_confidence = status_cols[3].empty()
        m_alert = status_cols[4].empty()
        st.markdown("</div>", unsafe_allow_html=True)
        
    live_commentary = st.empty()
    chart_placeholder = st.empty()

    if 't_sim' not in st.session_state or stop_btn:
        st.session_state.t_sim = 0
        st.session_state.history = {'t': [], 'T': [], 'A': [], 'RF': [], 'conf': [], 'alert': []}

    def render_fusion_plot(history):
        t = np.array(history['t'])
        T_flag = np.array(history['T'])
        A_flag = np.array(history['A'])
        RF_flag = np.array(history['RF'])
        confidence = np.array(history['conf'])
        alert_level = np.array(history['alert'])
        
        fig = plt.figure(figsize=(15, 8))
        gs = gridspec.GridSpec(3, 2, figure=fig, hspace=0.5, wspace=0.3)
        
        # 1. Sensors
        ax1 = fig.add_subplot(gs[0, :])
        if len(t) > 0:
            ax1.step(t, T_flag  + 0.1, color=ORANGE, lw=2, label="Thermal (Heat)",  where='post')
            ax1.step(t, A_flag  + 2.2, color=BLUE,   lw=2, label="Acoustic (Voice)", where='post')
            ax1.step(t, RF_flag + 4.3, color=TEAL,   lw=2, label="RF (Phone Scan)",  where='post')
        ax1.axvspan(15, 45, alpha=0.08, color=GREEN, label="True Presence Zone (Survivor actually there)")
        ax1.set_yticks([0.6, 2.7, 4.8])
        ax1.set_yticklabels(["Thermal", "Acoustic", "RF"])
        ax1.set_xlabel("Time (s)")
        ax1.set_title("Live Sensor Readings (1 = Detected, 0 = Clear)")
        ax1.legend(loc='upper right', fontsize=8)
        ax1.grid(True)
        ax1.set_ylim(-0.2, 5.8)
        ax1.set_xlim(0, 60)
        
        # 2. Confidence
        ax2 = fig.add_subplot(gs[1, :])
        if len(t) > 0:
            ax2.fill_between(t, confidence, alpha=0.25, color=YELLOW)
            ax2.plot(t, confidence, color=YELLOW, lw=2.5, label="Fusion Confidence Score")
        ax2.axhline(0.3, color=GRAY,   lw=1.5, ls='--', label="Low Alert Threshold")
        ax2.axhline(0.6, color=ORANGE, lw=1.5, ls='--', label="Medium Alert Threshold")
        ax2.axhline(0.9, color=RED,    lw=1.5, ls='--', label="High Alert Threshold")
        ax2.axvspan(15, 45, alpha=0.08, color=GREEN)
        ax2.set_ylabel("Confidence")
        ax2.set_xlabel("Time (s)")
        ax2.set_title("Combined Fusion Confidence Score")
        ax2.legend(fontsize=8, loc='upper right')
        ax2.set_ylim(-0.05, 1.15)
        ax2.set_xlim(0, 60)
        ax2.grid(True)
        
        # 3. Alert Actions
        ax3 = fig.add_subplot(gs[2, 0])
        colors_map = {0: GRAY, 1: BLUE, 2: ORANGE, 3: RED}
        if len(t) > 0:
            bar_colors = [colors_map[int(a)] for a in alert_level]
            ax3.bar(t, alert_level + 0.05, color=bar_colors, width=0.8)
        ax3.set_yticks([0, 1, 2, 3])
        ax3.set_yticklabels(["None", "LOW (Log only)", "MEDIUM (Transmit)", "HIGH (Rescue Beacon!)"])
        ax3.set_xlabel("Time (s)")
        ax3.set_title("Triggered Action Level")
        ax3.grid(True, axis='y')
        ax3.set_xlim(0, 60)
        
        # 4. Confusion Matrix Summary
        ax4 = fig.add_subplot(gs[2, 1])
        if len(t) > 0:
            true_presence = (t >= 15) & (t <= 45)
            detected      = alert_level >= 2
            
            TP = np.sum( true_presence  &  detected)
            FP = np.sum(~true_presence  &  detected)
            TN = np.sum(~true_presence  & ~detected)
            FN = np.sum( true_presence  & ~detected)
            
            matrix = np.array([[TP, FP], [FN, TN]])
            labels = [["TP (True Positive)", "FP (False Alarm)"], ["FN (Missed Person)", "TN (True Clear)"]]
            im = ax4.imshow(matrix, cmap='RdYlGn', vmin=0, vmax=35)
            for i in range(2):
                for j in range(2):
                    ax4.text(j, i, f"{labels[i][j]}\n{matrix[i,j]}",
                             ha='center', va='center', fontsize=9,
                             color='black', fontweight='bold')
            ax4.set_xticks([0, 1])
            ax4.set_yticks([0, 1])
            ax4.set_xticklabels(["Alert Sent", "No Alert"])
            ax4.set_yticklabels(["Person Present", "No Person"])
            precision = TP/(TP+FP+1e-9)
            recall = TP/(TP+FN+1e-9)
            ax4.set_title(f"Accuracy Summary: Precision={precision:.2f} | Recall={recall:.2f}")
        else:
            ax4.text(0.5, 0.5, "Start the simulation to populate matrix", ha='center', va='center')
            ax4.set_axis_off()
            
        fig.patch.set_facecolor('#0d1117')
        return fig

    # Render starting plot
    fig = render_fusion_plot(st.session_state.history)
    chart_placeholder.pyplot(fig)
    plt.close(fig)

    if run_btn:
        np.random.seed(21)
        st.session_state.history = {'t': [], 'T': [], 'A': [], 'RF': [], 'conf': [], 'alert': []}
        
        # Pre-generate simulated sensor streams
        T_stream = np.zeros(60)
        A_stream = np.zeros(60)
        RF_stream = np.zeros(60)
        for i in range(60):
            if 15 <= i <= 45: # Survivor is active in the zone
                T_stream[i] = 1 if np.random.rand() < 0.90 else 0
                A_stream[i] = 1 if np.random.rand() < 0.75 else 0
                RF_stream[i] = 1 if np.random.rand() < 0.80 else 0
            else: # Empty environment with random sensor noise
                T_stream[i] = 1 if np.random.rand() < 0.05 else 0
                A_stream[i] = 1 if np.random.rand() < 0.10 else 0
                RF_stream[i] = 1 if np.random.rand() < 0.15 else 0

        for step in range(60):
            st.session_state.t_sim = step
            T_val = T_stream[step]
            A_val = A_stream[step]
            RF_val = RF_stream[step]
            
            conf_val = w_T * T_val + w_A * A_val + w_RF * RF_val
            
            if conf_val < 0.3:
                alert_val = 0
                alert_lbl = "⚪ None"
            elif conf_val < 0.6:
                alert_val = 1
                alert_lbl = "🔵 LOW"
            elif conf_val < 0.9:
                alert_val = 2
                alert_lbl = "🟠 MEDIUM"
            else:
                alert_val = 3
                alert_lbl = "🔴 HIGH"
                
            st.session_state.history['t'].append(step)
            st.session_state.history['T'].append(T_val)
            st.session_state.history['A'].append(A_val)
            st.session_state.history['RF'].append(RF_val)
            st.session_state.history['conf'].append(conf_val)
            st.session_state.history['alert'].append(alert_val)
            
            # Commentary log
            if step < 15:
                comm_txt = f"**Status (Time = {step}s):** Scan starting. Drone searching empty sector. Sensors reporting noise."
            elif 15 <= step <= 45:
                detect_count = int(T_val) + int(A_val) + int(RF_val)
                comm_txt = f"**Status (Time = {step}s):** Survivor present in area! Active detections: {detect_count}/3. Fusion score is <span class='highlight'>{conf_val:.2f}</span>. Alert status: **{alert_lbl}**."
            else:
                comm_txt = f"**Status (Time = {step}s):** Drone flown past survivor. Returning to monitoring noise floor."
                
            live_commentary.markdown(f"<div class='live-status'>{comm_txt}</div>", unsafe_allow_html=True)
            
            # Metrics
            m_thermal.metric("Thermal (Heat)", "DETECTED 🔥" if T_val else "Clear ❄️")
            m_acoustic.metric("Acoustic (Sound)", "DETECTED 🔊" if A_val else "Clear 🔇")
            m_rf.metric("RF Signal (Phone)", "DETECTED 📱" if RF_val else "Clear 📴")
            m_confidence.metric("Fusion Confidence", f"{conf_val:.2f}")
            m_alert.metric("Action Triggered", alert_lbl)
            
            fig = render_fusion_plot(st.session_state.history)
            chart_placeholder.pyplot(fig)
            plt.close(fig)
            time.sleep(speed)

# -----------------------------------------------------------------------------
# TAB 2: Live Drone Range Sweep (TC1)
# -----------------------------------------------------------------------------
elif section == "📡 Live Drone Range Sweep (TC1)":
    st.subheader("📡 Live Drone Range Sweep (Communication Link)")
    
    st.markdown("""
    <div class="card">
        <h3>🔍 Concept made simple:</h3>
        The drone flies away from the base station to scan rubble. The further away it goes, the weaker its radio link becomes.
        We must calculate: <strong>how far can the drone fly before we lose communication?</strong>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        tx_power = st.slider("Transmission Power (dBm)", 10, 22, 20, help="How strongly the drone broadcasts. Higher = longer range, but uses more battery.")
        f_mhz = st.slider("Frequency (MHz)", 433, 915, 868, help="Carrier frequency. 868MHz is typical for LoRa EU.")
    with col2:
        sensitivity = st.slider("Receiver Sensitivity (dBm)", -140, -110, -137, help="How sensitive the ground station antenna is.")
        drone_alt = st.slider("Drone Altitude (m)", 10, 250, 50, help="Flying altitude.")
        
    start_sweep = st.button("✈ Start Live Drone Flight Sweep")
    flight_placeholder = st.empty()
    impact_lbl = st.empty()
    chart_placeholder = st.empty()
    
    f = f_mhz * 1e6
    c = 3e8
    Gtx = 2
    Grx = 2
    
    h_dist = np.linspace(1, 3000, 500)
    
    def draw_sweep_plot(current_dist=None):
        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        fig.patch.set_facecolor('#0d1117')
        
        # Plot 1: Received Power
        ax1 = axes[0]
        for alt_ref, col in [(30, BLUE), (100, PURPLE)]:
            d3d_ref = np.sqrt(h_dist**2 + alt_ref**2)
            FSPL_ref = 20*np.log10(d3d_ref) + 20*np.log10(f) + 20*np.log10(4*np.pi/c)
            Prx_ref = tx_power + Gtx + Grx - FSPL_ref
            ax1.plot(h_dist, Prx_ref, color=col, alpha=0.4, ls='--', label=f"Alt = {alt_ref}m (Ref)")
            
        d3d = np.sqrt(h_dist**2 + drone_alt**2)
        FSPL = 20*np.log10(d3d) + 20*np.log10(f) + 20*np.log10(4*np.pi/c)
        Prx = tx_power + Gtx + Grx - FSPL
        ax1.plot(h_dist, Prx, color=TEAL, lw=2.5, label=f"Active Path (Alt = {drone_alt}m)")
        
        ax1.axhline(sensitivity, color=RED, lw=2, ls='--', label=f"Receiver Sensitivity ({sensitivity} dBm)")
        ax1.fill_between(h_dist, sensitivity, -165, alpha=0.12, color=RED, label="Connection Lost Zone")
        
        if current_dist is not None:
            curr_d3d = np.sqrt(current_dist**2 + drone_alt**2)
            curr_fspl = 20*np.log10(curr_d3d) + 20*np.log10(f) + 20*np.log10(4*np.pi/c)
            curr_prx = tx_power + Gtx + Grx - curr_fspl
            ax1.plot(current_dist, curr_prx, marker='o', markersize=10, color=YELLOW, label="Current Drone Position")
            
        ax1.set_xlabel("Horizontal Distance (m)")
        ax1.set_ylabel("Signal Strength (dBm)")
        ax1.set_title("Signal Strength vs Distance")
        ax1.legend(fontsize=9)
        ax1.grid(True)
        ax1.set_ylim(-165, -60)
        
        # Plot 2: Contour Heatmap
        ax2 = axes[1]
        h_range = np.linspace(10, 2500, 200)
        alts = np.linspace(10, 200, 200)
        H, A = np.meshgrid(h_range, alts)
        D3D = np.sqrt(H**2 + A**2)
        FSPL2D = 20*np.log10(D3D) + 20*np.log10(f) + 20*np.log10(4*np.pi/c)
        Prx2D = tx_power + Gtx + Grx - FSPL2D
        margin = Prx2D - sensitivity
        
        im = ax2.contourf(H, A, margin, levels=20, cmap=plt.cm.RdYlGn, alpha=0.9)
        ax2.contour(H, A, margin, levels=[0], colors=[RED], linewidths=2)
        cbar = fig.colorbar(im, ax=ax2)
        cbar.set_label("Signal Margin (dB)")
        
        if current_dist is not None:
            ax2.plot(current_dist, drone_alt, marker='X', markersize=12, color=YELLOW, markeredgecolor='black')
            
        ax2.set_xlabel("Horizontal Distance (m)")
        ax2.set_ylabel("Drone Altitude (m)")
        ax2.set_title("Link Range Map (Green = Safe, Red Contour = Boundary)")
        
        return fig
        
    fig = draw_sweep_plot()
    chart_placeholder.pyplot(fig)
    plt.close(fig)
    
    if start_sweep:
        for dist in range(10, 3005, 100):
            curr_d3d = np.sqrt(dist**2 + drone_alt**2)
            curr_fspl = 20*np.log10(curr_d3d) + 20*np.log10(f) + 20*np.log10(4*np.pi/c)
            curr_prx = tx_power + Gtx + Grx - curr_fspl
            connected = curr_prx > sensitivity
            conn_status = "<span class='badge-green'>CONNECTED</span>" if connected else "<span class='badge-red'>DISCONNECTED</span>"
            
            flight_placeholder.markdown(f"<div class='live-status'>**Horizontal Range:** `{dist}m` | **Active Signal Strength:** `{curr_prx:.1f} dBm` | **Status:** {conn_status}</div>", unsafe_allow_html=True)
            
            if dist < 500:
                imp = "Signal is solid. Video feed is streaming with zero frame drops."
            elif 500 <= dist < 1200:
                imp = "Telemetry is clear, but real-time video feed is starting to experience minor lag."
            elif 1200 <= dist < 1800:
                imp = "Warning! High packet loss. Drone should prepare to turn around to avoid link drop."
            elif 1800 <= dist and connected:
                imp = "CRITICAL LIMIT! Link is holding on by a thread. Prepare for emergency Return-to-Home."
            else:
                imp = "⚠️ CONNECTION LOST! The drone has flown too far. Control is lost! Automated failsafe activated."
                
            impact_lbl.markdown(f"<div class='impact-glow'><strong>Live Mission Impact:</strong><br>{imp}</div>", unsafe_allow_html=True)
            
            fig = draw_sweep_plot(dist)
            chart_placeholder.pyplot(fig)
            plt.close(fig)
            time.sleep(speed)

# -----------------------------------------------------------------------------
# TAB 3: Live Survivor Detection Scans (TC2) - 3D ENGAGING VIEWS
# -----------------------------------------------------------------------------
elif section == "👁️ Live Survivor Detection Scans (TC2)":
    st.subheader("👁️ Live Survivor Detection Scans (3D Visualizer)")
    
    st.markdown("""
    <div class="card">
        <h3>🔍 3D Signal Modeling:</h3>
        We model survivor signatures as 3D physical fields on the ground.
        The graphs below now display a **3D spatial profile** of the signal strength. 
        Watch the drone's position move in 3D relative to the survivor to understand the physics of search boundaries.
    </div>
    """, unsafe_allow_html=True)
    
    sensor_model = st.radio("Select Sensor to Model", ["Thermal Sensor (Heat Signature)", "Acoustic (Microphone / Screams)", "RF Scan (WiFi/Bluetooth beacons)"])
    
    col_controls, col_display = st.columns([1, 2])
    
    with col_controls:
        st.markdown("### 🔧 Environmental Parameters")
        if sensor_model == "Thermal Sensor (Heat Signature)":
            p_heat = st.slider("Human Thermal Power (W)", 50, 150, 100)
            bg_noise = st.slider("Ambient Noise Floor (W/m²)", 1e-4, 1e-3, 3e-4, 5e-5)
            sensor_h = st.slider("Drone Height (m)", 2, 20, 8)
            threshold = bg_noise + 1.5e-4
            
        elif sensor_model == "Acoustic (Microphone / Screams)":
            voice_db = st.slider("Voice SPL (dB)", 50, 90, 70)
            ambient_db = st.slider("Wind/Rotor Noise (dB)", 20, 60, 40)
            sensor_h = st.slider("Drone Height (m)", 2, 30, 10)
            threshold = ambient_db + 6
            
        elif sensor_model == "RF Scan (WiFi/Bluetooth beacons)":
            n_debris = st.slider("Rubble Density (n)", 2.0, 4.0, 3.2, 0.1)
            rf_thresh = st.slider("Receiver Limit (dBm)", -95, -70, -80)
            sensor_h = st.slider("Drone Height (m)", 2, 40, 15)
            threshold = rf_thresh

        start_scan = st.button("▶ Run 3D Sweep Simulation", use_container_width=True)
        scan_lbl = st.empty()
        impact_lbl = st.empty()

    with col_display:
        chart_placeholder = st.empty()

    # Generate 3D grid data
    x_grid = np.linspace(-30, 30, 40)
    y_grid = np.linspace(-30, 30, 40)
    X, Y = np.meshgrid(x_grid, y_grid)

    def draw_3d_sensor_plot(drone_x=None):
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')
        fig.patch.set_facecolor('#0d1117')
        ax.set_facecolor('#161b22')
        
        # Calculate signal over grid
        if sensor_model == "Thermal Sensor (Heat Signature)":
            # Intensity drops off with 3D distance
            Z = p_heat / (4 * np.pi * (X**2 + Y**2 + sensor_h**2))
            cmap = 'YlOrRd'
            z_label = "IR Intensity (W/m²)"
            title = "3D Thermal Footprint profile"
            cutoff = threshold
        elif sensor_model == "Acoustic (Microphone / Screams)":
            d3d = np.sqrt(X**2 + Y**2 + sensor_h**2)
            Z = voice_db - 20 * np.log10(d3d + 0.1) - 11
            cmap = 'plasma'
            z_label = "Sound Pressure Level (dB)"
            title = "3D Sound Propagation Profile"
            cutoff = threshold
        else: # RF Scan
            d3d = np.sqrt(X**2 + Y**2 + sensor_h**2)
            Z = -40 - 10 * n_debris * np.log10(d3d + 0.1)
            cmap = 'viridis'
            z_label = "Signal Strength RSSI (dBm)"
            title = f"3D Radio Beacon Dome (n={n_debris})"
            cutoff = threshold

        # Plot 3D surface
        surf = ax.plot_surface(X, Y, Z, cmap=cmap, edgecolor='none', alpha=0.85)
        
        # Add colorbar
        cbar = fig.colorbar(surf, ax=ax, shrink=0.5, aspect=10)
        cbar.set_label(z_label, color='#e6edf3')
        
        # Fixed threshold plane
        ax.plot_surface(X, Y, np.full_like(Z, cutoff), color='red', alpha=0.15, label="Detection Limit")
        
        if drone_x is not None:
            # Active Drone Point floating above
            # Drone moves along X-axis, at Y=0, Z=sensor_h (representing physical flight)
            # Find signal value directly below the drone
            dist_to_origin = np.sqrt(drone_x**2 + sensor_h**2)
            if sensor_model == "Thermal Sensor (Heat Signature)":
                d_sig = p_heat / (4 * np.pi * dist_to_origin**2)
            elif sensor_model == "Acoustic (Microphone / Screams)":
                d_sig = voice_db - 20 * np.log10(dist_to_origin + 0.1) - 11
            else:
                d_sig = -40 - 10 * n_debris * np.log10(dist_to_origin + 0.1)
                
            # Plot drone in 3D
            ax.scatter(drone_x, 0, d_sig, color=YELLOW, s=150, edgecolor='black', label="Drone Scan position", zorder=10)
            
            # Line representing the vertical scan cone
            ax.plot([drone_x, drone_x], [0, 0], [0, d_sig], color=YELLOW, ls=':', lw=2)
            
        ax.set_xlabel("X coordinate (m)")
        ax.set_ylabel("Y coordinate (m)")
        ax.set_zlabel(z_label)
        ax.set_title(title, pad=20, fontsize=14, color=TEAL)
        ax.view_init(elev=25, azim=45)
        
        # Keep limits fixed to stop jittering
        ax.set_zlim(np.min(Z), np.max(Z)*1.1)
        
        return fig

    # Initial plot
    fig = draw_3d_sensor_plot()
    chart_placeholder.pyplot(fig)
    plt.close(fig)

    if start_scan:
        # Simulate Drone flying from left (-30m) to right (+30m) directly over the survivor
        for d_x in np.linspace(-30, 30, 20):
            dist_to_orig = np.sqrt(d_x**2 + sensor_h**2)
            
            if sensor_model == "Thermal Sensor (Heat Signature)":
                val = p_heat / (4 * np.pi * dist_to_orig**2)
                detected = val > threshold
                status = "<span class='badge-green'>DETECTED 🔥</span>" if detected else "<span class='badge-red'>Below Limit ❄️</span>"
                scan_lbl.markdown(f"<div class='live-status'>**Horizontal Drone Pos:** `{d_x:.1f}m` | **Heat Signature at sensor:** `{val:.2e} W/m²` | **Status:** {status}</div>", unsafe_allow_html=True)
                imp = "Drone captures heat peak directly above target." if detected else "Drone is too far horizontally; thermal sensor cannot resolve human body from ambient background."
                
            elif sensor_model == "Acoustic (Microphone / Screams)":
                val = voice_db - 20 * np.log10(dist_to_orig + 0.1) - 11
                detected = val > threshold
                status = "<span class='badge-green'>HEARD SURVIVOR 🔊</span>" if detected else "<span class='badge-red'>Muffled/Drowned 🔇</span>"
                scan_lbl.markdown(f"<div class='live-status'>**Horizontal Drone Pos:** `{d_x:.1f}m` | **Received Sound Level:** `{val:.1f} dB` | **Status:** {status}</div>", unsafe_allow_html=True)
                imp = "Scream successfully isolated by beamforming microphones." if detected else "High propeller noise floor or distance completely mask screams."
                
            else: # RF Scan
                val = -40 - 10 * n_debris * np.log10(dist_to_orig + 0.1)
                detected = val > threshold
                status = "<span class='badge-green'>PHONE SPOTTED 📱</span>" if detected else "<span class='badge-red'>No Signal 📴</span>"
                scan_lbl.markdown(f"<div class='live-status'>**Horizontal Drone Pos:** `{d_x:.1f}m` | **WiFi Signal RSSI:** `{val:.1f} dBm` | **Status:** {status}</div>", unsafe_allow_html=True)
                imp = "Captured cell beacon. IP/MAC logged." if detected else f"Concrete rubble attenuation exponent (n={n_debris}) limits coverage dome."

            impact_lbl.markdown(f"<div class='impact-glow'><strong>Live Mission Impact:</strong><br>{imp}</div>", unsafe_allow_html=True)
            
            fig = draw_3d_sensor_plot(d_x)
            chart_placeholder.pyplot(fig)
            plt.close(fig)
            time.sleep(speed * 2)

# -----------------------------------------------------------------------------
# TAB 4: Live Latency & Battery Drains
# -----------------------------------------------------------------------------
elif section == "⏱️ Live Latency & Battery Drains":
    st.subheader("⏱️ Live Latency & Battery Drain Analyzer")
    
    st.markdown("""
    <div class="card">
        <h3>🔍 Concept made simple:</h3>
        For live rescue support:
        <ul>
            <li><strong>Latency Pipeline:</strong> How fast is data sent from the moment the camera captures a frame to the moment rescue base receives it? (Goal: &lt;500ms).</li>
            <li><strong>Battery Drain:</strong> Quadcopters fly fast but drain batteries rapidly due to rotor motor draw (hovering takes massive power). Tethered balloons stay up for days but don't move.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### ⚡ Live Data Cycle Latency")
        sf = st.selectbox("LoRa Spreading Factor (SF)", [7, 8, 9, 10, 11, 12], index=0)
        edge_ai_inf = st.slider("Edge AI Inference (ms)", 10, 150, 56)
        
        start_cycle = st.button("⏱ Run Live Transmission Cycle")
        cycle_lbl = st.empty()
        impact_lbl1 = st.empty()
        chart_placeholder1 = st.empty()
        
        BW = 125e3
        payload = 20
        T_s = (2**sf) / BW * 1000
        n_payload = 8 + max(np.ceil((8*payload - 4*sf + 28 + 16) / (4*sf)), 0)
        toa_ms = (8 + 4.25 + n_payload) * T_s
        
        def plot_latency(active_stage=-1):
            stages = ['Sensor Acq.', 'Edge AI Inf.', 'MCU Overhead', 'LoRa ToA']
            values = [33, edge_ai_inf, 10, toa_ms]
            colors = [TEAL, PURPLE, BLUE, ORANGE]
            
            plot_colors = []
            for idx in range(4):
                if active_stage >= idx:
                    plot_colors.append(colors[idx])
                else:
                    plot_colors.append('#30363d')
                    
            fig, ax = plt.subplots(figsize=(6, 4))
            fig.patch.set_facecolor('#0d1117')
            bars = ax.bar(stages, values, color=plot_colors)
            for bar, val, p_color in zip(bars, values, plot_colors):
                if p_color != '#30363d':
                    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10, f"{val:.1f}ms", ha='center', color='white', fontsize=8)
            ax.set_ylabel("Latency (ms)")
            ax.axhline(500, color=RED, ls='--', label="500ms Threshold")
            ax.set_ylim(0, max(600, int(toa_ms + 100)))
            ax.legend(fontsize=8)
            return fig
            
        fig = plot_latency()
        chart_placeholder1.pyplot(fig)
        plt.close(fig)
        
        if start_cycle:
            stages_names = [
                "Acquiring raw camera frame...",
                "Running Edge AI target classification...",
                "Encoding packets and preparing serial bus...",
                "Transmitting over-the-air via LoRa modulation..."
            ]
            
            explanation_steps = [
                "**Sensor Acquisition (33ms):** Camera takes 33ms to scan the pixels. This delay is unavoidable.",
                f"**Edge AI Inference ({edge_ai_inf}ms):** Onboard microcontroller runs the neural network model. This takes {edge_ai_inf}ms.",
                "**MCU Packaging (10ms):** The CPU packs the coordinates, checksum, and signal logs into serial packets.",
                f"**LoRa Airtime ({toa_ms:.1f}ms):** The packet is modulated and sent over-the-air. Note: At Spreading Factor SF{sf}, this takes {toa_ms:.1f}ms."
            ]
            
            for step in range(4):
                cycle_lbl.markdown(f"<div class='live-status'>**Step {step+1}:** {stages_names[step]}</div>", unsafe_allow_html=True)
                impact_lbl1.markdown(f"<div class='impact-glow'><strong>Current Step Impact:</strong><br>{explanation_steps[step]}</div>", unsafe_allow_html=True)
                fig = plot_latency(step)
                chart_placeholder1.pyplot(fig)
                plt.close(fig)
                time.sleep(speed * 8)
            
            total_lat = 33 + edge_ai_inf + 10 + toa_ms
            status = "<span class='badge-green'>PASS</span>" if total_lat < 500 else "<span class='badge-red'>FAIL (Too Slow)</span>"
            
            if total_lat < 500:
                final_imp = f"Total latency is `{total_lat:.1f} ms` (Well under the 500ms limit). The rescue team receives live alerts almost instantly."
            else:
                final_imp = f"Total latency is `{total_lat:.1f} ms` (Exceeds 500ms safety threshold!). Alerts are lagging. Time-sensitive rescue could fail."
                
            cycle_lbl.markdown(f"<div class='live-status'>**Total Latency:** `{total_lat:.1f} ms` | **Status:** {status}</div>", unsafe_allow_html=True)
            impact_lbl1.markdown(f"<div class='impact-glow'><strong>Overall Operational Impact:</strong><br>{final_imp}</div>", unsafe_allow_html=True)
            
    with col2:
        st.markdown("### 🔋 Live Battery Discharge")
        battery_wh = st.slider("Battery Capacity (Wh)", 10, 120, 55)
        
        start_drain = st.button("🔋 Simulate Live Battery Drain")
        drain_lbl = st.empty()
        impact_lbl2 = st.empty()
        chart_placeholder2 = st.empty()
        
        P_balloon = 2.0  # Watts
        P_drone = 82.0   # Watts
        
        def plot_battery(current_pct=100.0):
            hours_balloon = battery_wh / P_balloon
            hours_drone = battery_wh / P_drone
            
            fig, ax = plt.subplots(figsize=(6, 4))
            fig.patch.set_facecolor('#0d1117')
            
            pcts = np.linspace(100, 0, 100)
            t_balloon = np.linspace(0, hours_balloon, 100)
            t_drone = np.linspace(0, hours_drone, 100)
            
            ax.plot(t_balloon, pcts, color=TEAL, lw=2, label="Balloon (Only payload)")
            ax.plot(t_drone, pcts, color=ORANGE, lw=2, label="Quadcopter (Motors + payload)")
            
            curr_hr_balloon = hours_balloon * (1 - current_pct/100)
            curr_hr_drone = hours_drone * (1 - current_pct/100)
            
            ax.plot(curr_hr_balloon, current_pct, 'o', color=TEAL, markersize=8)
            ax.plot(curr_hr_drone, current_pct, 'o', color=ORANGE, markersize=8)
            
            ax.set_ylabel("Battery Remaining (%)")
            ax.set_xlabel("Operating Duration (hours)")
            ax.set_ylim(-5, 105)
            ax.legend(fontsize=8)
            ax.grid(True)
            return fig
            
        fig = plot_battery()
        chart_placeholder2.pyplot(fig)
        plt.close(fig)
        
        if start_drain:
            for pct in range(100, -1, -5):
                balloon_rem = (battery_wh / P_balloon) * (pct / 100)
                drone_rem = (battery_wh / P_drone) * (pct / 100)
                drain_lbl.markdown(f"<div class='live-status'>**Battery Charge:** `{pct}%` | **Balloon:** `{balloon_rem:.2f} hrs` | **Drone:** `{drone_rem:.2f} hrs`</div>", unsafe_allow_html=True)
                
                if pct > 75:
                    imp_txt = "Batteries full. Drone can run high speed searches. Balloon has days of operating margin."
                elif 30 < pct <= 75:
                    imp_txt = f"Drone battery is at {pct}%. Hover time remaining: `{drone_rem:.1f} hours`."
                elif 10 < pct <= 30:
                    imp_txt = "LOW BATTERY! Drone must return to base. Balloon can still hover for several hours."
                else:
                    imp_txt = "🔋 EMPTY! Drone has landed/crashed. Balloon power down failsafe triggered."
                    
                impact_lbl2.markdown(f"<div class='impact-glow'><strong>Live Battery Impact:</strong><br>{imp_txt}</div>", unsafe_allow_html=True)
                
                fig = plot_battery(pct)
                chart_placeholder2.pyplot(fig)
                plt.close(fig)
                time.sleep(speed)
