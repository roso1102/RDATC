"""Provisional camera/radar evidence fusion on the laptop.

Rules (all provisional until Phase 5 calibration):
- Each source is first mapped to evidence in [0, 1]; raw radar energy/distance is never averaged.
  Camera: highest person-detection score in the current frame, 0 when the detector found nobody.
  Radar: 1 when the radar reports a target (moving or stationary), otherwise 0.
- The operator profile supplies weights. Synthetic IR has zero weight and is never an input.
- Missing or stale sources are excluded. The index is renormalised over the sources that remain,
  but coverage (the profile weight actually present) is reported, and a partial-coverage
  "no person indicated" never claims the scene is clear.
- The decision changes only after the same candidate appears on consecutive updates (persistence),
  with separate on/off thresholds (hysteresis).
The index is a weighted evidence index, not a calibrated probability.
"""

from dataclasses import dataclass

VERSION = "fusion-provisional-v1"


@dataclass(frozen=True)
class FusionConfig:
    on_threshold: float = 0.5
    off_threshold: float = 0.3
    persist_updates: int = 2
    disagreement_gap: float = 0.5

    def __post_init__(self):
        if not 0 <= self.off_threshold < self.on_threshold <= 1:
            raise ValueError("Fusion thresholds must satisfy 0 <= off < on <= 1")
        if self.persist_updates < 1:
            raise ValueError("Persistence must be at least one update")

    def to_record(self):
        return {"on_threshold": self.on_threshold, "off_threshold": self.off_threshold,
                "persist_updates": self.persist_updates, "disagreement_gap": self.disagreement_gap}


def camera_evidence(detection: dict | None) -> float | None:
    """Evidence from a current detector result; None when there is no current result."""
    if not detection or detection.get("status") != "READY":
        return None
    return max((person["score"] for person in detection["detections"]), default=0.0)


def radar_evidence(available: bool, reading: dict | None) -> float | None:
    """Evidence from a current radar report; None when radar is unavailable or the report is invalid."""
    if not available or not reading or reading.get("valid") is False:
        return None
    return 1.0 if reading.get("presence") else 0.0


class FusionEngine:
    def __init__(self, config: FusionConfig | None = None):
        self.config = config or FusionConfig()
        self.decision = "INSUFFICIENT_EVIDENCE"
        self.candidate = None
        self.candidate_count = 0
        self.profile_key = None

    def reset(self):
        self.decision = "INSUFFICIENT_EVIDENCE"
        self.candidate = None
        self.candidate_count = 0

    def _candidate(self, index):
        if index >= self.config.on_threshold:
            return "PRESENT"
        if index <= self.config.off_threshold:
            return "ABSENT"
        # Between thresholds: keep a settled present/absent state; otherwise stay uncertain.
        return self.decision if self.decision in ("PRESENT", "ABSENT") else "UNCERTAIN"

    def update(self, evidence: dict[str, float | None], weights: dict[str, float], profile_key) -> dict:
        """One fusion step. `evidence` maps source name to [0, 1] evidence or None if unavailable."""
        if profile_key != self.profile_key:
            # A new operator profile starts its own persistence history.
            self.reset()
            self.profile_key = profile_key
        eligible = {name: weight for name, weight in weights.items() if weight > 0}
        available = {name: eligible[name] for name in eligible if evidence.get(name) is not None}
        coverage = sum(available.values()) / sum(eligible.values()) if eligible else 0.0
        contributions = {
            name: {"weight": eligible[name], "evidence": evidence.get(name),
                   "available": name in available,
                   "contribution": round(eligible[name] * evidence[name], 3) if name in available else None}
            for name in eligible
        }
        if not available:
            self.reset()
            return self._result(None, coverage, contributions, False)

        index = sum(weight * evidence[name] for name, weight in available.items()) / sum(available.values())
        candidate = self._candidate(index)
        if candidate == self.candidate:
            self.candidate_count += 1
        else:
            self.candidate, self.candidate_count = candidate, 1
        if self.candidate_count >= self.config.persist_updates:
            self.decision = candidate
        elif self.decision == "INSUFFICIENT_EVIDENCE":
            self.decision = "UNCERTAIN"
        values = [evidence[name] for name in available]
        disagreement = len(values) > 1 and max(values) - min(values) >= self.config.disagreement_gap
        return self._result(index, coverage, contributions, disagreement)

    def _result(self, index, coverage, contributions, disagreement):
        full = coverage >= 0.999
        decision = self.decision
        if decision == "ABSENT":
            decision = "NO_PERSON_INDICATED" if full else "NO_PERSON_INDICATED_PARTIAL_COVERAGE"
        elif decision == "PRESENT":
            decision = "POSSIBLE_PERSON"
        return {
            "version": VERSION, "status": "PROVISIONAL_NOT_CALIBRATED",
            "decision": decision, "index": round(index, 3) if index is not None else None,
            "index_is_probability": False, "coverage": round(coverage, 3),
            "coverage_status": "NONE" if index is None else "FULL" if full else "PARTIAL",
            "disagreement": disagreement, "contributions": contributions,
            "pending_candidate": self.candidate, "pending_count": self.candidate_count,
            "config": self.config.to_record(),
        }
