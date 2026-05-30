# Implementation Notes — 22EEP69_02
## Phase-2 Hardware Integration Guide

---

## Hardware Components (Finalized in Phase-1)

| Component                   | Role                  | Interface      |
|-----------------------------|-----------------------|----------------|
| Seeed XIAO ESP32-S3 Sense   | Main MCU / Edge AI    | —              |
| MLX90640 IR array           | Thermal sensor        | I2C (0x33)     |
| MEMS Microphone (onboard)   | Acoustic sensor       | PDM / I2S      |
| ESP32 built-in Wi-Fi        | RF/RSSI scanning      | esp_wifi API   |
| LoRa SX1276 module          | Long-range comms      | SPI            |
| Li-Po 3S 5000mAh            | Power supply          | JST connector  |

---

## How Simulation Maps to Real Hardware

### TC1 — Communication (simulation.py → `simulate_tc1`)

**Simulation does:** Computes expected RSSI using FSPL at various altitudes.

**Phase-2 hardware code (ESP32 Arduino):**
```cpp
// On receiving node (ground station with SX1276)
#include <LoRa.h>

void loop() {
    if (LoRa.parsePacket()) {
        int rssi = LoRa.packetRssi();
        float snr = LoRa.packetSnr();
        Serial.printf("RSSI: %d dBm | SNR: %.1f dB\n", rssi, snr);
        // Compare against -137 dBm threshold (SF12)
        if (rssi > -137) {
            Serial.println("LINK OK");
        }
    }
}
```

**Validation:** Match measured RSSI against the simulation curve at known distances.

---

### TC2-A — Thermal Detection (simulation.py → `simulate_tc2_thermal`)

**Simulation does:** Models IR intensity using inverse-square law; applies 3σ threshold.

**Phase-2 hardware code:**
```cpp
#include <Wire.h>
#include "MLX90640_API.h"

float mlx90640To[768];    // 32×24 pixel array

void setup() {
    Wire.begin();
    Wire.setClock(400000);  // I2C fast mode
    MLX90640_SetRefreshRate(0x33, 0x04);  // 8Hz
}

void loop() {
    MLX90640_GetFrameData(0x33, mlx90640Frame);
    MLX90640_CalculateTo(mlx90640Frame, &mlx90640Params, 0.95, 23.0, mlx90640To);

    // Find max temperature in frame
    float maxTemp = *std::max_element(mlx90640To, mlx90640To + 768);

    // Background mean estimated from frame edges (assumed cold)
    float bgMean = 0;
    for (int i = 0; i < 32; i++) bgMean += mlx90640To[i];
    bgMean /= 32;

    float threshold = bgMean + 5.0;  // 5°C above ambient
    bool thermal_flag = (maxTemp > threshold);
}
```

**Validation:** Hold a thermal target at measured distances; log detection/no-detection.

---

### TC2-B — Acoustic Detection (simulation.py → `simulate_tc2_acoustic`)

**Simulation does:** Models SPL propagation; checks if SPL > noise_floor + 6dB.

**Phase-2 hardware code:**
```cpp
#include <driver/i2s.h>

#define I2S_WS 42
#define I2S_SCK 41
#define I2S_SD 2

int16_t samples[512];

void setup() {
    i2s_config_t i2s_config = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX | I2S_MODE_PDM),
        .sample_rate = 16000,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
        .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    };
    i2s_driver_install(I2S_NUM_0, &i2s_config, 0, NULL);
}

void loop() {
    size_t bytes_read;
    i2s_read(I2S_NUM_0, samples, sizeof(samples), &bytes_read, portMAX_DELAY);

    // Compute RMS amplitude
    long sum = 0;
    for (int i = 0; i < 256; i++) sum += (long)samples[i] * samples[i];
    float rms = sqrt((float)sum / 256);

    // Convert to dB SPL (calibrate against known source)
    float spl_dB = 20 * log10(rms / 1.0) + CALIBRATION_OFFSET;

    bool acoustic_flag = (spl_dB > 46.0);  // 40 dB floor + 6 dB margin
}
```

---

