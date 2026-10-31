import unittest

from ares.backend import PROFILES
from ares.fusion import FusionConfig, FusionEngine, camera_evidence, radar_evidence

CLEAR, REDUCED = PROFILES["clear"], PROFILES["reduced_visibility"]


def run(engine, evidence, weights=CLEAR, profile="clear", times=1):
    result = None
    for _ in range(times):
        result = engine.update(evidence, weights, profile)
    return result


class EvidenceMappingTests(unittest.TestCase):
    def test_camera_uses_best_person_score_and_zero_only_for_a_current_empty_frame(self):
        ready = {"status": "READY", "detections": [{"score": 0.4}, {"score": 0.82}]}
        self.assertEqual(camera_evidence(ready), 0.82)
        self.assertEqual(camera_evidence({"status": "READY", "detections": []}), 0.0)
        for status in ("CAMERA_UNAVAILABLE", "TEST_PATTERN", "WAITING_FOR_FRAME", "MODEL_NOT_LOADED"):
            self.assertIsNone(camera_evidence({"status": status, "detections": []}))

    def test_radar_maps_target_flag_not_raw_energy(self):
        self.assertEqual(radar_evidence(True, {"presence": True, "moving_energy": 3, "valid": True}), 1.0)
        self.assertEqual(radar_evidence(True, {"presence": False, "moving_energy": 100}), 0.0)
        self.assertIsNone(radar_evidence(False, {"presence": True}))
        self.assertIsNone(radar_evidence(True, {"presence": True, "valid": False}))


class FusionTests(unittest.TestCase):
    def test_no_inputs_is_insufficient_evidence_not_absence(self):
        result = run(FusionEngine(), {"camera": None, "radar": None})
        self.assertEqual(result["decision"], "INSUFFICIENT_EVIDENCE")
        self.assertIsNone(result["index"])
        self.assertEqual(result["coverage_status"], "NONE")
        self.assertFalse(result["index_is_probability"])

    def test_decision_needs_persistence(self):
        engine = FusionEngine()
        first = run(engine, {"camera": 0.9, "radar": 1.0})
        self.assertEqual(first["decision"], "UNCERTAIN")
        self.assertEqual((first["pending_candidate"], first["pending_count"]), ("PRESENT", 1))
        second = run(engine, {"camera": 0.9, "radar": 1.0})
        self.assertEqual(second["decision"], "POSSIBLE_PERSON")
        self.assertAlmostEqual(second["index"], 0.93)
        self.assertEqual(second["coverage_status"], "FULL")

    def test_hysteresis_holds_between_thresholds_and_needs_persistence_to_clear(self):
        engine = FusionEngine()
        run(engine, {"camera": 0.9, "radar": 1.0}, times=2)
        self.assertEqual(run(engine, {"camera": 0.2, "radar": 1.0})["decision"], "POSSIBLE_PERSON")  # 0.44
        self.assertEqual(run(engine, {"camera": 0.0, "radar": 0.0})["decision"], "POSSIBLE_PERSON")
        self.assertEqual(run(engine, {"camera": 0.0, "radar": 0.0})["decision"], "NO_PERSON_INDICATED")

    def test_missing_radar_is_excluded_not_counted_as_absence(self):
        result = run(FusionEngine(), {"camera": 0.9, "radar": None}, times=2)
        self.assertAlmostEqual(result["index"], 0.9)  # Renormalised; not 0.7 * 0.9.
        self.assertEqual(result["coverage"], 0.7)
        self.assertEqual(result["coverage_status"], "PARTIAL")
        self.assertFalse(result["contributions"]["radar"]["available"])
        self.assertIsNone(result["contributions"]["radar"]["contribution"])

    def test_partial_coverage_never_claims_a_clear_scene(self):
        result = run(FusionEngine(), {"camera": 0.0, "radar": None}, times=2)
        self.assertEqual(result["decision"], "NO_PERSON_INDICATED_PARTIAL_COVERAGE")

    def test_profiles_change_weights_and_disagreement_is_flagged(self):
        evidence = {"camera": 0.0, "radar": 1.0}  # Radar target the camera cannot see.
        clear = run(FusionEngine(), evidence, CLEAR, "clear", times=2)
        reduced = run(FusionEngine(), evidence, REDUCED, "reduced_visibility", times=2)
        self.assertAlmostEqual(clear["index"], 0.3)
        self.assertEqual(clear["decision"], "NO_PERSON_INDICATED")
        self.assertAlmostEqual(reduced["index"], 0.8)
        self.assertEqual(reduced["decision"], "POSSIBLE_PERSON")
        self.assertTrue(clear["disagreement"] and reduced["disagreement"])
        self.assertFalse(run(FusionEngine(), {"camera": 0.9, "radar": 1.0})["disagreement"])

    def test_profile_change_restarts_persistence(self):
        engine = FusionEngine()
        run(engine, {"camera": 0.9, "radar": 1.0}, times=2)
        changed = run(engine, {"camera": 0.9, "radar": 1.0}, REDUCED, "reduced_visibility")
        self.assertEqual(changed["decision"], "UNCERTAIN")
        self.assertEqual(changed["pending_count"], 1)

    def test_zero_weight_synthetic_ir_is_never_an_input(self):
        result = run(FusionEngine(), {"camera": 0.0, "radar": 0.0, "ir": 1.0}, times=2)
        self.assertNotIn("ir", result["contributions"])
        self.assertEqual(result["index"], 0.0)

    def test_invalid_configuration_is_rejected(self):
        for kwargs in ({"on_threshold": 0.3, "off_threshold": 0.5}, {"persist_updates": 0}):
            with self.assertRaises(ValueError):
                FusionConfig(**kwargs)


class DisasterProfileTests(unittest.TestCase):
    def test_priors_are_valid_and_synthetic_ir_is_applied_as_zero(self):
        from ares.backend import PROFILE_INFO, applied_weights

        self.assertEqual(set(PROFILES), set(PROFILE_INFO))
        for name, prior in PROFILES.items():
            with self.subTest(profile=name):
                self.assertAlmostEqual(sum(prior.values()), 1.0)
                self.assertTrue(all(weight >= 0 for weight in prior.values()))
                applied = applied_weights(prior)
                self.assertEqual(applied["ir"], 0.0)
                self.assertAlmostEqual(sum(applied.values()), 1.0, places=3)
                # Camera:radar ratio is kept when IR is removed.
                self.assertAlmostEqual(applied["camera"] / applied["radar"], prior["camera"] / prior["radar"], places=2)
        self.assertEqual(applied_weights(PROFILES["fire_smoke"]), {"camera": 0.1111, "radar": 0.8889, "ir": 0.0})
        self.assertEqual(applied_weights(PROFILES["clear"]), PROFILES["clear"])

    def test_disaster_profiles_drive_fusion_with_applied_weights_only(self):
        from ares.backend import applied_weights

        weights = applied_weights(PROFILES["earthquake"])
        result = run(FusionEngine(), {"camera": 0.0, "radar": 1.0, "ir": 1.0}, weights, "earthquake", times=2)
        self.assertNotIn("ir", result["contributions"])
        self.assertEqual(result["coverage_status"], "FULL")
        self.assertAlmostEqual(result["index"], 0.8421, places=3)
        self.assertEqual(result["decision"], "POSSIBLE_PERSON")
