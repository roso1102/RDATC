# Camera build validation — 31 October 2026

## Verified environment

- Arduino CLI 1.5.1; installed ESP32 Arduino core 3.3.7.
- COM3 read-only esptool query: ESP32-S3 revision v0.2, 8 MB quad flash, 8 MB embedded PSRAM (AP_3v3), USB-Serial/JTAG.
- Board options and exact compile command: [board-config.md](../hardware/board-config.md).
- Working sketch: `firmware/ares_node/ares_node.ino`; original RDATC reference: `ARES_Firmware/OV7670/Frame_Capture_2_FPS/Frame_Capture_2_FPS.ino` at commit `e2e770a8ebfbef6a6824544be477ca15c3299e1c`.

## Initial reference-copy compile

**PASS.** The working reference copy compiled using the selected ESP32-S3/8 MB flash/OPI PSRAM configuration.

```text
Sketch uses 994755 bytes (29%) of program storage space. Maximum is 3342336 bytes.
Global variables use 63872 bytes (19%) of dynamic memory, leaving 263808 bytes for local variables. Maximum is 327680 bytes.
```

These are build/linker statistics. They do not include a measured runtime memory budget for frame buffers, JPEG conversion, network peaks or a future AI model.

The sandboxed compiler initially failed with an Illegal System DLL Relocation error. The same command completed outside the sandbox; this was a tool-execution issue, not a camera source compilation error.

## Configuration initialisation change

Changed the local `camera_config_t` declaration to `camera_config_t config = {};` so unassigned driver fields have deterministic zero values. The preserved reference was not modified.

**Follow-up compile: PASS**, using the same command and board options.

```text
Sketch uses 994751 bytes (29%) of program storage space. Maximum is 3342336 bytes.
Global variables use 63872 bytes (19%) of dynamic memory, leaving 263808 bytes for local variables. Maximum is 327680 bytes.
```

Build artifacts are in `build/camera-baseline/`. No further build or hardware-performance claim is implied by this compile result.

## Publication preparation

Wi-Fi assignments were moved from the working sketch into an ignored local `wifi_secrets.h`. The repository includes `wifi_secrets.example.h` and setup instructions instead of populated credentials. No original historical sketch or Git history was rewritten.

**Credential-include build: PASS**, with the same board options and the local header present. Output remained 994751 bytes of program storage and 63872 bytes of global variables. The publication copy was checked against the compiled working source, allowing only trailing line-whitespace cleanup.

The portable launcher returned Arduino CLI 1.5.1 both with the existing local configuration and via an executable on PATH. Staged-file checks confirmed that local credential values were absent from the new/modified publication text, local documentation links resolved, and whitespace checks passed. Existing historical files were retained; this is not a claim that repository history was scrubbed.

## Remaining gates

Later physical probe results and the compiled project-local STOP/START fix are
recorded in [SCCB validation](camera-sccb-2026-10-31.md). PSRAM is now detected
at runtime and the camera ID is readable with the working transaction method;
post-fix full capture and Wi-Fi remain pending.

- No application firmware was uploaded during these checks. Esptool temporarily ran a RAM stub for identification and reset the board.
- Runtime PSRAM initialisation/usable capacity and actual OV7670 frames remain untested here.
- Wi-Fi operation and camera wiring/power remain to be verified. Latest scope excludes physical IR acquisition (nonworking, laptop simulation) and ESP32 radar wiring. Subsequent direct radar BLE validation is recorded separately in [backend validation](backend-2026-10-31.md).
- Full phase 0 is still IN PROGRESS, and phase 1 live acquisition is not passed.
