#include <Arduino.h>
#include <WiFi.h>
#include <ESPmDNS.h>
#include "esp_camera.h"
#include "esp_http_server.h"
#include "wifi_connection.h"
#include "edge_person.h"

extern "C" const char *ares_sccb_backend_name(void);

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

#define ARES_FIRMWARE   "ares-node-0.4"
#define EDGE_MODEL      "tflm-person-detect-int8-96"
#define ARES_HOSTNAME   "ares"  // Reachable as http://ares.local when mDNS resolves.

httpd_handle_t camera_httpd = NULL;

// Updated only from the single HTTP server task.
static uint32_t frames_served    = 0;
static uint32_t capture_failures = 0;
static bool     colorbar_on      = false;
static bool     mdns_started     = false;
static uint32_t edge_runs        = 0;
static uint32_t edge_last_ms     = 0;
// Survives software reboots (not power-off): counts consecutive camera start failures.
RTC_NOINIT_ATTR static uint32_t camera_init_failures;

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
    capture_failures++;
    Serial.println("[ERROR] Camera capture failed");
    httpd_resp_send_500(req);
    return ESP_FAIL;
  }
  // Node-clock capture marker: milliseconds since boot, not synchronised wall time.
  uint32_t captured_ms = millis();

  // On-node person inference on this exact frame, before it is JPEG-encoded and sent.
  EdgePersonResult edge = edgePersonRun(fb);
  if (edge.ok) {
    edge_runs++;
    edge_last_ms = edge.infer_ms;
  }

  // Convert uncompressed RGB565 buffer to JPEG (Quality: 80 out of 100)
  uint8_t *jpg_buf = NULL;
  size_t jpg_len = 0;
  bool converted = frame2jpg(fb, 80, &jpg_buf, &jpg_len);
  
  // Return raw RGB565 buffer to PSRAM pool immediately
  esp_camera_fb_return(fb);

  if (!converted) {
    capture_failures++;
    Serial.println("[ERROR] Software RGB565 -> JPEG conversion failed");
    httpd_resp_send_500(req);
    return ESP_FAIL;
  }

  // Header values must stay valid until httpd_resp_send returns.
  frames_served++;
  char seq_hdr[12], uptime_hdr[12], rssi_hdr[8];
  snprintf(seq_hdr, sizeof(seq_hdr), "%lu", (unsigned long)frames_served);
  snprintf(uptime_hdr, sizeof(uptime_hdr), "%lu", (unsigned long)captured_ms);
  snprintf(rssi_hdr, sizeof(rssi_hdr), "%ld", (long)WiFi.RSSI());
  char score_hdr[8], infer_hdr[12], prep_hdr[12];
  snprintf(score_hdr, sizeof(score_hdr), "%.3f", edge.score);
  snprintf(infer_hdr, sizeof(infer_hdr), "%lu", (unsigned long)edge.infer_ms);
  snprintf(prep_hdr, sizeof(prep_hdr), "%lu", (unsigned long)edge.prep_ms);

  httpd_resp_set_type(req, "image/jpeg");
  httpd_resp_set_hdr(req, "Content-Disposition", "inline; filename=capture.jpg");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  httpd_resp_set_hdr(req, "Cache-Control", "no-store");
  httpd_resp_set_hdr(req, "X-Ares-Frame-Seq", seq_hdr);
  httpd_resp_set_hdr(req, "X-Ares-Uptime-Ms", uptime_hdr);
  httpd_resp_set_hdr(req, "X-Ares-Rssi-Dbm", rssi_hdr);
  httpd_resp_set_hdr(req, "X-Ares-Test-Pattern", colorbar_on ? "1" : "0");
  httpd_resp_set_hdr(req, "X-Ares-Person-Status", edge.ok ? "ok" : "unavailable");
  if (edge.ok) {
    httpd_resp_set_hdr(req, "X-Ares-Person-Score", score_hdr);
    httpd_resp_set_hdr(req, "X-Ares-Person-Infer-Ms", infer_hdr);
    httpd_resp_set_hdr(req, "X-Ares-Person-Prep-Ms", prep_hdr);
    httpd_resp_set_hdr(req, "X-Ares-Person-Model", EDGE_MODEL);
  }
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

