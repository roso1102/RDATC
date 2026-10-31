"""Paper figures for a guided trial (after ares.analyse_trial has written results.json).

    python -m ares.figures ../benchmarks/trials/<folder> --out ../docs/results/figures

Writes PNG (300 dpi) and PDF for each figure. Colours: validated categorical palette (slots 1-4),
assigned to sources in a fixed order; identity is also carried by legends and labels.
"""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

from .analyse_trial import BASELINES, build_streams, load_events, replay, ts  # noqa: E402
from .backend import EDGE_PERSON_THRESHOLD, PROFILES, applied_weights  # noqa: E402

SOURCES = {"esp32": ("ESP32 on-device", "#2a78d6"), "laptop": ("Laptop YOLOX-Nano", "#eb6834"),
           "radar": ("Radar presence", "#1baf7a"), "fusion": ("Fused decision", "#eda100")}
INK, MUTED, GRID, PRESENT, OUTAGE = "#0b0b0b", "#52514e", "#e6e5e1", "#eef2f6", "#f6d8d8"

plt.rcParams.update({
    "font.size": 8, "axes.titlesize": 9, "axes.labelsize": 8, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "legend.frameon": False, "legend.fontsize": 7, "figure.dpi": 150, "savefig.bbox": "tight",
})


def save(fig, out, name):
    out.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(out / f"{name}.{ext}", dpi=300)
    plt.close(fig)


def shade(ax, segments, t0, outage=None):
    for s in segments:
        if s["person_present"]:
            ax.axvspan(s["_start"] - t0, s["_end"] - t0, color=PRESENT, lw=0, zorder=0)
    if outage:
        ax.axvspan(*outage, color=OUTAGE, lw=0, zorder=0, hatch="////", alpha=0.6)


def timeline(trial, out):
    segs, t0, camera, radar, telemetry, outage = trial["segments"], trial["t0"], trial["camera"], trial["radar"], trial["telemetry"], trial["outage"]
    fig, axes = plt.subplots(3, 1, figsize=(7.2, 4.6), sharex=True, gridspec_kw={"height_ratios": [1.3, 0.7, 1.1]})
    ax = axes[0]
    shade(ax, segs, t0, outage)
    ax.plot([c["t"] - t0 for c in camera if c["edge_score"] is not None],
            [c["edge_score"] for c in camera if c["edge_score"] is not None], "o", ms=2.6, color=SOURCES["esp32"][1],
            label="ESP32 person score")
    ax.plot([c["t"] - t0 for c in camera if c["laptop_score"] is not None],
            [c["laptop_score"] for c in camera if c["laptop_score"] is not None], "s", ms=2.4, color=SOURCES["laptop"][1],
            label="Laptop best box score")
    ax.axhline(EDGE_PERSON_THRESHOLD, color=MUTED, lw=0.8, ls="--")
    ax.set_ylim(-0.05, 1.05); ax.set_ylabel("Camera score")
    ax.legend(loc="upper left", ncol=2, bbox_to_anchor=(0, 1.32))
    for s in segs:  # Step numbers along the top.
        ax.text((s["_start"] + s["_end"]) / 2 - t0, 1.07, str(s["index"]), ha="center", va="bottom", fontsize=7, color=MUTED,
                transform=ax.get_xaxis_transform())

    ax = axes[1]
    shade(ax, segs, t0, outage)
    ax.step([r["t"] - t0 for r in radar], [int(r["presence"]) for r in radar], where="post", lw=1.2, color=SOURCES["radar"][1])
    ax.set_ylim(-0.15, 1.15); ax.set_yticks([0, 1]); ax.set_yticklabels(["none", "target"]); ax.set_ylabel("Radar")

    ax = axes[2]
    shade(ax, segs, t0, outage)
    ticks = trial["replay"]["clear"]
    ax.plot([k["t"] - t0 for k in ticks], [k["index"] if k["index"] is not None else float("nan") for k in ticks],
            lw=1.6, color=SOURCES["fusion"][1], label="Fusion index (clear profile)")
    present = [k["t"] - t0 for k in ticks if k["decision"] == "POSSIBLE_PERSON"]
    ax.plot(present, [1.08] * len(present), "|", ms=5, color=INK, label="Decision: possible person")
    ax.axhline(0.5, color=MUTED, lw=0.8, ls="--"); ax.axhline(0.3, color=MUTED, lw=0.8, ls=":")
    ax.set_ylim(-0.05, 1.15); ax.set_ylabel("Fusion"); ax.set_xlabel("Time since step 1 (s)")
    ax.legend(loc="lower left", ncol=2, fontsize=6.5)
    handles = [Patch(color=PRESENT, label="Person present (ground truth)"), Patch(facecolor=OUTAGE, hatch="////", label="Camera link outage")]
    fig.legend(handles=handles, loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.03))
    ax.set_xlim(0, segs[-1]["_end"] - t0)
    save(fig, out, "fig1_timeline")


