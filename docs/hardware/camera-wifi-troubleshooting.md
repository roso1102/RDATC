# Camera Wi-Fi connection — 31 October 2026

## Observations

- After the SCCB fix, the user's viewer reaches `Connecting to Wi-Fi` and prints
  buffer bit diagnostics. The current control flow requires successful camera
  initialisation and a returned frame buffer to produce those diagnostics.
  A correct visible image is still unverified.
- The user confirmed no physical antenna is connected to the WROOM-1U.
- The laptop's actual WLAN SSID matches the configured Pixel hotspot name.
  Both ignored credential headers match the user-provided configuration. No
  password is copied into this document or diagnostic logs.
- The old sketch waited indefinitely for `WL_CONNECTED`, providing no cause.

The WROOM-1U uses an external antenna connector. Attach a compatible 2.4 GHz
antenna with power disconnected, then retest. An absent antenna is a strong
candidate for poor/unusable connectivity; it is not proof of the only cause.
Source: [Espressif module datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf).

## Updated viewer diagnostics

`wifi_connection.cpp` selects station mode, scans for the configured target,
prints only matching network signal/channel/security-mode codes, and logs
association and disconnection reason codes. It does not print passwords,
neighbouring SSIDs or BSSIDs. Scan failure or an absent scan match does not
prevent a connection attempt.

The connection wait after `WiFi.begin` is limited to 30 seconds. A timeout
cancels automatic retries and leaves the web server unstarted, with an explicit
instruction to check the hardware/hotspot and press EN/RESET. This is a bounded
startup diagnostic, not a complete unattended recovery state machine. Successful
connections retain automatic reconnect and disconnect logging.

Scan visibility, association and acquiring an IP are different steps. A reason
label is a diagnostic hint: authentication/handshake failures can have multiple
causes. Preserve the numeric code when sharing results.
Reference: [Espressif Arduino Wi-Fi API](https://docs.espressif.com/projects/arduino-esp32/en/latest/api/wifi.html).

## Next hardware validation

1. Unplug USB and any other power. Attach the compatible 2.4 GHz antenna.
2. Keep the Pixel hotspot at 2.4 GHz and the laptop connected to it.
3. Open and upload the complete updated `firmware/ares_node` sketch.
4. Read Serial Monitor at 115200 after EN/RESET. Confirm `[WIFI] Diagnostics v1`.
5. Confirm target visibility, successful connection and a nonzero local IP.
6. Open the printed address and `/capture`; check image colour, geometry and
   changing pixels. Only then configure that actual URL in the ground station.

The user's initial buffer check reported bit D2 low. Recheck camera D2 to GPIO10
with power disconnected if image inspection/test-pattern capture confirms a
problem. Buffer bit variation from one frame is not an electrical continuity
test and does not independently prove a broken wire.

## Build validation

PASS: Arduino CLI 1.5.1 / ESP32 core 3.3.7 with the documented S3, 8 MB flash,
OPI PSRAM, hardware USB CDC and default_8MB settings. Program storage: 997735
bytes (29%); static RAM: 63896 bytes (19%). The link map resolves
`connectAresWiFi` to the new local helper and retains the project-local
`SCCB_Read` fix. Working and repository helper SHA256 values match:
`083AACF0248875584956E445F97AE8EF28A0FB3E8E3B68D5647DA10EEA67C26E`.

The agent has not uploaded this diagnostic build. Post-antenna connection,
timeout/disconnect behaviour on hardware and real image validation are pending.
No live image, measured Wi-Fi RSSI, camera rate or final network diagnosis is
claimed yet.

## Result after fitting the antenna — 31 October 2026

The user fitted the external 2.4 GHz antenna, uploaded the updated viewer and
reported from Serial Monitor: `Wi-Fi Connected! RSSI=-18 dBm`, `Web Server
started!` and a local address on the Pixel hotspot. Fitting the antenna resolved
the connection failure in this setup.

From the laptop, three `/capture` requests returned HTTP 200 JPEGs of 27–30 KB
in 0.27–0.46 s each. The ground-station backend was configured with that
`/capture` URL and reported camera status `READY`, available, receive age 16 ms.

**Image content is not valid yet.** The decoded 320x240 frames are dominated by
magenta/purple speckle noise with a faint bright region, consistent with
light reaching the sensor but corrupted pixel data. In RGB565, data bit D2
carries the green MSB in the high byte, so a D2 line stuck low would remove much
of the green and give a magenta cast. This matches the earlier buffer check that
reported D2 low, but it is a hypothesis: check D2 to GPIO10 continuity with power
off, then compare the OV7670 colour-bar test pattern. Detection work must not use
these frames as valid images.
