# Arduino CLI and camera setup

The camera baseline was compiled with Arduino CLI 1.5.1 and ESP32 Arduino core 3.3.7. Reusing those versions makes the recorded result reproducible; changing toolchain versions requires a fresh build check.

## Install or locate the tools

1. Install Arduino CLI from the [official installation page](https://docs.arduino.cc/arduino-cli/installation) or the [verified release version](https://github.com/arduino/arduino-cli/releases/tag/v1.5.1).
2. Either put `arduino-cli.exe` on PATH or extract it into `tools/arduino-cli/` under this repository. Executables and downloaded archives are not checked in.
3. Install ESP32 core 3.3.7 using Arduino IDE Boards Manager or the CLI. Espressif's stable board index is `https://espressif.github.io/arduino-esp32/package_esp32_index.json`.
4. Run the project launcher from the repository root:

```powershell
.\arduino-cli.cmd version
.\arduino-cli.cmd core list
.\arduino-cli.cmd board list
```

The launcher first looks for the local executable, then an executable on PATH. An optional local `arduino-cli.yaml` is used only if present. That configuration is ignored by Git because it may contain machine-specific paths. Without it, Arduino CLI uses its normal configuration.

If needed, install the core with the official index explicitly:

```powershell
.\arduino-cli.cmd core update-index --additional-urls 'https://espressif.github.io/arduino-esp32/package_esp32_index.json'
.\arduino-cli.cmd core install esp32:esp32@3.3.7 --additional-urls 'https://espressif.github.io/arduino-esp32/package_esp32_index.json'
```

## Configure the working camera sketch

```powershell
Copy-Item .\firmware\ares_node\wifi_secrets.example.h .\firmware\ares_node\wifi_secrets.h
```

Edit the copied file locally with the demonstration network's SSID and password. The populated header is ignored; do not add it to Git. The original `ARES_Firmware/` sketches are historical references, not the current credential-template workflow.

The board queried during this work had 8 MB flash and 8 MB embedded PSRAM. Use [the recorded board options](../hardware/board-config.md) for that device; a different module must be identified independently.

Compile only:

```powershell
.\arduino-cli.cmd compile --fqbn 'esp32:esp32:esp32s3:FlashSize=8M,PSRAM=opi,CDCOnBoot=cdc,USBMode=hwcdc,PartitionScheme=default_8MB' --build-path '.\build\camera-baseline' --jobs 4 --warnings default '.\firmware\ares_node'
```

Recheck the port before any upload; COM3 was the observed port on the development computer, not a portable configuration. Compilation is not validation of camera frames, usable PSRAM, connectivity or AI execution.

## Connect the camera to a hotspot

1. Put the exact hotspot SSID/password into the local ignored wifi_secrets.h. Changing this file alone does not change firmware already running on the ESP32.
2. Enable a 2.4 GHz hotspot and connect the laptop to that same network. The [ESP32-S3 supports 2.4 GHz Wi-Fi](https://www.espressif.com/products/socs/esp32-s3); a 5 GHz-only hotspot will not work with this node.
3. Compile and upload the current sketch using the recorded board/flash/PSRAM settings. Close any serial monitor before upload, then reopen it at 115200 baud.
4. Read the actual IP printed after Wi-Fi connection and HTTP-server startup. Do not guess it from the phone's hotspot address or substitute localhost for the ESP32 address.
5. Test http://ACTUAL-ESP32-IP/capture from the laptop. It should return an actual changing JPEG when refreshed.
6. Enter that /capture URL into the ARES dashboard's ESP32 capture endpoint field and apply it. The Python backend then acquires frames for the viewer.

The baseline sketch initialises the camera before joining Wi-Fi and starts its HTTP server only after association succeeds. Wrong Wi-Fi credentials can therefore leave it waiting indefinitely before the server starts. A camera initialisation error earlier in the boot log is a separate issue that new credentials will not resolve. A missing dashboard camera URL is another separate configuration step.

If an IP is printed but /capture cannot be reached, check that both devices remain on the same hotspot and test whether it permits communication between connected clients. Keep a clear distinction between association failure, camera/capture failure and backend URL configuration.

Credentials are local configuration, not project documentation or Git content. Never publish the populated header or binaries containing its values.
