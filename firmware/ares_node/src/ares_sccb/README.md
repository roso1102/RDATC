# Project-local OV7670 SCCB compatibility fix

Source: Espressif esp32-camera commit
`281d951f75b6559adec3cdb8cf076366da103880`:
https://github.com/espressif/esp32-camera/tree/281d951f75b6559adec3cdb8cf076366da103880

Vendored files are `driver/sccb-ng.c` and `driver/private_include/sccb.h`.
The files carry OpenMV MIT notices, preserved with `LICENSE.sccb-MIT`;
`LICENSE.upstream` retains the repository's root license too.

The user-run ARES probe read PID 0x76 / VER 0x73 three times with STOP/START
at each XCLK setting (8 MHz and 20 MHz). Repeated START returned no bytes
in all six attempts. Runtime PSRAM reported 8388608 bytes.

Local change: `SCCB_Read` uses separate `i2c_master_transmit` and
`i2c_master_receive` calls for 8-bit register reads at address 0x21. It checks
both return codes and returns zero on failure. Other addresses retain the
upstream repeated-START-first / STOP-START-fallback implementation. Wider
register accessors are unchanged. This is specific to the current OV7670 demo.

Arduino builds sources recursively in the sketch `src` folder. The local
SCCB translation unit supplies the SCCB symbols before SDK static archives
are searched, so the SDK SCCB object is not extracted. No global toolchain
files, board properties or user-installed libraries are modified. Keep the
whole sketch folder when opening or sharing it; copying only the .ino loses
the fix. A core update requires a fresh link-map and runtime check.

The boot marker identifies this build, but the link map must independently
show SCCB_Read resolved from this folder. Full sensor initialisation, image
capture, Wi-Fi and usable frames still require a physical run after upload.
