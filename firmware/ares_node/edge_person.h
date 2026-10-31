#pragma once

#include <stddef.h>
#include <stdint.h>
#include "esp_camera.h"

// On-node person classification: TFLM person_detect (int8, 96x96 grayscale) on the ESP32-S3.
// Gives a person score for the whole centre crop, not boxes.
struct EdgePersonResult {
  bool ok;
  float score;        // Dequantised "person" class output, 0..1.
  uint32_t prep_ms;   // Crop, downscale and grayscale conversion.
  uint32_t infer_ms;  // Interpreter Invoke() only.
};

bool edgePersonBegin();
EdgePersonResult edgePersonRun(const camera_fb_t *fb);
const char *edgePersonStatus();   // "ready" or a short reason it is unavailable.
const char *edgePersonArena();    // "internal" or "psram".
size_t edgePersonArenaUsed();
