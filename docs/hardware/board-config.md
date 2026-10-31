# ESP32-S3 board configuration

Verified on 31 October 2026 using esptool 5.1.0 over COM3. The query ran a temporary RAM stub and reset the board; it did not write flash firmware.

## Observed hardware

| Item | Observation |
|---|---|
| User-reported module marking | ESP32-S3-WROOM-1U, Espressif |
| Exact ordering suffix | Not supplied; do not assume N16R8 |
| Detected chip | ESP32-S3, revision v0.2 |
| Flash | 8 MB, quad interface, 3.3 V |
| Embedded PSRAM | 8 MB, AP_3v3 |
| Crystal | 40 MHz |
| USB interface | USB-Serial/JTAG |
| Port during verification | COM3; recheck after reconnecting |
| Existing Arduino ESP32 core | 3.3.7 |

The WROOM-1U uses an external antenna connector. Capacity observations above come from the connected device, rather than an inferred module suffix or the reference sketch's N16R8 comment. PSRAM initialisation and usable capacity still require a runtime firmware test.

## Selected compile configuration

| Arduino IDE option | Setting |
|---|---|
| Board | ESP32S3 Dev Module |
| Flash Size | 8MB (64Mb) |
| PSRAM | OPI PSRAM |
| USB Mode | Hardware CDC and JTAG |
| USB CDC On Boot | Enabled |
| Partition Scheme | 8M with spiffs (3MB APP/1.5MB SPIFFS) |

FQBN from the installed core's board definitions:

```text
esp32:esp32:esp32s3:FlashSize=8M,PSRAM=opi,CDCOnBoot=cdc,USBMode=hwcdc,PartitionScheme=default_8MB
```

Compile-only command from the project root, after [tool and local-credential setup](../setup/arduino-cli.md):

```powershell
.\arduino-cli.cmd compile --fqbn 'esp32:esp32:esp32s3:FlashSize=8M,PSRAM=opi,CDCOnBoot=cdc,USBMode=hwcdc,PartitionScheme=default_8MB' --build-path '.\build\camera-baseline' --jobs 4 --warnings default '.\firmware\ares_node'
```

Compile compatibility does not establish camera wiring, PSRAM runtime operation, Wi-Fi connectivity or valid images. Latest scope: physical IR is nonworking and simulated on the laptop; radar uses its own separate app/web system, not ESP32 GPIOs.

The camera working sketch compiled successfully with these options, including a follow-up build after zero-initialising its camera configuration. See [camera build validation](../validation/camera-build-2026-10-31.md).
