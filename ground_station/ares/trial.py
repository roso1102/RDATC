"""Guided live trial: spoken cues, timed ground-truth segments and a backend recording.

    python -m ares.trial            # 10 x 30 s protocol, about 5.5 minutes with the countdown
    python -m ares.trial --scale 0.1  # dry run with 3 s segments

The operator follows the spoken cue for each segment. Segment start/end times are written to
protocol.json and are the ground truth for ares.analyse_trial; the first `settle_s` seconds of each
segment (moving into position) are excluded from scoring. Labels say whether a person is inside the
marked zone, not what any sensor reported.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import threading
import time

import httpx

from .measure import sample_from_state, summarise

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "benchmarks" / "trials"

# id, condition, person present in the zone, settle seconds, spoken cue
PROTOCOL = [
    ("empty_start", "Empty scene", False, 5,
     "Step out of view. Leave the area in front of the sensors, at least six metres away or out of the room."),
    ("walk", "Walking", True, 5, "Walk in and move slowly left and right, about two metres in front of the camera."),
    ("stand", "Standing, frontal", True, 3, "Stand still, facing the camera, about two metres away."),
    ("far", "Standing, far", True, 5, "Step back to about three and a half metres and stand still."),
    ("side", "Standing, side view", True, 5, "Come back to two metres, turn sideways and stay still."),
    ("crouch", "Sitting or crouching", True, 5, "Sit down or crouch at about two metres and stay still."),
    ("occluded", "Partly occluded", True, 5,
     "Stand behind a chair or table so that only your upper body is visible."),
    ("camera_covered", "Camera covered", True, 8,
     "Cover the camera lens with paper or cloth, then step back to two metres and stand still."),
    ("object_only", "Object, no person", False, 8,
     "Uncover the camera. Put a bag or jacket on a chair two metres away, then leave the area."),
    ("empty_end", "Empty scene", False, 3, "Stay out of view. Final empty check."),
]


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def say(text):
    """Speak on the laptop without blocking the timer (Windows SAPI)."""
    script = ("Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
              f"$s.Rate = 0; $s.Speak('{text.replace(chr(39), '')}')")
    try:
        subprocess.Popen(["powershell", "-NoProfile", "-Command", script],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {text}", flush=True)


def sampler(client, base, stop, samples, start):
    while not stop.is_set():
        try:
            samples.append(sample_from_state(time.monotonic() - start, client.get(f"{base}/api/state").json()))
        except (httpx.HTTPError, ValueError):
            pass
        time.sleep(0.2)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    parser.add_argument("--segment-s", type=float, default=30.0)
    parser.add_argument("--scale", type=float, default=1.0, help="shrink all durations (dry runs)")
    parser.add_argument("--countdown-s", type=float, default=10.0)
    parser.add_argument("--profile", default="clear", help="live fusion profile during the trial")
    parser.add_argument("--label", default="trial")
    args = parser.parse_args(argv)
    segment_s, countdown_s = args.segment_s * args.scale, args.countdown_s * args.scale

    with httpx.Client(timeout=5, trust_env=False) as client:
        state = client.get(f"{args.base}/api/state").json()
        previous_profile = state["profile"]["active"]
        client.post(f"{args.base}/api/config/profile", json={"profile": args.profile}).raise_for_status()
        session = client.post(f"{args.base}/api/recording/start").json()["session_id"]
        samples, stop = [], threading.Event()
        start = time.monotonic()
        thread = threading.Thread(target=sampler, args=(client, args.base, stop, samples, start), daemon=True)
        thread.start()
        segments = []
        try:
            say(f"ARES trial starting in {round(countdown_s)} seconds. Get ready. First: step out of view.")
            time.sleep(countdown_s)
            for index, (segment_id, condition, present, settle_s, cue) in enumerate(PROTOCOL, 1):
                say(f"Step {index}. {cue}")
                began_utc, began = utc_now(), time.monotonic() - start
                time.sleep(segment_s)
                segments.append({"index": index, "id": segment_id, "condition": condition, "person_present": present,
                                 "settle_s": settle_s * args.scale, "start_utc": began_utc, "end_utc": utc_now(),
                                 "start_s": round(began, 3), "end_s": round(time.monotonic() - start, 3), "cue": cue})
            say("Trial complete. Thank you.")
        finally:
            stop.set()
            thread.join(timeout=3)
            client.post(f"{args.base}/api/recording/stop")
            client.post(f"{args.base}/api/config/profile", json={"profile": previous_profile})

    duration = round(time.monotonic() - start, 2)
    folder = OUTPUT_DIR / f"{datetime.now().strftime('%Y-%m-%dT%H%M%S')}-{args.label}"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "protocol.json").write_text(json.dumps({
        "session_id": session, "live_profile": args.profile, "segment_s": segment_s, "scale": args.scale,
        "ground_truth": "person present inside the marked zone, by protocol timing; settle window excluded",
        "segments": segments}, indent=1), encoding="utf-8")
    (folder / "samples.json").write_text(json.dumps(samples), encoding="utf-8")
    (folder / "pipeline.json").write_text(json.dumps(summarise(samples, duration), indent=1), encoding="utf-8")
    print(json.dumps({"trial_dir": str(folder), "session_id": session, "segments": len(segments)}, indent=1))


if __name__ == "__main__":
    main()