### TC2-C — RF Signal Detection (simulation.py → `simulate_tc2_rf`)

**Simulation does:** Models RSSI using LDPL; detection if RSSI > −80 dBm.

**Phase-2 hardware code:**
```cpp
#include "esp_wifi.h"

bool rf_flag = false;

void scan_wifi() {
    wifi_scan_config_t scan_config = {
        .ssid = NULL,
        .bssid = NULL,
        .channel = 0,
        .show_hidden = true
    };
    esp_wifi_scan_start(&scan_config, true);

    uint16_t ap_count;
    esp_wifi_scan_get_ap_num(&ap_count);

    wifi_ap_record_t ap_records[ap_count];
    esp_wifi_scan_get_ap_records(&ap_count, ap_records);

    rf_flag = false;
    for (int i = 0; i < ap_count; i++) {
        if (ap_records[i].rssi > -80) {
            rf_flag = true;
            ESP_LOGI("RF", "Device found: RSSI = %d", ap_records[i].rssi);
        }
    }
}
```

---

### TC3 — Fusion & Alert (simulation.py → `simulate_tc3`)

**Simulation does:** Weighted fusion of 3 binary flags → confidence → alert level.

**Phase-2 hardware code (main loop):**
```cpp
void send_alert(int level, float confidence) {
    // Build LoRa packet: [alert_level, confidence_byte, timestamp]
    uint8_t packet[4];
    packet[0] = 0xAA;               // header
    packet[1] = (uint8_t)level;     // 0–3
    packet[2] = (uint8_t)(confidence * 100);  // 0–100
    packet[3] = 0xBB;               // footer

    LoRa.beginPacket();
    LoRa.write(packet, 4);
    LoRa.endPacket();
}

void loop() {
    // Read flags from each sensor function
    bool T_flag  = thermal_detect();
    bool A_flag  = acoustic_detect();
    bool RF_flag = wifi_scan_detect();

    // Weighted fusion
    float confidence = 0.4 * T_flag + 0.3 * A_flag + 0.3 * RF_flag;

    int alert_level = 0;
    if      (confidence >= 0.9) alert_level = 3;
    else if (confidence >= 0.6) alert_level = 2;
    else if (confidence >= 0.3) alert_level = 1;

    if (alert_level >= 2) {
        send_alert(alert_level, confidence);
    }

    delay(1000);  // 1-second scan cycle
}
```

---

## Latency Measurement in Phase-2

To measure real end-to-end latency:
```cpp
unsigned long t_start = millis();

// ... sensor read, inference, packet send ...

unsigned long t_end = millis();
Serial.printf("End-to-end latency: %lu ms\n", t_end - t_start);
```

Log 100 measurements and compute mean ± std. Compare against simulated 179ms.

---

## Ground Station (Python receiver for PC)

```python
import serial
import struct
import datetime

ser = serial.Serial('COM3', 115200)  # adjust port

while True:
    data = ser.read(4)
    if data[0] == 0xAA and data[3] == 0xBB:
        level      = data[1]
        confidence = data[2] / 100.0
        ts         = datetime.datetime.now()
        labels     = ["NONE", "LOW", "MEDIUM", "HIGH"]
        print(f"[{ts}] ALERT: {labels[level]} | Confidence: {confidence:.2f}")
```

---

## Testing Checklist (Phase-2 Validation)

| Test                     | Method                                      | Pass Criterion           |
|--------------------------|---------------------------------------------|--------------------------|
| TC1 — Link range         | Walk ground station away from aerial node   | RSSI > −137 dBm at 500m  |
| TC2-A — Thermal          | Person at 3m, 5m, 7m from sensor           | Detection at ≤7m          |
| TC2-B — Acoustic         | Voice at measured distances                 | Detection at ≤15m         |
| TC2-C — RF               | Mobile phone at measured distances          | Detection at ≤40m (open) |
| TC3 — Fusion alert       | All three sensors triggered simultaneously  | HIGH alert transmitted    |
| Latency                  | Measure t_start to t_end                    | < 500 ms                  |
| False positive rate      | No person present, run for 5 min           | < 2 false alerts/min      |
