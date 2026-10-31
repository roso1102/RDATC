"""Turn a guided trial (ares.trial) and its backend recording into benchmark tables.

    python -m ares.analyse_trial benchmarks/trials/<trial folder>

Writes results.json, results.md and timeline.csv into the trial folder. Ground truth comes from the
protocol timing; samples inside each segment's settle window are excluded. Every metric is per
observation of that source (camera frames, radar reports, 1 Hz fusion telemetry, 0.5 s replay ticks),
so sources with different rates are not pooled.
"""

import argparse
import bisect
import csv
from datetime import datetime
import json
from pathlib import Path
import sys

from .backend import EDGE_PERSON_THRESHOLD, PROFILE_INFO, PROFILES, applied_weights
from .fusion import FusionEngine
from .measure import stats

SESSIONS_DIR = Path(__file__).resolve().parents[2] / "benchmarks" / "sessions"
STALE_S = 3.0
REPLAY_TICK_S = 0.5
BASELINES = {"camera_only": {"camera": 1.0, "radar": 0.0, "ir": 0.0},
             "radar_only": {"camera": 0.0, "radar": 1.0, "ir": 0.0}}


def ts(value):
    return datetime.fromisoformat(value).timestamp()


def load_events(session_id, sessions_dir=SESSIONS_DIR):
    path = Path(sessions_dir) / session_id / "events.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def label_at(t, segments):
    """(segment, person_present) for time t, or None inside a settle window or outside the trial."""
    for segment in segments:
        if segment["_start"] + segment["settle_s"] <= t < segment["_end"]:
            return segment, segment["person_present"]
    return None


def confusion(pairs):
    """pairs: (predicted, actual) booleans."""
    tp = sum(p and a for p, a in pairs); fp = sum(p and not a for p, a in pairs)
    fn = sum(a and not p for p, a in pairs); tn = sum(not p and not a for p, a in pairs)
    ratio = lambda num, den: round(num / den, 3) if den else None
    precision, recall = ratio(tp, tp + fp), ratio(tp, tp + fn)
    f1 = round(2 * precision * recall / (precision + recall), 3) if precision and recall else (0.0 if precision == 0 or recall == 0 else None)
    return {"n": len(pairs), "tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": precision, "recall": recall,
            "f1": f1, "specificity": ratio(tn, tn + fp), "false_alert_rate": ratio(fp, fp + tn),
            "accuracy": ratio(tp + tn, len(pairs))}


def auc(scored):
    """ROC AUC via the Mann-Whitney statistic; scored: (score, actual)."""
    positives = [s for s, a in scored if a]; negatives = [s for s, a in scored if not a]
    if not positives or not negatives:
        return None
    wins = sum((p > n) + 0.5 * (p == n) for p in positives for n in negatives)
    return round(wins / (len(positives) * len(negatives)), 3)


def kappa(pairs):
    """Cohen's kappa between two boolean raters."""
    n = len(pairs)
    if not n:
        return None
    observed = sum(a == b for a, b in pairs) / n
    pa, pb = sum(a for a, _ in pairs) / n, sum(b for _, b in pairs) / n
    expected = pa * pb + (1 - pa) * (1 - pb)
    return round((observed - expected) / (1 - expected), 3) if expected < 1 else None


def build_streams(events):
    frames, detections, radar, telemetry = {}, {}, [], []
    for event in events:
        kind, data = event["kind"], event["data"]
        if kind == "camera_frame" and data.get("content", "SCENE") == "SCENE":
            frames[data["frame_id"]] = {"t": ts(data["received_at_utc"]), "edge": data.get("node_person"),
                                        "fetch_ms": data.get("fetch_duration_ms")}
        elif kind == "person_detection":
            detections[data["frame_id"]] = data
        elif kind == "radar_report" and data.get("valid", True):
            radar.append({"t": ts(data["received_at_utc"]), "presence": bool(data.get("presence")),
                          "moving": data.get("moving"), "distance_cm": data.get("detection_distance_cm")})
        elif kind == "telemetry":
            telemetry.append({"t": ts(data["server_time_utc"]), "decision": data["assessment"].get("decision"),
                              "index": (data.get("fusion") or {}).get("index"),
                              "profile": data["profile"]["active"]})
    camera = []
    for frame_id, frame in sorted(frames.items(), key=lambda item: item[1]["t"]):
        detection = detections.get(frame_id)
        edge = frame["edge"] if frame["edge"] and frame["edge"].get("status") == "ok" else None
        camera.append({"t": frame["t"], "frame_id": frame_id, "fetch_ms": frame["fetch_ms"],
                       "laptop_score": max((d["score"] for d in detection["detections"]), default=0.0) if detection else None,
                       "laptop_count": detection["person_count"] if detection else None,
                       "laptop_ms": detection["inference_ms"] if detection else None,
                       "edge_score": edge["score"] if edge else None,
                       "edge_infer_ms": edge["infer_ms"] if edge else None,
                       "edge_prep_ms": edge["prep_ms"] if edge else None})
    return camera, sorted(radar, key=lambda r: r["t"]), sorted(telemetry, key=lambda r: r["t"])