def by_condition(results, out):
    segs = results["segments"]
    keys = [("esp32_tflm", "esp32"), ("laptop_yolox", "laptop"), ("radar", "radar"), ("fusion_live", "fusion")]
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    width = 0.19
    for i, (result_key, source) in enumerate(keys):
        values = [results["per_condition"][result_key][s["id"]]["positive_rate"] or 0 for s in segs]
        xs = [j + (i - 1.5) * (width + 0.01) for j in range(len(segs))]
        ax.bar(xs, values, width=width, color=SOURCES[source][1], label=SOURCES[source][0], edgecolor="white", linewidth=0.5)
    ax.set_xticks(range(len(segs)))
    ax.set_xticklabels([f"{s['index']}. {s['condition']}\n({'person' if s['person_present'] else 'no person'})" for s in segs],
                       rotation=35, ha="right", fontsize=6.5)
    for j, s in enumerate(segs):
        if not s["person_present"]:
            ax.axvspan(j - 0.5, j + 0.5, color="#f4f4f2", lw=0, zorder=0)
    ax.set_ylim(0, 1.05); ax.set_ylabel("Share of observations\nreporting a person")
    ax.legend(ncol=4, loc="lower left", bbox_to_anchor=(0, 1.01))
    save(fig, out, "fig2_by_condition")


def profiles(results, out):
    order = ["clear", "flood", "fire_no_smoke", "reduced_visibility", "fire_smoke", "earthquake", "camera_only", "radar_only"]
    names = {"clear": "Clear", "flood": "Flood", "fire_no_smoke": "Fire,\nno smoke", "reduced_visibility": "Reduced\nvisibility",
             "fire_smoke": "Fire +\nsmoke", "earthquake": "Earthquake", "camera_only": "Camera\nonly", "radar_only": "Radar\nonly"}
    metrics = [("precision", "Precision", SOURCES["esp32"][1]), ("recall", "Recall", SOURCES["laptop"][1]),
               ("false_alert_rate", "False-alert rate", SOURCES["radar"][1])]
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    width = 0.25
    for i, (key, label, colour) in enumerate(metrics):
        values = [results["fusion_profiles"][p][key] or 0 for p in order]
        ax.bar([j + (i - 1) * (width + 0.02) for j in range(len(order))], values, width=width, color=colour, label=label,
               edgecolor="white", linewidth=0.5)
    for j, p in enumerate(order):
        f1 = results["fusion_profiles"][p]["f1"]
        ax.text(j, 1.03, f"F1 {f1:.2f}", ha="center", fontsize=6.5, color=INK)
    w = {p: results["fusion_profiles"][p]["weights"] for p in order}
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels([f"{names[p]}\n{w[p]['camera']:.2f}/{w[p]['radar']:.2f}" for p in order], fontsize=6.5)
    ax.axvline(5.5, color=MUTED, lw=0.8, ls=":")
    ax.set_ylim(0, 1.12); ax.set_ylabel("Rate")
    ax.legend(ncol=3, loc="lower left", bbox_to_anchor=(0, 1.01))
    save(fig, out, "fig3_profiles")


