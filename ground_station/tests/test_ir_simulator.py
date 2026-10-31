import unittest

from ares.ir_simulator import IRScenario, IRSimulator


class IRSimulatorTests(unittest.TestCase):
    def test_seeded_recordings_can_be_reproduced(self):
        first = IRSimulator(seed=17)
        replay = IRSimulator(seed=17)
        for index, scenario in enumerate(IRScenario):
            self.assertEqual(
                first.sample(scenario, index * 1000).to_record(),
                replay.sample(scenario, index * 1000).to_record(),
            )

    def test_provenance_excludes_every_scenario_from_live_fusion(self):
        simulator = IRSimulator()
        for index, scenario in enumerate(IRScenario):
            with self.subTest(scenario=scenario):
                record = simulator.sample(scenario, index * 1000).to_record()
                self.assertEqual(record["source"], "SYNTHETIC")
                self.assertEqual(record["producer"], "LAPTOP")
                self.assertEqual(record["hardware_status"], "UNAVAILABLE")
                self.assertFalse(record["eligible_for_live_fusion"])
                self.assertIsNone(record["hardware_sample_time_ms"])

    def test_unavailable_data_has_no_invented_temperature(self):
        record = IRSimulator().sample("unavailable", 0).to_record()
        self.assertFalse(record["valid"])
        self.assertIsNone(record["object_temperature_c"])
        self.assertIsNone(record["sensor_temperature_c"])

    def test_bad_input_does_not_advance_replay_state(self):
        simulator = IRSimulator(seed=7)
        reference = IRSimulator(seed=7)
        with self.assertRaises(ValueError):
            simulator.sample("unknown", 0)
        for bad_time in [-1, 1.5, True]:
            with self.subTest(time=bad_time), self.assertRaises(ValueError):
                simulator.sample("baseline", bad_time)
        self.assertEqual(
            simulator.sample("baseline", 1000),
            reference.sample("baseline", 1000),
        )
        with self.assertRaises(ValueError):
            simulator.sample("baseline", 999)
        self.assertEqual(
            simulator.sample("warm_target", 2000),
            reference.sample("warm_target", 2000),
        )


if __name__ == "__main__":
    unittest.main()