def latest(stream, t, times):
    index = bisect.bisect_right(times, t) - 1
    if index < 0 or t - stream[index]["t"] > STALE_S:
        return None
    return stream[index]


def replay(camera, radar, start, end, weights, profile):
    """Re-run the live fusion rules on recorded evidence at the live 0.5 s tick."""
    engine, ticks = FusionEngine(), []
    cam = [c for c in camera if c["laptop_score"] is not None]
    cam_t, radar_t = [c["t"] for c in cam], [r["t"] for r in radar]
    t = start
    while t < end:
        c, r = latest(cam, t, cam_t), latest(radar, t, radar_t)
        evidence = {"camera": c["laptop_score"] if c else None, "radar": (1.0 if r["presence"] else 0.0) if r else None}
        result = engine.update(evidence, weights, profile)
        ticks.append({"t": t, "decision": result["decision"], "index": result["index"]})
        t += REPLAY_TICK_S
    return ticks


def segment_rates(observations, segments, predicate):
    rows = {}
    for segment in segments:
        inside = [o for o in observations if segment["_start"] + segment["settle_s"] <= o["t"] < segment["_end"]]
        values = [predicate(o) for o in inside if predicate(o) is not None]
        rows[segment["id"]] = {"n": len(values), "positive_rate": round(sum(values) / len(values), 3) if values else None}
    return rows


def scored(observations, segments, predicate):
    pairs = []
    for o in observations:
        label = label_at(o["t"], segments)
        value = predicate(o)
        if label and value is not None:
            pairs.append((bool(value), label[1]))
    return pairs


def first_time(observations, start, end, predicate):
    for o in observations:
        if start <= o["t"] < end and predicate(o):
            return round(o["t"] - start, 2)
    return None


def clear_delay(observations, start, end, predicate):
    """Seconds after `start` until the predicate stays false for the rest of the window."""
    window = [o for o in observations if start <= o["t"] < end and predicate(o) is not None]
    last_positive = max((o["t"] for o in window if predicate(o)), default=None)
    return round(last_positive - start, 2) if last_positive is not None else 0.0