def latency(trial, out):
    camera = trial["camera"]
    edge = [c["edge_infer_ms"] for c in camera if c["edge_infer_ms"] is not None]
    prep = [c["edge_prep_ms"] for c in camera if c["edge_prep_ms"] is not None]
    laptop = [c["laptop_ms"] for c in camera if c["laptop_ms"] is not None]
    fetch = [c["fetch_ms"] for c in camera if c["fetch_ms"] is not None]
    fig, (left, right) = plt.subplots(1, 2, figsize=(7.2, 2.6), gridspec_kw={"width_ratios": [1.4, 1]})
    parts = left.boxplot([edge, prep, laptop], orientation="horizontal", widths=0.5, patch_artist=True, showfliers=True,
                         flierprops={"markersize": 2, "markeredgecolor": MUTED})
    for patch, colour in zip(parts["boxes"], [SOURCES["esp32"][1], SOURCES["esp32"][1], SOURCES["laptop"][1]]):
        patch.set_facecolor(colour); patch.set_alpha(0.85); patch.set_edgecolor(INK)
    for median in parts["medians"]:
        median.set_color(INK)
    left.set_yticklabels(["ESP32 inference", "ESP32 pre-process", "Laptop inference"])
    left.set_xlabel("Milliseconds per frame"); left.set_title("Inference time", loc="left")
    right.hist(fetch, bins=20, color=SOURCES["esp32"][1], edgecolor="white", linewidth=0.5)
    right.set_xlabel("Milliseconds"); right.set_ylabel("Frames")
    right.set_title("Node request: capture + on-device\ninference + JPEG", loc="left")
    save(fig, out, "fig4_latency")


def degradation(supplementary, out):
    rows = [("Camera only", "camera_only"), ("Fusion (clear)", "clear"), ("Radar only", "radar_only")]
    fig, ax = plt.subplots(figsize=(3.5, 2.4))
    width = 0.36
    during = [supplementary[f"{k}_during_outage"]["recall"] for _, k in rows]
    outside = [supplementary[f"{k}_outside_outage"]["recall"] for _, k in rows]
    ax.bar([j - width / 2 - 0.01 for j in range(3)], outside, width, color=SOURCES["esp32"][1], label="Camera available")
    ax.bar([j + width / 2 + 0.01 for j in range(3)], during, width, color=SOURCES["laptop"][1], label="During 30 s camera outage")
    for j, (a, b) in enumerate(zip(outside, during)):
        ax.text(j - width / 2 - 0.01, a + 0.02, f"{a:.2f}", ha="center", fontsize=6.5, color=INK)
        ax.text(j + width / 2 + 0.01, b + 0.02, f"{b:.2f}", ha="center", fontsize=6.5, color=INK)
    ax.set_xticks(range(3)); ax.set_xticklabels([r[0] for r in rows])
    ax.set_ylim(0, 1.15); ax.set_ylabel("Recall")
    ax.legend(loc="upper left", bbox_to_anchor=(0, 1.22), ncol=1)
    save(fig, out, "fig5_degradation")


def load_trial(trial_dir):
    protocol = json.loads((trial_dir / "protocol.json").read_text(encoding="utf-8"))
    segments = protocol["segments"]
    for s in segments:
        s["_start"], s["_end"] = ts(s["start_utc"]), ts(s["end_utc"])
    camera, radar, telemetry = build_streams(load_events(protocol["session_id"]))
    t0 = segments[0]["_start"]
    start_offset = segments[0]["start_s"]
    pipeline = json.loads((trial_dir / "pipeline.json").read_text(encoding="utf-8"))
    outages = pipeline["camera"]["outages"]
    outage = (outages[0]["start_s"] - start_offset, (outages[0]["end_s"] or segments[-1]["end_s"]) - start_offset) if outages else None
    start, end = segments[0]["_start"], segments[-1]["_end"]
    return {"segments": segments, "t0": t0, "camera": camera, "radar": radar, "telemetry": telemetry, "outage": outage,
            "replay": {"clear": replay(camera, radar, start, end, applied_weights(PROFILES["clear"]), "clear")}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("trial_dir")
    parser.add_argument("--out", default=str(Path(__file__).resolve().parents[2] / "docs" / "results" / "figures"))
    args = parser.parse_args(argv)
    trial_dir, out = Path(args.trial_dir), Path(args.out)
    results = json.loads((trial_dir / "results.json").read_text(encoding="utf-8"))
    trial = load_trial(trial_dir)
    timeline(trial, out)
    by_condition(results, out)
    profiles(results, out)
    latency(trial, out)
    supplementary = trial_dir / "supplementary.json"
    if supplementary.exists():
        degradation(json.loads(supplementary.read_text(encoding="utf-8")), out)
    print(f"Figures written to {out}")


if __name__ == "__main__":
    main()
