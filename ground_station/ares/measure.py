"""Measure the live ARES pipeline through the backend API.

    python -m ares.measure --duration 60 --clients 4
    python -m ares.measure --duration 90 --reset-node-at 20 --reset-port COM3

Polls /api/state at 10 Hz and reports camera frame rate and ages, detector coverage and timing,
fusion tick rate, radar report rate, and every camera outage with its recovery time. With
--clients N, N threads fetch /api/camera/frame like dashboard tabs while the node's own
frames_served counter checks that acquisition stays single-owner. --reset-node-at hard-resets the
ESP32 over USB (esptool) to time reboot and Wi-Fi rejoin recovery.

Ages use backend receive time. The node clock is not synchronised, so capture-to-receive latency
is bounded by the fetch duration (the frame is captured during the request), not measured exactly.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import threading
import time

import httpx

DEFAULT_ESPTOOL = Path.home() / "AppData/Local/Arduino15/packages/esp32/tools/esptool_py/5.1.0/esptool.exe"
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "benchmarks" / "pipeline"


def percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(fraction * (len(ordered) - 1)))]


def stats(values):
    return {"n": len(values), "p50": percentile(values, 0.5), "p95": percentile(values, 0.95),
            "max": max(values) if values else None}


def sample_from_state(t, state):
    camera, frame = state["camera"], state["camera"]["frame"] or {}
    detection, fusion, radar = state["detection"], state.get("fusion") or {}, state["radar"]
    return {
        "t": round(t, 3), "camera_status": camera["status"], "camera_available": camera["available"],
        "frame_id": frame.get("frame_id"), "receive_age_ms": camera["receive_age_ms"],
        "fetch_duration_ms": frame.get("fetch_duration_ms"), "node_uptime_ms": frame.get("node_uptime_ms"),
        "node_rssi_dbm": frame.get("node_rssi_dbm"),
        "detection_status": detection["status"], "detection_frame_id": detection["frame_id"],
        "inference_ms": detection["inference_ms"], "person_count": detection["person_count"],
        "fusion_at": fusion.get("computed_at_utc"), "decision": state["assessment"].get("decision"),
        "radar_status": radar["status"], "radar_sequence": (radar["reading"] or {}).get("sequence"),
        "radar_age_ms": radar["receive_age_ms"],
    }


def outages(samples, key="camera_status", good="READY"):
    """Intervals where `key` was not `good`, with the statuses seen and recovery duration."""
    result, current = [], None
    for sample in samples:
        if sample[key] != good and current is None:
            current = {"start_s": sample["t"], "statuses": [sample[key]]}
        elif sample[key] != good:
            if sample[key] != current["statuses"][-1]:
                current["statuses"].append(sample[key])
        elif current is not None:
            current.update(end_s=sample["t"], duration_s=round(sample["t"] - current["start_s"], 2))
            result.append(current)
            current = None
    if current is not None:
        current.update(end_s=None, duration_s=None)  # Not recovered within the run.
        result.append(current)
    return result


def first_seen(samples, key):
    """Time of first appearance of each distinct non-null value of `key`."""
    seen = {}
    for sample in samples:
        value = sample[key]
        if value is not None and value not in seen:
            seen[value] = sample["t"]
    return seen


def summarise(samples, duration_s):
    frames = first_seen(samples, "frame_id")
    detected = first_seen(samples, "detection_frame_id")
    fusion_ticks = first_seen(samples, "fusion_at")
    radar = [s["radar_sequence"] for s in samples if s["radar_sequence"] is not None]
    per_frame = {}
    for sample in samples:  # Fetch duration and inference time once per frame.
        if sample["frame_id"] and sample["frame_id"] not in per_frame:
            per_frame[sample["frame_id"]] = sample
    # Compare with the last known uptime: a reboot is usually separated by an outage of null samples.
    uptimes = [s["node_uptime_ms"] for s in samples if s["node_uptime_ms"] is not None]
    reboots = sum(1 for a, b in zip(uptimes, uptimes[1:]) if b < a)
    available = [s for s in samples if s["camera_available"]]
    decisions = [s["decision"] for s in samples]
    return {
        "duration_s": duration_s, "polls": len(samples),
        "camera": {
            "frames": len(frames), "fps": round(len(frames) / duration_s, 2) if duration_s else None,
            "available_fraction": round(len(available) / len(samples), 3) if samples else None,
            "receive_age_ms": stats([s["receive_age_ms"] for s in available if s["receive_age_ms"] is not None]),
            "fetch_duration_ms": stats([s["fetch_duration_ms"] for s in per_frame.values()
                                        if s["fetch_duration_ms"] is not None]),
            "node_rssi_dbm": stats([s["node_rssi_dbm"] for s in per_frame.values()
                                    if s["node_rssi_dbm"] is not None]),
            "node_reboots_seen": reboots,
            "outages": outages(samples),
        },
        "detection": {
            "frames_detected": len(detected),
            "coverage_of_frames": round(len(set(detected) & set(frames)) / len(frames), 3) if frames else None,
            "inference_ms": stats([s["inference_ms"] for s in samples
                                   if s["detection_status"] == "READY" and s["inference_ms"] is not None]),
            "frames_with_person": len({s["detection_frame_id"] for s in samples if s["person_count"]}),
        },
        "fusion": {
            "updates": len(fusion_ticks),
            "rate_hz": round(len(fusion_ticks) / duration_s, 2) if duration_s else None,
            "decision_changes": sum(1 for a, b in zip(decisions, decisions[1:]) if a != b),
        },
        "radar": {
            "reports": (max(radar) - min(radar)) if len(radar) > 1 else 0,
            "rate_hz": round((max(radar) - min(radar)) / duration_s, 2) if len(radar) > 1 and duration_s else None,
            "age_ms": stats([s["radar_age_ms"] for s in samples
                             if s["radar_status"] == "STREAMING" and s["radar_age_ms"] is not None]),
            "outages": outages(samples, "radar_status", "STREAMING"),
        },
    }


def node_frames_served(client, node):
    try:
        return client.get(f"{node}/health", timeout=3).json()["frames_served"]
    except (httpx.HTTPError, ValueError, KeyError):
        return None


def preview_client(base, stop, counts, index):
    with httpx.Client(timeout=3, trust_env=False) as client:
        while not stop.is_set():
            try:
                if client.get(f"{base}/api/camera/frame").status_code == 200:
                    counts[index] += 1
            except httpx.HTTPError:
                pass
            time.sleep(0.1)


def reset_node(port, esptool, start, events):
    code = subprocess.run([str(esptool), "--port", port, "--after", "hard-reset", "read-mac"],
                          capture_output=True, text=True, timeout=60).returncode
    events.append({"t": round(time.monotonic() - start, 3), "event": "esptool_exit", "code": code})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    parser.add_argument("--node", default="http://ares.local", help="node base URL for /health counters")
    parser.add_argument("--duration", type=float, default=60)
    parser.add_argument("--interval", type=float, default=0.1)
    parser.add_argument("--clients", type=int, default=0, help="concurrent dashboard-like frame readers")
    parser.add_argument("--reset-node-at", type=float, help="seconds into the run to hard-reset the ESP32")
    parser.add_argument("--reset-port", default="COM3")
    parser.add_argument("--esptool", type=Path, default=DEFAULT_ESPTOOL)
    parser.add_argument("--label", default="run")
    args = parser.parse_args(argv)

    samples, events = [], []
    stop, counts = threading.Event(), [0] * args.clients
    threads = [threading.Thread(target=preview_client, args=(args.base, stop, counts, i), daemon=True)
               for i in range(args.clients)]
    reset_thread = None
    with httpx.Client(timeout=3, trust_env=False) as client:
        served_before = node_frames_served(client, args.node)
        started_utc = datetime.now(timezone.utc).isoformat()
        for thread in threads:
            thread.start()
        start = time.monotonic()
        while (elapsed := time.monotonic() - start) < args.duration:
            if args.reset_node_at is not None and reset_thread is None and elapsed >= args.reset_node_at:
                events.append({"t": round(elapsed, 3), "event": "node_hard_reset_requested"})
                reset_thread = threading.Thread(
                    target=reset_node, args=(args.reset_port, args.esptool, start, events), daemon=True)
                reset_thread.start()
            try:
                samples.append(sample_from_state(elapsed, client.get(f"{args.base}/api/state").json()))
            except (httpx.HTTPError, ValueError) as error:
                events.append({"t": round(elapsed, 3), "event": "state_poll_failed", "error": type(error).__name__})
            time.sleep(args.interval)
        stop.set()
        for thread in threads:
            thread.join(timeout=5)
        if reset_thread:
            reset_thread.join(timeout=60)
        served_after = node_frames_served(client, args.node)

    duration = round(time.monotonic() - start, 2)
    summary = summarise(samples, duration)
    summary["clients"] = {"count": args.clients, "frames_read": sum(counts)}
    summary["node_frames_served_delta"] = (served_after - served_before
                                           if served_before is not None and served_after is not None
                                           and served_after >= served_before else None)
    result = {"label": args.label, "started_at_utc": started_utc, "base": args.base, "node": args.node,
              "settings": vars(args) | {"esptool": str(args.esptool)}, "events": events,
              "summary": summary, "samples": samples}
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"{started_utc[:19].replace(':', '')}-{args.label}.json"
    path.write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps({"saved": str(path), "events": events, "summary": summary}, indent=1))


if __name__ == "__main__":
    main()