def analyse(trial_dir, sessions_dir=SESSIONS_DIR):
    trial_dir = Path(trial_dir)
    protocol = json.loads((trial_dir / "protocol.json").read_text(encoding="utf-8"))
    segments = protocol["segments"]
    for segment in segments:
        segment["_start"], segment["_end"] = ts(segment["start_utc"]), ts(segment["end_utc"])
    start, end = segments[0]["_start"], segments[-1]["_end"]
    camera, radar, telemetry = build_streams(load_events(protocol["session_id"], sessions_dir))

    detectors = {
        "esp32_tflm": (camera, lambda o: None if o["edge_score"] is None else o["edge_score"] >= EDGE_PERSON_THRESHOLD),
        "laptop_yolox": (camera, lambda o: None if o["laptop_count"] is None else o["laptop_count"] > 0),
        "radar": (radar, lambda o: o["presence"]),
        "fusion_live": (telemetry, lambda o: None if o["decision"] is None else o["decision"] == "POSSIBLE_PERSON"),
    }
    results = {"trial": trial_dir.name, "session_id": protocol["session_id"], "live_profile": protocol["live_profile"],
               "segments": [{k: v for k, v in s.items() if not k.startswith("_")} for s in segments],
               "detectors": {}, "per_condition": {}, "fusion_profiles": {}}

    for name, (stream, predicate) in detectors.items():
        results["detectors"][name] = confusion(scored(stream, segments, predicate))
        results["per_condition"][name] = segment_rates(stream, segments, predicate)
    for name, key in (("esp32_tflm", "edge_score"), ("laptop_yolox", "laptop_score")):
        results["detectors"][name]["roc_auc"] = auc(
            [(o[key], label_at(o["t"], segments)[1]) for o in camera if o[key] is not None and label_at(o["t"], segments)])

    both = [(o["edge_score"] >= EDGE_PERSON_THRESHOLD, o["laptop_count"] > 0) for o in camera
            if o["edge_score"] is not None and o["laptop_count"] is not None and label_at(o["t"], segments)]
    results["esp32_vs_laptop"] = {"frames": len(both), "agreement": round(sum(a == b for a, b in both) / len(both), 3) if both else None,
                                  "cohens_kappa": kappa(both)}

    profiles = {**{name: applied_weights(prior) for name, prior in PROFILES.items()}, **BASELINES}
    timeline_replay = {}
    for name, weights in profiles.items():
        ticks = replay(camera, radar, start, end, weights, name)
        timeline_replay[name] = ticks
        entry = confusion(scored(ticks, segments, lambda o: o["decision"] == "POSSIBLE_PERSON"))
        entry["weights"] = weights
        entry["status"] = PROFILE_INFO.get(name, (name, "BASELINE"))[1]
        entry["per_condition"] = segment_rates(ticks, segments, lambda o: o["decision"] == "POSSIBLE_PERSON")
        entry["decision_changes"] = sum(1 for a, b in zip(ticks, ticks[1:]) if a["decision"] != b["decision"])
        results["fusion_profiles"][name] = entry

    entry = next((s for s in segments if s["id"] == "walk"), None)
    exit_ = next((s for s in segments if s["id"] == "object_only"), None)
    results["delays_s"] = {}
    for name, (stream, predicate) in {**detectors, "fusion_replay_clear": (timeline_replay["clear"], lambda o: o["decision"] == "POSSIBLE_PERSON")}.items():
        results["delays_s"][name] = {
            "first_detection_after_entry": first_time(stream, entry["_start"], entry["_end"], lambda o: predicate(o) is True) if entry else None,
            "clear_after_exit_cue": clear_delay(stream, exit_["_start"], exit_["_end"], predicate) if exit_ else None}

    edge_infer = [o["edge_infer_ms"] for o in camera if o["edge_infer_ms"] is not None]
    edge_prep = [o["edge_prep_ms"] for o in camera if o["edge_prep_ms"] is not None]
    laptop_ms = [o["laptop_ms"] for o in camera if o["laptop_ms"] is not None]
    fetch_ms = [o["fetch_ms"] for o in camera if o["fetch_ms"] is not None]
    duration = end - start
    results["latency_ms"] = {"esp32_inference": stats(edge_infer), "esp32_preprocess": stats(edge_prep),
                             "laptop_inference": stats(laptop_ms), "node_fetch_incl_capture_inference_jpeg": stats(fetch_ms)}
    results["throughput"] = {"duration_s": round(duration, 1),
                             "camera_fps": round(len([c for c in camera if start <= c["t"] < end]) / duration, 2),
                             "radar_hz": round(len([r for r in radar if start <= r["t"] < end]) / duration, 2),
                             "esp32_results_fraction": round(len(edge_infer) / len(camera), 3) if camera else None}
    pipeline = trial_dir / "pipeline.json"
    if pipeline.exists():
        results["pipeline"] = json.loads(pipeline.read_text(encoding="utf-8"))

    write_outputs(trial_dir, results, camera, radar, telemetry, timeline_replay, segments, start)
    return results


def write_outputs(trial_dir, results, camera, radar, telemetry, timeline_replay, segments, start):
    (trial_dir / "results.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    with (trial_dir / "timeline.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["t_s", "source", "segment", "person_present", "value", "extra"])
        for o in camera:
            label = label_at(o["t"], segments)
            writer.writerow([round(o["t"] - start, 2), "esp32_score", label[0]["id"] if label else "", label[1] if label else "", o["edge_score"], o["frame_id"]])
            writer.writerow([round(o["t"] - start, 2), "laptop_best_score", label[0]["id"] if label else "", label[1] if label else "", o["laptop_score"], o["laptop_count"]])
        for o in radar:
            label = label_at(o["t"], segments)
            writer.writerow([round(o["t"] - start, 2), "radar_presence", label[0]["id"] if label else "", label[1] if label else "", int(o["presence"]), o["distance_cm"]])
        for name in ("clear", "reduced_visibility", "earthquake", "fire_smoke"):
            for o in timeline_replay[name]:
                writer.writerow([round(o["t"] - start, 2), f"fusion_index_{name}", "", "", o["index"], o["decision"]])
    (trial_dir / "results.md").write_text(markdown(results), encoding="utf-8")


def fmt(value):
    return "—" if value is None else (f"{value:.3f}".rstrip("0").rstrip(".") if isinstance(value, float) else str(value))


