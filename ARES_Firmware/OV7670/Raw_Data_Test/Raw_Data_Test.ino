#include <Arduino.h>
#include "esp_camera.h"

// Stage 1 + Stage 2 Pin Mapping
#define CAM_PIN_PWDN    -1  // Tied to GND in hardware
#define CAM_PIN_RESET   -1  // Tied to 3V3 in hardware
#define CAM_PIN_XCLK    15
#define CAM_PIN_SIOD    4
#define CAM_PIN_SIOC    5

#define CAM_PIN_D7      16
#define CAM_PIN_D6      17
#define CAM_PIN_D5      18
#define CAM_PIN_D4      12
#define CAM_PIN_D3      11
#define CAM_PIN_D2      10
#define CAM_PIN_D1      9
#define CAM_PIN_D0      8

#define CAM_PIN_VSYNC   6
#define CAM_PIN_HREF    7
#define CAM_PIN_PCLK    13

void setup() {
  Serial.begin(115200);
  delay(2000);
  Serial.println("\n=== ARES OV7670 Stage 2: DMA Frame Capture Test ===");

  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer   = LEDC_TIMER_0;
  config.pin_d0       = CAM_PIN_D0;
  config.pin_d1       = CAM_PIN_D1;
  config.pin_d2       = CAM_PIN_D2;
  config.pin_d3       = CAM_PIN_D3;
  config.pin_d4       = CAM_PIN_D4;
  config.pin_d5       = CAM_PIN_D5;
  config.pin_d6       = CAM_PIN_D6;
  config.pin_d7       = CAM_PIN_D7;
  config.pin_xclk     = CAM_PIN_XCLK;
  config.pin_pclk     = CAM_PIN_PCLK;
  config.pin_vsync    = CAM_PIN_VSYNC;
  config.pin_href     = CAM_PIN_HREF;
  config.pin_sccb_sda = CAM_PIN_SIOD;
  config.pin_sccb_scl = CAM_PIN_SIOC;
  config.pin_pwdn     = CAM_PIN_PWDN;
  config.pin_reset    = CAM_PIN_RESET;

  config.xclk_freq_hz = 10000000;        // 10 MHz master clock
  config.pixel_format = PIXFORMAT_RGB565; // Uncompressed 16-bit color (2 bytes/pixel)
  config.frame_size   = FRAMESIZE_QVGA;   // 320x240 = 153,600 bytes per frame
  config.fb_location  = CAMERA_FB_IN_PSRAM;
  config.fb_count     = 2;                // Double buffer in 8MB OPI PSRAM
  config.grab_mode    = CAMERA_GRAB_LATEST;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("[ERROR] Camera init failed with error 0x%x\n", err);
    return;
  }

  sensor_t *s = esp_camera_sensor_get();
  Serial.printf("[OK] Camera initialized! Sensor PID: 0x%02X\n", s->id.PID);
  Serial.println("Capturing 1 frame/sec. Cover the lens with your finger to see Average Byte value drop!");
}

void loop() {
  uint32_t t0 = millis();
  
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("[ERROR] Frame buffer capture failed/timed out! Check VSYNC (GPIO 6), HREF (GPIO 7), and PCLK (GPIO 13).");
    delay(1000);
    return;
  }

  uint32_t capture_time = millis() - t0;

  // Calculate average byte value across the frame to verify light sensitivity
  uint64_t sum = 0;
  for (size_t i = 0; i < fb->len; i += 16) {
    sum += fb->buf[i];
  }
  uint8_t avg_byte = sum / (fb->len / 16);

  Serial.printf("[FRAME OK] %dx%d | Size: %u bytes | Time: %u ms | Avg Brightness Byte: %3u | Center: %02X %02X %02X %02X\n",
                fb->width, fb->height, fb->len, capture_time, avg_byte,
                fb->buf[fb->len/2], fb->buf[fb->len/2 + 1],
                fb->buf[fb->len/2 + 2], fb->buf[fb->len/2 + 3]);

  esp_camera_fb_return(fb);
  delay(1000);
}