"""Reproducible IR demonstration values, never physical temperature evidence."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
from enum import Enum
import json
import random


class IRScenario(str, Enum):
    BASELINE = "baseline"
    WARM_TARGET = "warm_target"
    HOT_BACKGROUND = "hot_background"
    UNAVAILABLE = "unavailable"


# Illustrative fixture values only, not measurements or a calibrated heat model.
_SCENARIO_VALUES = {
    IRScenario.BASELINE: (25.0, 25.0),
    IRScenario.WARM_TARGET: (33.0, 25.0),
    IRScenario.HOT_BACKGROUND: (55.0, 27.0),
}


@dataclass(frozen=True)
class IRReading:
    sequence: int
    scenario_id: str
    scenario_elapsed_ms: int
    seed: int
    object_temperature_c: float | None
    sensor_temperature_c: float | None
    valid: bool
    source: str = field(default="SYNTHETIC", init=False)
    producer: str = field(default="LAPTOP", init=False)
    hardware_status: str = field(default="UNAVAILABLE", init=False)
    eligible_for_live_fusion: bool = field(default=False, init=False)
    hardware_sample_time_ms: None = field(default=None, init=False)
    generator_version: str = field(default="ir-sim-1", init=False)

    def to_record(self) -> dict:
        """Return a JSON-ready record with provenance attached."""
        return asdict(self)


class IRSimulator:
    """Generate explicit fixtures; the caller controls scenario and elapsed time.

    Selecting a disaster profile does not select a scenario. ``valid`` means
    the synthetic numeric sample is usable for display, not that hardware works.
    Elapsed time is a simulation clock, never a physical measurement timestamp.
    """

    def __init__(self, seed: int = 42):
        self.seed = seed
        self._random = random.Random(seed)
        self._sequence = 0
        self._last_elapsed_ms = -1

    def sample(self, scenario_id: str | IRScenario, elapsed_ms: int) -> IRReading:
        scenario = IRScenario(scenario_id)
        if isinstance(elapsed_ms, bool) or not isinstance(elapsed_ms, int):
            raise ValueError("elapsed_ms must be an integer simulation time")
        if elapsed_ms < 0 or elapsed_ms < self._last_elapsed_ms:
            raise ValueError("simulation time must be nonnegative and not regress")

        if scenario == IRScenario.UNAVAILABLE:
            object_temperature = None
            sensor_temperature = None
            valid = False
        else:
            object_base, sensor_base = _SCENARIO_VALUES[scenario]
            object_temperature = round(object_base + self._random.uniform(-0.2, 0.2), 2)
            sensor_temperature = round(sensor_base + self._random.uniform(-0.1, 0.1), 2)
            valid = True

        self._sequence += 1
        self._last_elapsed_ms = elapsed_ms
        return IRReading(
            sequence=self._sequence,
            scenario_id=scenario.value,
            scenario_elapsed_ms=elapsed_ms,
            seed=self.seed,
            object_temperature_c=object_temperature,
            sensor_temperature_c=sensor_temperature,
            valid=valid,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=[s.value for s in IRScenario], default="baseline")
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--interval-ms", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    arguments = parser.parse_args()
    if arguments.samples < 1 or arguments.interval_ms < 1:
        parser.error("samples and interval-ms must be positive")

    simulator = IRSimulator(seed=arguments.seed)
    for index in range(arguments.samples):
        reading = simulator.sample(arguments.scenario, index * arguments.interval_ms)
        print(json.dumps(reading.to_record(), sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