def markdown(r):
    lines = [f"# ARES live trial results — {r['trial']}", "",
             f"Session `{r['session_id']}`; live fusion profile `{r['live_profile']}`. Ground truth = protocol timing "
             "(person inside the marked zone); settle windows excluded. All weights/thresholds are provisional or "
             "literature priors; synthetic IR has zero applied weight and is excluded.", "",
             "## Detection performance (per observation)", "",
             "| Source | n | Precision | Recall | F1 | Specificity | False-alert rate | Accuracy | ROC-AUC |",
             "|---|---|---|---|---|---|---|---|---|"]
    names = {"esp32_tflm": "ESP32 on-device (TFLM, 96×96, score ≥ 0.5)", "laptop_yolox": "Laptop YOLOX-Nano (≥ 1 box)",
             "radar": "Radar presence flag", "fusion_live": "Fused decision (live, 1 Hz)"}
    for key, label in names.items():
        d = r["detectors"][key]
        lines.append(f"| {label} | {d['n']} | {fmt(d['precision'])} | {fmt(d['recall'])} | {fmt(d['f1'])} | "
                     f"{fmt(d['specificity'])} | {fmt(d['false_alert_rate'])} | {fmt(d['accuracy'])} | {fmt(d.get('roc_auc'))} |")
    e = r["esp32_vs_laptop"]
    lines += ["", f"ESP32 vs laptop on the same frames: {e['frames']} frames, agreement {fmt(e['agreement'])}, "
              f"Cohen's κ {fmt(e['cohens_kappa'])}.", "", "## Positive rate by condition", "",
              "| Condition | Person | " + " | ".join(names[k].split(" (")[0] for k in names) + " |",
              "|---|---|" + "---|" * len(names)]
    for s in r["segments"]:
        cells = [fmt(r["per_condition"][k][s["id"]]["positive_rate"]) for k in names]
        lines.append(f"| {s['index']}. {s['condition']} | {'yes' if s['person_present'] else 'no'} | " + " | ".join(cells) + " |")
    lines += ["", "Positive rate = share of observations reporting a person. For person-present rows this is the "
              "detection rate; for empty/object rows it is the false-alert rate.", "",
              "## Fusion under each condition profile (offline replay of recorded evidence, 0.5 s ticks)", "",
              "| Profile | Applied camera/radar | Status | Precision | Recall | F1 | False-alert rate | Decision changes |",
              "|---|---|---|---|---|---|---|---|"]
    for name, f in r["fusion_profiles"].items():
        lines.append(f"| {name} | {f['weights']['camera']:.2f} / {f['weights']['radar']:.2f} | {f['status']} | "
                     f"{fmt(f['precision'])} | {fmt(f['recall'])} | {fmt(f['f1'])} | {fmt(f['false_alert_rate'])} | {f['decision_changes']} |")
    lines += ["", "## Delays (seconds after the cue; includes the operator's movement time)", "",
              "| Source | First detection after entry cue | Last positive after exit cue |", "|---|---|---|"]
    for name, d in r["delays_s"].items():
        lines.append(f"| {name} | {fmt(d['first_detection_after_entry'])} | {fmt(d['clear_after_exit_cue'])} |")
    lat = r["latency_ms"]
    lines += ["", "## Latency and throughput", "", "| Measure | n | p50 | p95 | max |", "|---|---|---|---|---|"]
    for name, s in lat.items():
        lines.append(f"| {name.replace('_', ' ')} (ms) | {s['n']} | {fmt(s['p50'])} | {fmt(s['p95'])} | {fmt(s['max'])} |")
    t = r["throughput"]
    lines += ["", f"Duration {t['duration_s']} s; camera {t['camera_fps']} fps; radar {t['radar_hz']} Hz; "
              f"ESP32 result present on {fmt(t['esp32_results_fraction'])} of frames."]
    if "pipeline" in r:
        p = r["pipeline"]["camera"]
        lines.append(f"Backend frame age p50/p95: {fmt(p['receive_age_ms']['p50'])}/{fmt(p['receive_age_ms']['p95'])} ms; "
                     f"camera available {fmt(p['available_fraction'])} of polls; outages {len(p['outages'])}.")
    lines += ["", "## Limitations", "",
              "- One participant, one room, one ~5-minute session: results are a pilot, not a generalisable accuracy claim.",
              "- Ground truth is protocol timing, not frame-by-frame annotation; transitions are excluded via settle windows.",
              "- Fusion profile weights are provisional/literature priors and were not tuned on this session; the replay "
              "applies the live rules to the same recorded evidence.",
              "- Disaster profiles are exercised on a lab scene, not on fire, smoke, flood or rubble.",
              "- Radar presence covers a wider area than the camera; spatial alignment is unverified."]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("trial_dir")
    parser.add_argument("--sessions-dir", default=str(SESSIONS_DIR))
    args = parser.parse_args(argv)
    results = analyse(args.trial_dir, args.sessions_dir)
    sys.stdout.reconfigure(encoding="utf-8")
    print((Path(args.trial_dir) / "results.md").read_text(encoding="utf-8"))
    return results


if __name__ == "__main__":
    main()