// HTTP Handler: node health for operators and diagnostics (JSON)
static esp_err_t health_handler(httpd_req_t *req) {
  sensor_t *s = esp_camera_sensor_get();
  char body[640];
  snprintf(body, sizeof(body),
           "{\"firmware\":\"%s\",\"hostname\":\"%s.local\",\"mdns\":%s,"
           "\"uptime_ms\":%lu,\"frames_served\":%lu,\"capture_failures\":%lu,"
           "\"rssi_dbm\":%ld,\"ip\":\"%s\",\"free_heap\":%lu,\"free_psram\":%lu,"
           "\"sensor_pid\":%u,\"test_pattern\":%s,\"time_basis\":\"NODE_UPTIME\","
           "\"edge\":{\"model\":\"%s\",\"status\":\"%s\",\"arena\":\"%s\",\"arena_used\":%u,"
           "\"runs\":%lu,\"last_infer_ms\":%lu},\"wifi_disconnects\":%lu,\"wifi_last_reason\":%u,"
           "\"reset_reason\":%d,\"min_free_heap\":%lu}",
           ARES_FIRMWARE, ARES_HOSTNAME, mdns_started ? "true" : "false",
           (unsigned long)millis(), (unsigned long)frames_served,
           (unsigned long)capture_failures, (long)WiFi.RSSI(),
           WiFi.localIP().toString().c_str(), (unsigned long)ESP.getFreeHeap(),
           (unsigned long)ESP.getFreePsram(), s ? (unsigned)s->id.PID : 0u,
           colorbar_on ? "true" : "false", EDGE_MODEL, edgePersonStatus(), edgePersonArena(),
           (unsigned)edgePersonArenaUsed(), (unsigned long)edge_runs, (unsigned long)edge_last_ms,
           (unsigned long)aresWiFiDisconnects(), (unsigned)aresWiFiLastReason(), (int)esp_reset_reason(),
           (unsigned long)ESP.getMinFreeHeap());
  httpd_resp_set_type(req, "application/json");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  httpd_resp_set_hdr(req, "Cache-Control", "no-store");
  return httpd_resp_send(req, body, strlen(body));
}

// HTTP Handler: /colorbar?on=1 shows the OV7670 test pattern; on=0 returns to the lens image.
static esp_err_t colorbar_handler(httpd_req_t *req) {
  char query[32] = {0};
  char value[4] = {0};
  if (httpd_req_get_url_query_str(req, query, sizeof(query)) != ESP_OK ||
      httpd_query_key_value(query, "on", value, sizeof(value)) != ESP_OK ||
      (strcmp(value, "0") != 0 && strcmp(value, "1") != 0)) {
    httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "Use /colorbar?on=1 or /colorbar?on=0");
    return ESP_FAIL;
  }
  sensor_t *s = esp_camera_sensor_get();
  if (!s || !s->set_colorbar || s->set_colorbar(s, value[0] == '1') != 0) {
    httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "Sensor did not accept the test-pattern setting");
    return ESP_FAIL;
  }
  colorbar_on = value[0] == '1';
  Serial.printf("[CAMERA] Test pattern %s\n", colorbar_on ? "ON" : "OFF");
  const char *body = colorbar_on ? "{\"test_pattern\":true}" : "{\"test_pattern\":false}";
  httpd_resp_set_type(req, "application/json");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  return httpd_resp_send(req, body, strlen(body));
}

void startCameraServer() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 80;
  config.max_resp_headers = 16;  // Default 8 silently drops the X-Ares-Person-* headers.

  httpd_uri_t index_uri = { .uri = "/", .method = HTTP_GET, .handler = index_handler, .user_ctx = NULL };
  httpd_uri_t capture_uri = { .uri = "/capture", .method = HTTP_GET, .handler = capture_handler, .user_ctx = NULL };
  httpd_uri_t health_uri = { .uri = "/health", .method = HTTP_GET, .handler = health_handler, .user_ctx = NULL };
  httpd_uri_t colorbar_uri = { .uri = "/colorbar", .method = HTTP_GET, .handler = colorbar_handler, .user_ctx = NULL };

  if (httpd_start(&camera_httpd, &config) == ESP_OK) {
    httpd_register_uri_handler(camera_httpd, &index_uri);
    httpd_register_uri_handler(camera_httpd, &capture_uri);
    httpd_register_uri_handler(camera_httpd, &health_uri);
    httpd_register_uri_handler(camera_httpd, &colorbar_uri);
    Serial.println("[OK] Web Server started!");
  }
}

