# Synthetic IR component validation — 31 October 2026

## Scope

Validated only the standalone Python provider. The MLX90614 is reported nonworking. Radar is separate and not connected to ESP32; no radar interface, API, frontend or automatic fusion is established by these checks.

## Commands

From ground_station/:

```powershell
python -m unittest discover -s tests -v
python -m ares.ir_simulator --scenario warm_target --samples 2 --seed 42
```

## Results

**PASS: 4 unit checks**, plus successful JSON-lines smoke output.

- Identical seed and ordered scenario/time inputs reproduce identical records.
- Every scenario retains SYNTHETIC source, LAPTOP producer, UNAVAILABLE physical hardware, false live-fusion eligibility and null physical timestamp.
- The unavailable fixture returns null temperatures and valid=false, rather than invented values.
- Unknown scenarios and invalid/regressing simulation times are rejected without advancing replay state.

The numeric records are illustrative fixtures; valid means usable synthetic data, not an operational physical sensor. No physical IR detection/accuracy, real-time transport/UI label preservation or fused performance was tested. Those claims do not follow from a passing unit suite.

The next gate is FastAPI transport/recording and per-input provenance checks, alongside actual camera runtime validation. Subsequent documentation review identified a direct BLE radar protocol; physical device/GATT/stream validation is still pending and was not part of this unit suite.
