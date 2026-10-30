#include <Arduino.h>
#include <Wire.h>

#define CAM_XCLK_PIN 15
#define CAM_SDA_PIN  4
#define CAM_SCL_PIN  5
#define OV7670_ADDR  0x21 // 7-bit I2C/SCCB address of OV7670

// Helper to read a single register from OV7670 via 2-phase SCCB transaction
uint8_t readOV7670Reg(uint8_t reg) {
  Wire.beginTransmission(OV7670_ADDR);
  Wire.write(reg);
  if (Wire.endTransmission(true) != 0) { // OV7670 requires a STOP condition between write & read
    return 0xFF;
  }
  delayMicroseconds(20);
  Wire.requestFrom(OV7670_ADDR, (uint8_t)1);
  if (Wire.available()) {
    return Wire.read();
  }
  return 0xFF;
}

void setup() {
  Serial.begin(115200);
  delay(2000); // Wait for USB Serial monitor to connect
  Serial.println("\n=== ARES OV7670 Stage 1: Heartbeat & PSRAM Test ===");

  // 1. Verify N16R8 Octal PSRAM
  if (psramFound()) {
    Serial.printf("[OK] Octal PSRAM Detected! Total: %d bytes, Free: %d bytes\n", 
                  ESP.getPsramSize(), ESP.getFreePsram());
  } else {
    Serial.println("[ERROR] PSRAM NOT found! Set Tools -> PSRAM -> 'OPI PSRAM'");
  }

  // 2. Start 10 MHz Master Clock (XCLK) on GPIO 15 so OV7670 wakes up
  // Compatible with both Arduino ESP32 Core v2.x and v3.x
  #if ESP_ARDUINO_VERSION >= ESP_ARDUINO_VERSION_VAL(3, 0, 0)
    ledcAttach(CAM_XCLK_PIN, 10000000, 1); // 10 MHz, 1-bit resolution (50% duty)
    ledcWrite(CAM_XCLK_PIN, 1);
  #else
    ledcSetup(0, 10000000, 1);
    ledcAttachPin(CAM_XCLK_PIN, 0);
    ledcWrite(0, 1);
  #endif
  Serial.println("[OK] 10 MHz XCLK started on GPIO 15");
  delay(100); // Let camera internal PLL stabilize

  // 3. Initialize I2C with internal pull-ups enabled
  pinMode(CAM_SDA_PIN, INPUT_PULLUP);
  pinMode(CAM_SCL_PIN, INPUT_PULLUP);
  Wire.begin(CAM_SDA_PIN, CAM_SCL_PIN, 100000); // 100 kHz SCCB clock

  // 4. Read PID (0x0A -> expected 0x76) and VER (0x0B -> expected 0x73)
  uint8_t pid = readOV7670Reg(0x0A);
  uint8_t ver = readOV7670Reg(0x0B);

  Serial.printf("Camera Register Read -> PID: 0x%02X | VER: 0x%02X\n", pid, ver);

  if (pid == 0x76) {
    Serial.println("\n[SUCCESS] OV7670 is ALIVE and responding on SCCB bus!");
    Serial.println("Ready to proceed to Stage 2 (8-bit Parallel Data Wiring).");
  } else {
    Serial.println("\n[FAILED] Could not read 0x76 from OV7670. Check:");
    Serial.println("  1. Is XCLK firmly connected to GPIO 15?");
    Serial.println("  2. Is PWDN connected to GND and RESET connected to 3V3?");
    Serial.println("  3. Are SIOD (GPIO 4) and SIOC (GPIO 5) swapped, or needing 4.7k pull-ups to 3V3?");
  }
}

void loop() {
  delay(1000);
}