import unittest

from ares.analyse_trial import auc, clear_delay, confusion, first_time, kappa, label_at


class StatisticsTests(unittest.TestCase):
    def test_confusion_counts_and_rates(self):
        pairs = [(True, True)] * 8 + [(False, True)] * 2 + [(True, False)] * 1 + [(False, False)] * 9
        result = confusion(pairs)
        self.assertEqual((result["tp"], result["fn"], result["fp"], result["tn"]), (8, 2, 1, 9))
        self.assertEqual((result["precision"], result["recall"], result["specificity"]), (0.889, 0.8, 0.9))
        self.assertEqual(result["false_alert_rate"], 0.1)
        self.assertEqual(result["f1"], 0.842)

    def test_auc_matches_mann_whitney_including_ties(self):
        self.assertEqual(auc([(0.9, True), (0.8, True), (0.1, False), (0.2, False)]), 1.0)
        self.assertEqual(auc([(0.5, True), (0.5, False)]), 0.5)
        self.assertEqual(auc([(0.2, True), (0.9, False)]), 0.0)
        self.assertIsNone(auc([(0.2, True)]))

    def test_kappa_perfect_chance_and_degenerate(self):
        self.assertEqual(kappa([(True, True), (False, False)] * 5), 1.0)
        self.assertEqual(kappa([(True, True), (True, False), (False, True), (False, False)]), 0.0)
        self.assertIsNone(kappa([(True, True)] * 3))

    def test_settle_window_is_excluded_from_labels(self):
        segments = [{"_start": 0, "_end": 30, "settle_s": 5, "person_present": False},
                    {"_start": 30, "_end": 60, "settle_s": 5, "person_present": True}]
        self.assertIsNone(label_at(2, segments))
        self.assertFalse(label_at(10, segments)[1])
        self.assertIsNone(label_at(33, segments))
        self.assertTrue(label_at(40, segments)[1])
        self.assertIsNone(label_at(61, segments))

    def test_delays(self):
        stream = [{"t": t, "v": v} for t, v in ((10, False), (12, True), (14, True), (16, False), (18, False))]
        self.assertEqual(first_time(stream, 10, 20, lambda o: o["v"]), 2)
        self.assertEqual(clear_delay(stream, 10, 20, lambda o: o["v"]), 4)
