#include <Arduino.h>
#include <WiFi.h>
#include "wifi_connection.h"

static volatile uint32_t disconnects = 0;
static volatile uint8_t last_reason = 0;
static uint32_t down_since = 0;  // millis() when the link was first seen down; 0 while connected.

static const char *disconnectHint(uint8_t reason) {
  switch (reason) {
    case WIFI_REASON_NO_AP_FOUND:
      return "Hotspot not found: check antenna, 2.4 GHz band and hotspot visibility";
    case WIFI_REASON_AUTH_FAIL:
      return "Authentication failed: check hotspot password and security compatibility";
    case WIFI_REASON_4WAY_HANDSHAKE_TIMEOUT:
    case WIFI_REASON_HANDSHAKE_TIMEOUT:
      return "Handshake timed out: check antenna/signal and hotspot credentials/security";
    case WIFI_REASON_BEACON_TIMEOUT:
      return "Hotspot beacons lost: check antenna/signal and hotspot power";
    case WIFI_REASON_NO_AP_FOUND_W_COMPATIBLE_SECURITY:
    case WIFI_REASON_NO_AP_FOUND_IN_AUTHMODE_THRESHOLD:
      return "No eligible hotspot: check its security mode";
    case WIFI_REASON_ASSOC_COMEBACK_TIME_TOO_LONG:
    case WIFI_REASON_ASSOC_FAIL:
      return "Hotspot refused association (often transient after a reboot); retrying";
    default:
      return "Inspect numeric reason; check antenna, hotspot availability and credentials";
  }
}

static bool waitForLink(uint32_t timeout_ms) {
  uint32_t started = millis(), lastReport = started;
  while (WiFi.status() != WL_CONNECTED && (uint32_t)(millis() - started) < timeout_ms) {
    delay(100);
    if ((uint32_t)(millis() - lastReport) >= 5000) {
      Serial.printf("[WIFI] Waiting: %lu s; status=%d\n",
                    (unsigned long)((millis() - started) / 1000), (int)WiFi.status());
      lastReport = millis();
    }
  }
  return WiFi.status() == WL_CONNECTED;
}

bool connectAresWiFi(const char *networkName, const char *networkPassword) {
  Serial.println("\n[WIFI] Diagnostics v2; 3 attempts of 20 s, then reboot.");
  Serial.println("[WIFI] WROOM-1U needs its external 2.4 GHz antenna connected.");
  if (!WiFi.mode(WIFI_STA)) {
    Serial.println("[ERROR] Could not enable Wi-Fi station mode.");
    return false;
  }

  // Print only the configured target's results, not neighbouring network names.
  int count = WiFi.scanNetworks(false, false, false, 200);
  int matches = 0;
  if (count >= 0) {
    for (int i = 0; i < count; ++i) {
      if (WiFi.SSID(i) == networkName) {
        ++matches;
        Serial.printf("[WIFI] Target visible: RSSI=%ld dBm; channel=%ld; security code=%d\n",
                      (long)WiFi.RSSI(i), (long)WiFi.channel(i), (int)WiFi.encryptionType(i));
      }
    }
    if (!matches) Serial.println("[WARN] Configured target not found in scan; will still try connecting.");
  } else {
    Serial.printf("[WARN] Wi-Fi scan failed: %d; will still try connecting.\n", count);
  }
  WiFi.scanDelete();

  // Callback runs on the network task: only counters and thread-safe Serial output here.
  WiFi.onEvent([](arduino_event_id_t event, arduino_event_info_t info) {
    if (event == ARDUINO_EVENT_WIFI_STA_CONNECTED) {
      Serial.println("[WIFI] Associated with hotspot; waiting for an IP address.");
    } else if (event == ARDUINO_EVENT_WIFI_STA_DISCONNECTED) {
      uint8_t reason = info.wifi_sta_disconnected.reason;
      disconnects = disconnects + 1;
      last_reason = reason;
      Serial.printf("[WIFI] Disconnected: reason=%u. %s\n", reason, disconnectHint(reason));
    }
  });
  WiFi.setAutoReconnect(true);

  for (int attempt = 1; attempt <= 3; ++attempt) {
    Serial.printf("[WIFI] Connecting (attempt %d/3); password is never printed.\n", attempt);
    WiFi.begin(networkName, networkPassword);
    if (waitForLink(20000)) {
      Serial.printf("[OK] Wi-Fi Connected! RSSI=%ld dBm\n", (long)WiFi.RSSI());
      return true;
    }
    // A refused association often clears after a short pause and a fresh start.
    WiFi.disconnect(false, false);
    delay(2000 * attempt);
  }
  Serial.println("[ERROR] Wi-Fi not connected after 3 attempts; rebooting in 5 s.");
  delay(5000);
  ESP.restart();
  return false;
}

void maintainAresWiFi(uint32_t reboot_after_ms) {
  if (WiFi.status() == WL_CONNECTED) {
    down_since = 0;
    return;
  }
  if (down_since == 0) down_since = millis() | 1;
  if ((uint32_t)(millis() - down_since) > reboot_after_ms) {
    Serial.printf("[ERROR] Wi-Fi down for %lu s despite auto-reconnect; rebooting.\n",
                  (unsigned long)(reboot_after_ms / 1000));
    delay(200);
    ESP.restart();
  }
}

uint32_t aresWiFiDisconnects() { return disconnects; }
uint8_t aresWiFiLastReason() { return last_reason; }
