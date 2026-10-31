# Camera SCCB identification — 31 October 2026

## User-run physical probe

The user uploaded `firmware/ares_camera_probe/ares_camera_probe.ino` and supplied
its serial output. Pins: SDA4, SCL5, XCLK15; SCCB configured at 100 kHz.
PSRAM detected: YES, total 8388608 bytes. This is a runtime capacity report,
not a memory stress test.

| Configured XCLK | Address 0x21 probe | Read method | PID / VER | Attempts |
|---|---|---|---|---|
| 8 MHz | ACK | Repeated START | No bytes received | 3/3 failed |
| 8 MHz | ACK | STOP then START | 0x76 / 0x73 | 3/3 matched |
| 20 MHz | ACK | Repeated START | No bytes received | 3/3 failed |
| 20 MHz | ACK | STOP then START | 0x76 / 0x73 | 3/3 matched |

Conclusion: sensor identification works with separate STOP/START transactions.
The repeated-START method is incompatible in this observed setup. This supports
a software transaction fix without further pin changes. The result does not
validate D0-D7, PCLK, HREF, VSYNC, capture quality, Wi-Fi or long-term reliability.

## Viewer change prepared

The working viewer has a project-local SCCB implementation in
`firmware/ares_node/src/ares_sccb`, based on a pinned official Espressif source
revision. Reads of 8-bit registers at 0x21 go directly through separate transmit
and receive calls with both errors checked. The global Arduino installation is
unchanged. Wider-register methods and other-address behaviour remain upstream.
See the folder README for revision and licensing details.

The viewer prints the selected SCCB backend, PSRAM report, camera error code,
sensor PID/VER and the first captured frame size. XCLK remains at 8 MHz to avoid
changing two variables during the first full capture attempt.

## Compile and link validation

PASS using Arduino CLI 1.5.1, core 3.3.7 and the documented ESP32S3 / 8 MB
flash / OPI PSRAM / hardware USB CDC / default_8MB configuration.

```text
Sketch uses 994547 bytes (29%) of program storage space. Maximum is 3342336 bytes.
Global variables use 63872 bytes (19%) of dynamic memory, leaving 263808 bytes for local variables. Maximum is 327680 bytes.
```

`build/camera-baseline/ares_node.ino.map` resolves `SCCB_Read` (0x42003268),
`SCCB_Init` and `ares_sccb_backend_name` to
`sketch/src/ares_sccb/sccb-ng.c.o`. The SDK archive's `sccb-ng.c.obj` is not
extracted. Root working and repository SCCB source hashes match:
`FB1094DF1603627E3421566107B132DE8F87111E5AB953AB38B0F057FA25B744`.

The agent has not uploaded this viewer build. A user-run post-fix upload is the
next check. No successful full camera initialisation or real frame is claimed
yet. Read Serial Monitor at 115200 after EN/RESET, confirm the local SCCB boot
marker, then camera initialisation, a real captured frame and a Wi-Fi address.
