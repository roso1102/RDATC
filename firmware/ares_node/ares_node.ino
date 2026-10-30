#include <Arduino.h>
#include <WiFi.h>
#include "esp_camera.h"
#include "esp_http_server.h"

// ================= WIFI CREDENTIALS =================
#include "wifi_secrets.h"
// ====================================================

// Stage 1 + Stage 2 Pin Mapping
#define CAM_PIN_PWDN    -1
#define CAM_PIN_RESET   -1
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

httpd_handle_t camera_httpd = NULL;

// Diagnostic function: checks if all 8 data pins (D0-D7) toggle across a frame
void checkDataPins(camera_fb_t *fb) {
  uint8_t seen_high = 0;
  uint8_t seen_low  = 0;
  for (size_t i = 0; i < fb->len; i++) {
    seen_high |= fb->buf[i];
    seen_low  |= ~(fb->buf[i]);
  }
  uint8_t toggling = seen_high & seen_low;
  Serial.println("\n--- D0-D7 Parallel Data Pin Health Check ---");
  for (int bit = 0; bit < 8; bit++) {
    bool ok = (toggling >> bit) & 0x01;
    bool hi = (seen_high >> bit) & 0x01;
    Serial.printf("  Pin D%d : %s\n", bit,
                  ok ? "[OK - Toggling]" : (hi ? "[STUCK HIGH]" : "[STUCK LOW - Check Wire!]"));
  }
  Serial.println("--------------------------------------------\n");
}

// HTTP Handler: Captures raw RGB565 frame, converts to JPEG in software, sends to browser
static esp_err_t capture_handler(httpd_req_t *req) {
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("[ERROR] Camera capture failed");
    httpd_resp_send_500(req);
    return ESP_FAIL;
  }

  // Convert uncompressed RGB565 buffer to JPEG (Quality: 80 out of 100)
  uint8_t *jpg_buf = NULL;
  size_t jpg_len = 0;
  bool converted = frame2jpg(fb, 80, &jpg_buf, &jpg_len);

  // Return raw RGB565 buffer to PSRAM pool immediately
  esp_camera_fb_return(fb);

  if (!converted) {
    Serial.println("[ERROR] Software RGB565 -> JPEG conversion failed");
    httpd_resp_send_500(req);
    return ESP_FAIL;
  }

  httpd_resp_set_type(req, "image/jpeg");
  httpd_resp_set_hdr(req, "Content-Disposition", "inline; filename=capture.jpg");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  esp_err_t res = httpd_resp_send(req, (const char *)jpg_buf, jpg_len);

  free(jpg_buf); // Free temporary JPEG buffer
  return res;
}

// HTTP Handler: Main HTML Dashboard (auto-refreshes at ~2 FPS)
static esp_err_t index_handler(httpd_req_t *req) {
  const char* html =
    "<!DOCTYPE html><html><head><title>ARES OV7670 Viewer</title>"
    "<meta name='viewport' content='width=device-width, initial-scale=1'>"
    "<style>body{background:#121212;color:#eee;font-family:sans-serif;text-align:center;padding:20px;}"
    "img{border:3px solid #00e676;border-radius:8px;width:320px;height:240px;image-rendering:pixelated;}"
    ".btn{background:#00e676;color:#000;border:none;padding:10px 20px;font-weight:bold;border-radius:5px;cursor:pointer;margin:10px;}</style>"
    "</head><body>"
    "<h2>Project ARES - OV7670 Live Snapshot Feed</h2>"
    "<p>Resolution: 320x240 (QVGA RGB565) | Refresh Rate: ~2 FPS</p>"
    "<img id='cam' src='/capture' /><br>"
    "<button class='btn' onclick='toggleStream()' id='btn'>Pause Auto-Refresh</button>"
    "<script>"
    "let streaming = true;"
    "const img = document.getElementById('cam');"
    "img.onload = () => { if(streaming) setTimeout(() => { img.src = '/capture?t=' + Date.now(); }, 500); };"
    "img.onerror = () => { if(streaming) setTimeout(() => { img.src = '/capture?t=' + Date.now(); }, 1000); };"
    "function toggleStream() { streaming = !streaming; document.getElementById('btn').innerText = streaming ? 'Pause Auto-Refresh' : 'Resume Auto-Refresh'; if(streaming) img.src = '/capture?t=' + Date.now(); }"
    "</script></body></html>";
  httpd_resp_set_type(req, "text/html");
  return httpd_resp_send(req, html, strlen(html));
}

void startCameraServer() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 80;

  httpd_uri_t index_uri = { .uri = "/", .method = HTTP_GET, .handler = index_handler, .user_ctx = NULL };
  httpd_uri_t capture_uri = { .uri = "/capture", .method = HTTP_GET, .handler = capture_handler, .user_ctx = NULL };

  if (httpd_start(&camera_httpd, &config) == ESP_OK) {
    httpd_register_uri_handler(camera_httpd, &index_uri);
    httpd_register_uri_handler(camera_httpd, &capture_uri);
    Serial.println("[OK] Web Server started!");
  }
}

void setup() {
  Serial.begin(115200);
  delay(2000);
  Serial.println("\n=== ARES OV7670 Stage 3: Live Web Viewer & Pin Diagnostic ===");

  camera_config_t config = {};  // Initialise optional driver fields deterministically.
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

  // 8 MHz XCLK improves breadboard jumper wire signal integrity
  config.xclk_freq_hz = 8000000;
  config.pixel_format = PIXFORMAT_RGB565;
  config.frame_size   = FRAMESIZE_QVGA;
  config.fb_location  = CAMERA_FB_IN_PSRAM;
  config.fb_count     = 2;
  config.grab_mode    = CAMERA_GRAB_LATEST;

  if (esp_camera_init(&config) != ESP_OK) {
    Serial.println("[ERROR] Camera init failed!");
    return;
  }

  // Optional OV7670 sensor tweaks for better color & breadboard stability
  sensor_t *s = esp_camera_sensor_get();
  s->set_colorbar(s, 0); // Set to 1 if you want to display the internal OV7670 8-color test pattern!

  // Grab one test frame and verify all 8 data pins (D0-D7) are toggling
  camera_fb_t *fb = esp_camera_fb_get();
  if (fb) {
    checkDataPins(fb);
    esp_camera_fb_return(fb);
  }

  // Connect to Wi-Fi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n[OK] Wi-Fi Connected!");

  startCameraServer();

  Serial.print("\n>>> Open this URL in your browser: http://");
  Serial.println(WiFi.localIP());
}

void loop() {
  delay(1000);
}
