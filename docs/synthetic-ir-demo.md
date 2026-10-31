# Current demo inputs and synthetic IR contract

## Confirmed scope change

- The MLX90614 is reported nonworking. Use an explicitly synthetic laptop-side provider; repair and physical thermal validation are deferred.
- Radar is separate from the ESP32. Direct BLE authentication/reporting now works; labelled scene/outage validation remains pending. No ESP32 radar UART/GPIO work is required; see [integration notes](hardware/radar-integration.md).
- ESP32 supplies the real camera feed. The laptop combines available inputs and hosts the application. Camera runtime validation is still pending.

## Source and display rules

| Input | Current source | Display / evaluation rule |
|---|---|---|
| Camera | Real ESP32 frames when connected | No placeholder image presented as live; absent frames show disconnected/stale |
| IR | Laptop synthetic provider | Persistent SYNTHETIC badge; hardware unavailable; excluded from real detection/thermal metrics |
| Radar | Separate device with documented BLE reports | Show as external/not integrated until actual laptop streaming is verified; no invented readings |

Use per-input provenance in telemetry, recordings and the UI. Label real-camera-plus-synthetic-IR sessions MIXED; never use a single LIVE label that implies the IR is measured. A valid synthetic number does not mean the physical IR sensor is working.

The adapter now supplies actual radar reports, but no person detector or automatic fused person assessment exists yet. Display the sources separately. Future camera-only versus fused assessments must retain their true scope and availability.

If external radar data become available, validate their meaning, timestamps, delay, overlap with the camera's scene and failure handling before enabling camera/radar fusion. Manual entry, if later chosen, must be labelled MANUAL and excluded from automatic sensor-performance claims.

## Implemented provider

`ground_station/ares/ir_simulator.py` uses only Python's standard library. A fixed seed and ordered scenario/time inputs reproduce the same records.

- `baseline`: illustrative room/background values.
- `warm_target`: illustrative warmer object-area values; not a simulated human classifier.
- `hot_background`: illustrative elevated-temperature context.
- `unavailable`: null temperatures and `valid=false`, for UI/error-path checks.

Each record contains scenario/version/seed, sequence, simulation elapsed time, temperatures and validity, plus fixed provenance:

```json
{
  "source": "SYNTHETIC",
  "producer": "LAPTOP",
  "hardware_status": "UNAVAILABLE",
  "eligible_for_live_fusion": false,
  "hardware_sample_time_ms": null
}
```

The backend will attach actual generation/receive timestamps in its own clock domain. Never relabel scenario elapsed time as a physical measurement timestamp. Scenario choice is separate from the operator's disaster/visibility profile; selecting fire must not manufacture corroborating temperature evidence.

## Validation and limits

- Check reproducible replay, immutable synthetic provenance, null fault samples and rejection of invalid/regressing simulation times.
- Provenance was verified through API/recording/export and the actual browser display; see the backend validation record. Further real-camera and labelled performance checks remain pending.
- Keep IR weight zero in the live person-presence path. Synthetic IR can exercise displays and separate labelled logic demonstrations; it cannot train/tune/validate the real IR sensor's human-detection value.
- Physical human-versus-phone thermal comparison is deferred. Phone/mug cases can still challenge camera or an integrated real radar, but displayed synthetic temperatures do not come from those objects.

## Next implementation batch

1. Add a FastAPI service with a single configured camera acquisition worker, bounded latest-frame storage, health/status records and the synthetic IR provider.
2. Expose configuration for the ESP32 camera URL; missing configuration/connection shows unavailable, never simulated camera frames.
3. Implement/validate the documented direct laptop BLE radar route, including device/GATT identification, permission handshake, report parsing and stale/reconnect states. Disconnect the phone app before a laptop connection; no default fake radar feed.
4. Add recording with per-input provenance and explicit missing-input states before model/fusion integration.
5. Add the minimal React viewer, then frontal person detection and the illustrative avatar. Validate at each step using ACTION_PLAN.md.

Implementation update: FastAPI, the React viewer, direct BLE radar receiver and recording/export now exist. Synthetic provenance survived a real radar/IR session, and scenario/profile controls were verified independently. See [backend validation](validation/backend-2026-10-31.md). Actual camera runtime, person detection and calibrated fusion remain pending.
