#include <Arduino.h>
#include <ESP_TF.h>
#include "esp_heap_caps.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/schema/schema_generated.h"
#include "edge_person.h"
#include "person_detect_model.h"

namespace {
constexpr int kSide = 96;             // Model input is 96 x 96 x 1.
constexpr int kPersonIndex = 1;       // Output order: [no person, person].
constexpr size_t kArenaSize = 128 * 1024;  // Measured use 122,572 bytes; ~8.5 KB margin.

tflite::MicroInterpreter *interpreter = nullptr;
uint8_t *arena = nullptr;
const char *status = "not started";
const char *arena_location = "none";

// RGB565 as delivered by the camera driver: high byte first.
inline uint8_t luminance(const uint8_t *pixel) {
  uint16_t value = (pixel[0] << 8) | pixel[1];
  uint8_t r5 = value >> 11, g6 = (value >> 5) & 0x3F, b5 = value & 0x1F;
  uint32_t r = (r5 << 3) | (r5 >> 2), g = (g6 << 2) | (g6 >> 4), b = (b5 << 3) | (b5 >> 2);
  return (77 * r + 150 * g + 29 * b) >> 8;
}
}  // namespace

bool edgePersonBegin() {
  const tflite::Model *model = tflite::GetModel(g_person_detect_model);
  if (model->version() != TFLITE_SCHEMA_VERSION) {
    status = "model schema mismatch";
    return false;
  }
  // Internal RAM is faster for the ESP-NN kernels; fall back to PSRAM if it is short.
  arena = (uint8_t *)heap_caps_aligned_alloc(16, kArenaSize, MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
  arena_location = "internal";
  if (!arena) {
    arena = (uint8_t *)heap_caps_aligned_alloc(16, kArenaSize, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
    arena_location = "psram";
  }
  if (!arena) {
    status = "no memory for tensor arena";
    arena_location = "none";
    return false;
  }
  static tflite::MicroMutableOpResolver<5> resolver;
  resolver.AddAveragePool2D();
  resolver.AddConv2D();
  resolver.AddDepthwiseConv2D();
  resolver.AddReshape();
  resolver.AddSoftmax();
  static tflite::MicroInterpreter static_interpreter(model, resolver, arena, kArenaSize);
  if (static_interpreter.AllocateTensors() != kTfLiteOk) {
    status = "tensor allocation failed";
    return false;
  }
  TfLiteTensor *input = static_interpreter.input(0);
  if (input->type != kTfLiteInt8 || input->bytes != kSide * kSide) {
    status = "unexpected model input";
    return false;
  }
  interpreter = &static_interpreter;
  status = "ready";
  TfLiteTensor *output = interpreter->output(0);
  Serial.printf("[EDGE] person_detect ready: arena %s, %u / %u bytes; input scale %.5f zp %ld; "
                "output scale %.5f zp %ld\n", arena_location, (unsigned)interpreter->arena_used_bytes(),
                (unsigned)kArenaSize, input->params.scale, (long)input->params.zero_point,
                output->params.scale, (long)output->params.zero_point);
  return true;
}

EdgePersonResult edgePersonRun(const camera_fb_t *fb) {
  EdgePersonResult result = {false, 0.0f, 0, 0};
  if (!interpreter || fb->format != PIXFORMAT_RGB565) return result;

  uint32_t started = millis();
  // Centre square crop, box-averaged down to 96 x 96 grayscale.
  int side = fb->width < fb->height ? fb->width : fb->height;
  int x0 = (fb->width - side) / 2, y0 = (fb->height - side) / 2;
  TfLiteTensor *input = interpreter->input(0);
  float scale = input->params.scale;
  int zero_point = input->params.zero_point;
  for (int oy = 0; oy < kSide; ++oy) {
    int sy0 = y0 + oy * side / kSide, sy1 = y0 + (oy + 1) * side / kSide;
    for (int ox = 0; ox < kSide; ++ox) {
      int sx0 = x0 + ox * side / kSide, sx1 = x0 + (ox + 1) * side / kSide;
      uint32_t sum = 0, count = 0;
      for (int sy = sy0; sy < sy1; ++sy) {
        const uint8_t *row = fb->buf + (sy * fb->width) * 2;
        for (int sx = sx0; sx < sx1; ++sx, ++count) sum += luminance(row + sx * 2);
      }
      // The model's real input range is -1..1 (scale 2/255, zero point -1), i.e. pixel/127.5 - 1.
      float normalised = (sum / (float)count) / 127.5f - 1.0f;
      int quantised = (int)lroundf(normalised / scale) + zero_point;
      input->data.int8[oy * kSide + ox] = (int8_t)constrain(quantised, -128, 127);
    }
  }
  result.prep_ms = millis() - started;

  started = millis();
  if (interpreter->Invoke() != kTfLiteOk) return result;
  result.infer_ms = millis() - started;
  TfLiteTensor *output = interpreter->output(0);
  result.score = (output->data.int8[kPersonIndex] - output->params.zero_point) * output->params.scale;
  result.ok = true;
  return result;
}

const char *edgePersonStatus() { return status; }
const char *edgePersonArena() { return arena_location; }
size_t edgePersonArenaUsed() { return interpreter ? interpreter->arena_used_bytes() : 0; }