void setup() {
  Serial.begin(115200);
  if (esp_reset_reason() == ESP_RST_POWERON) camera_init_failures = 0;  // RTC_NOINIT starts as garbage.
  delay(2000);
  Serial.println("\n=== ARES OV7670 Stage 3: Live Web Viewer & Pin Diagnostic (" ARES_FIRMWARE ") ===");
  Serial.printf("[SCCB] %s\n", ares_sccb_backend_name());
  Serial.printf("[MEMORY] PSRAM detected: %s; total bytes: %u\n",
                psramFound() ? "YES" : "NO", ESP.getPsramSize());

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

  esp_err_t camera_error = esp_camera_init(&config);
  if (camera_error != ESP_OK) {
    Serial.printf("[ERROR] Camera init failed: 0x%x (%s). Wi-Fi not started.\n",
                  (unsigned)camera_error, esp_err_to_name(camera_error));
    // A loose connector often recovers on a retry; stop after 3 so a dead camera does not bootloop.
    if (++camera_init_failures <= 3) {
      Serial.printf("[NEXT] Rebooting to retry camera (%lu/3) in 10 s.\n", (unsigned long)camera_init_failures);
      delay(10000);
      ESP.restart();
    }
    Serial.println("[NEXT] Camera failed 3 boots in a row; check wiring and press EN/RESET.");
    return;
  }
  camera_init_failures = 0;
  Serial.println("[OK] Camera initialised!");

  // Optional OV7670 sensor tweaks for better color & breadboard stability
  sensor_t *s = esp_camera_sensor_get();
  Serial.printf("[CAMERA] PID=0x%02X VER=0x%02X\n", s->id.PID, s->id.VER);
  s->set_colorbar(s, 0); // Set to 1 if you want to display the internal OV7670 8-color test pattern!

  // Load the on-node person model before Wi-Fi so its arena gets internal RAM first.
  if (!edgePersonBegin()) {
    Serial.printf("[EDGE] On-node person detection unavailable: %s\n", edgePersonStatus());
  }

  // Grab one test frame and verify all 8 data pins (D0-D7) are toggling
  camera_fb_t *fb = esp_camera_fb_get();
  if (fb) {
    Serial.printf("[FRAME] %ux%u; %u bytes\n", (unsigned)fb->width,
                  (unsigned)fb->height, (unsigned)fb->len);
    checkDataPins(fb);
    EdgePersonResult edge = edgePersonRun(fb);
    if (edge.ok) {
      Serial.printf("[EDGE] First frame: person score %.3f; prep %lu ms; inference %lu ms\n", edge.score,
                    (unsigned long)edge.prep_ms, (unsigned long)edge.infer_ms);
    }
    esp_camera_fb_return(fb);
  } else {
    Serial.println("[WARN] Camera identified but first frame capture failed.");
  }

  // Report scan/connection failures instead of waiting forever.
  if (!connectAresWiFi(ssid, password)) return;
  
  startCameraServer();

  mdns_started = MDNS.begin(ARES_HOSTNAME);
  if (mdns_started) {
    MDNS.addService("http", "tcp", 80);
    Serial.println("[OK] mDNS name: http://" ARES_HOSTNAME ".local (if the laptop resolves .local names)");
  } else {
    Serial.println("[WARN] mDNS failed to start; use the IP address below.");
  }
  Serial.println("[INFO] Endpoints: /capture  /health  /colorbar?on=1  /colorbar?on=0");

  Serial.print("\n>>> Open this URL in your browser: http://");
  Serial.println(WiFi.localIP());
}

void loop() {
  // Auto-reconnect normally restores the link; reboot if it stays down for a minute.
  if (camera_httpd) maintainAresWiFi(60000);
  delay(1000);
}
