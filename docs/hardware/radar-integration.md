# Separate radar integration — documented Bluetooth route

Reviewed and implemented 31 October 2026. Direct laptop BLE authentication and actual report capture now work; scene/accuracy/outage validation and person fusion remain pending.

## Sources and identification

- User-supplied 101010001.pdf: seven-page Seeed product sheet for 24GHz mmWave Human Static Presence Sensor for XIAO, SKU 101010001. Page 6 shows the Bluetooth and radar hardware; page 7 links the full manuals.
- [Seeed product manual](https://files.seeedstudio.com/wiki/mmwave-for-xiao/24GHz_mmWave_for_XIAO-Datasheet-V1.00.pdf), section 6.5, page 16: Bluetooth characteristics and connection rules. This fuller manual refers to 2410C.
- [Seeed protocol manual](https://files.seeedstudio.com/wiki/mmwave-for-xiao/24GHz_mmWave_for_XIAO-Usermanual-V1.00.pdf), section 2.2.14 and 2.3: authentication and reported data frames.
- [Seeed setup guide](https://wiki.seeedstudio.com/mmwave_for_xiao/): phone Bluetooth operation and optional USB-to-serial connection.
- [HLKRadarTool listing](https://play.google.com/store/apps/details?id=com.hlk.hlkradartool): the phone app communicates over Bluetooth Low Energy. The reviewed material does not establish a hosted HTTP API.

The observed advertised identity and GATT characteristics matched the receiver's checks, followed by successful permission ACK and actual reports. Exact firmware version was not queried; do not infer it from a product sheet.

## Preferred ARES route

```text
ESP32-S3 / OV7670 -- Wi-Fi images --> laptop backend
separate radar ----- Bluetooth ---> laptop backend
synthetic IR ------- local Python -> laptop backend
                                    |
                                    v
                            React evidence / 3D view
```

Radar stays separate from the ESP32. The laptop can become the BLE client; it need not read numbers from the phone screen or depend on an undocumented app API.

The full manual documents one Bluetooth central/client at a time. Disconnect HLKRadarTool from the radar before trying the laptop. The app can remain the setup/reference tool, but cannot be assumed to share an active BLE connection with our receiver.

## Documented characteristics and data

| Characteristic | Property / direction |
|---|---|
| 0000fff1-0000-1000-8000-00805f9b34fb | Read/Notify; radar to receiver |
| 0000fff2-0000-1000-8000-00805f9b34fb | Write Without Response; receiver to radar |

The documented BLE permission/password handshake precedes report streaming. After authentication, BLE carries the same framed reports as the serial protocol. This supports a common report parser with different transport adapters.

Reported fields include target state, moving/stationary distances and energies, and detection distance; engineering reports add range-gate energies. These are presence/zone observations, not person identities, camera bounding boxes or calibrated human probabilities.

## First validation sequence

1. Keep the separately powered radar near the laptop and disconnect its phone-app connection.
2. Verify that the laptop has a working BLE adapter, scan for the matching radar, and inspect the actual GATT characteristics/firmware identity.
3. Subscribe to the documented reporting characteristic and perform the permission handshake. Verify the acknowledgement and actual stream before marking the adapter connected/usable.
4. Buffer fragmented/coalesced notifications and validate complete report framing/length. Preserve raw packets with receive timestamps; do not invent a hardware capture timestamp.
5. Decode basic presence/distance/energy reports. Test empty scene, walking, stationary person, departure, disconnect, stale data and reconnect.
6. Compare against HLKRadarTool in separate runs using the same marked scene and settings. Check camera/radar scene overlap and bystanders before fusion.
7. Only after those checks, publish LIVE_EXTERNAL radar evidence and enable laptop-side camera/radar fusion. Until then use EXTERNAL / NOT INTEGRATED and camera-only assessment.

Implement a read-only data path apart from the required authentication/session commands. Protocol examples still need length/field checks against actual packets; do not treat a copied command example as a tested receiver.

## Fallback and deferred work

If BLE cannot be made reliable, the manufacturer also documents UART through a USB-to-serial adapter directly to the laptop, subject to confirmed hardware/power/logic compatibility. That fallback does not require wiring radar to the camera ESP32. No UART rewiring or purchase is presumed in the current BLE-first plan.

If neither route is ready for the demo, retain the separate radar display and clearly mark automatic integration/fusion pending. IR remains explicitly synthetic and ineligible for physical accuracy or live person-fusion claims.

## Current implementation status

The BLE receiver/handshake and bounded report parser are implemented. Targeted device discovery authenticated successfully and decoded 58 actual reports; the backend subsequently streamed real radar into React and saved 885 radar reports in a browser-operated recording. Name-filtered discovery was intermittent, so selected-device lookup uses the explicit address and does not depend on a local name being advertised.

See [backend validation](../validation/backend-2026-10-31.md). Labelled moving/stationary/empty trials, camera-zone alignment, actual outage/reconnect and calibrated external-source fusion remain pending. A verified packet stream alone does not pass those gates.
