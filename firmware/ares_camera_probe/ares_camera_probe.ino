#include <Arduino.h>
#include <Wire.h>

// Standalone diagnostic: no Wi-Fi, image capture or sensor configuration writes.
// Wiring matches ares_node. PWDN must be held LOW and RESET held HIGH externally.
constexpr uint8_t CAMERA_ADDRESS = 0x21;
constexpr int CAMERA_SDA = 4;
constexpr int CAMERA_SCL = 5;
constexpr int CAMERA_XCLK = 15;

struct RegisterRead {
  uint8_t transmitStatus;
  size_t received;
  int value;
};

RegisterRead readRegister(uint8_t reg, bool stopBetween) {
  Wire.beginTransmission(CAMERA_ADDRESS);
  Wire.write(reg);
  uint8_t status = Wire.endTransmission(stopBetween);
  if (status != 0) return {status, 0, -1};
  size_t count = Wire.requestFrom(CAMERA_ADDRESS, size_t(1), true);
  int value = (count == 1 && Wire.available()) ? Wire.read() : -1;
  while (Wire.available()) Wire.read();
  return {status, count, value};
}

void runProbes() {
  const uint32_t clocks[] = {8000000, 20000000};
  for (uint32_t frequency : clocks) {
    if (!ledcChangeFrequency(CAMERA_XCLK, frequency, 1)) {
      Serial.printf("[ERROR] Cannot set XCLK to %lu Hz\n", (unsigned long)frequency);
      continue;
    }
    delay(100);
    Serial.printf("\n--- XCLK configured: %lu Hz; SCCB: 100000 Hz ---\n",
                  (unsigned long)ledcReadFreq(CAMERA_XCLK));
    Wire.beginTransmission(CAMERA_ADDRESS);
    Serial.printf("Address 0x21 probe status: %u (0 = ACK only, not sensor ID)\n",
                  Wire.endTransmission(true));

    for (int method = 0; method < 2; ++method) {
      bool stopBetween = method == 1;
      Serial.printf("Read method: %s\n", stopBetween ? "STOP then START" : "repeated START");
      for (int attempt = 1; attempt <= 3; ++attempt) {
        RegisterRead pid = readRegister(0x0A, stopBetween);
        RegisterRead ver = readRegister(0x0B, stopBetween);
        Serial.printf("  #%d PID: tx=%u rx=%u value=", attempt,
                      pid.transmitStatus, (unsigned)pid.received);
        if (pid.value < 0) Serial.print("UNREADABLE");
        else Serial.printf("0x%02X", pid.value);
        Serial.printf("; VER: tx=%u rx=%u value=", ver.transmitStatus, (unsigned)ver.received);
        if (ver.value < 0) Serial.print("UNREADABLE");
        else Serial.printf("0x%02X", ver.value);
        Serial.println(pid.value == 0x76 ? " [OV7670 PID matches]" : " [NO OV7670 PID MATCH]");
        delay(30);
      }
    }
  }
  Serial.println("\nProbe complete. Send r or press EN/RESET to repeat. No image capture tested.");
}

void setup() {
  Serial.begin(115200);
  delay(2000);
  Serial.println("\n=== ARES camera SCCB probe v1 ===");
  Serial.println("SDA=GPIO4 SCL=GPIO5 XCLK=GPIO15; external PWDN=LOW RESET=HIGH");
  Serial.printf("PSRAM detected: %s; total bytes: %u (separate from camera ID test)\n",
                psramFound() ? "YES" : "NO", ESP.getPsramSize());
  if (!ledcAttach(CAMERA_XCLK, 8000000, 1) || !ledcWrite(CAMERA_XCLK, 1)) {
    Serial.println("[ERROR] Could not configure XCLK output");
    return;
  }
  if (!Wire.begin(CAMERA_SDA, CAMERA_SCL, 100000)) {
    Serial.println("[ERROR] Could not initialise SCCB bus");
    return;
  }
  Wire.setTimeOut(100);
  runProbes();
}

void loop() {
  if (Serial.available() && Serial.read() == 'r') runProbes();
  delay(10);
}
