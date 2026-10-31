# OV7670 identification failure: 31 October 2026

**Probe result received:** STOP/START reads returned PID 0x76 and VER 0x73 in
all three attempts at both 8 MHz and 20 MHz. Repeated START returned no bytes
in all attempts. PSRAM reported 8388608 bytes. Keep the wiring unchanged for
the next test: the viewer now contains a project-local STOP/START fix in its
`src/ares_sccb` folder. Upload the complete `firmware/ares_node` sketch next;
do not keep running the probe when testing the viewer. See
[recorded validation](../validation/camera-sccb-2026-10-31.md).

The user successfully verified and uploaded the viewer, then supplied runtime logs:
`SCCB_Read Failed addr:0x21, reg:0x0a ... ret:259`, followed by
`Camera probe failed with error 0x106(ESP_ERR_NOT_SUPPORTED)`.

This establishes failure while reading sensor identification, before the sketch's
Wi-Fi connection. The logged data byte after a failed read is not a valid sensor
identity. The installed ESP32-S3 core 3.3.7 sdkconfig enables OV7670 support.
The log alone cannot distinguish wiring, power, clock, bus electrical issues,
sensor failure or a transaction compatibility issue.

## Physical check, with USB and any other supplies disconnected

Check camera pin labels, rather than connector positions or wire colours:

| Camera module pin | Expected connection for this sketch |
|---|---|
| 3.3V / VCC on the pictured 3.3V OV7670 module | ESP32 3V3; do not substitute 5V |
| GND | ESP32 GND |
| SIOD / SDA | GPIO4 |
| SIOC / SCL | GPIO5 |
| XCLK | GPIO15 |
| PWDN | GND |
| RESET / RST | 3V3 |

Use short, secure connections and verify breadboard rail continuity. A different
breakout must have its supply specification confirmed. RESET and PWDN are not
driven by the viewer (`-1`), so they cannot be left floating. Leave the parallel
data wires unchanged during this first identification check. Check external
SCCB pull-ups to 3.3V if fitted; do not connect those signals to 5V.

## Separate diagnostic sketch

Open `firmware/ares_camera_probe/ares_camera_probe.ino` in Arduino IDE. Use the
same verified S3 board settings, upload, then read Serial Monitor at 115200 baud
after EN/RESET. This replaces the running application until ares_node is uploaded
again. It needs no Wi-Fi credentials and does not provide a camera web server.

The probe checks address 0x21 and reads PID/VER three times with repeated START
and with STOP then START, at configured XCLK frequencies of 8 MHz and 20 MHz.
It never treats a failed read's byte as a sensor identity. Stable PID 0x76 is the
expected OV7670 identifier; a single address ACK alone is insufficient.
Configured clock frequency is not an oscilloscope measurement at the sensor.
The probe reports PSRAM separately and does not prove image capture operation.

Interpret results before changing the viewer or installed core:

- No reliable reads with either method: investigate power, reset/power-down,
  clock delivery, SDA/SCL wiring and pull-ups; an incompatible or damaged module
  remains possible. A failing method alone does not prove faulty hardware.
- STOP/START reads consistently match 0x76 but repeated START does not: evidence
  for a read-transaction compatibility problem; select a project-scoped driver
  workaround after reviewing the result, rather than editing global libraries.
- Only one clock setting works: evidence to retest the viewer at that clock;
  jumper signal integrity remains relevant.
- Both methods work reliably: move to full driver initialisation and capture
  diagnostics. Identification alone does not validate data pins or PSRAM buffers.

Espressif's OV7670 driver checks PID register 0x0A. A report of the same
read-failure pattern and separate transmit/receive workaround is in
https://github.com/espressif/esp32-camera/issues/737 . This is a diagnostic lead,
not proof that the user's hardware has the same cause.

Validation status: original viewer compiled and user-confirmed Verify succeeded;
physical viewer initialisation failed. The standalone probe compiled successfully
with core 3.3.7 and the documented S3/8MB/OPI/USB-CDC settings: 347133 bytes
program storage and 24076 bytes static RAM. Probe hardware execution is pending;
the agent has not uploaded it. No camera frame or Wi-Fi connection is verified.
