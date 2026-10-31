import unittest

from ares.measure import outages, percentile, summarise


def sample(t, status="READY", frame=None, uptime=None, detected=None, people=None, fusion=None,
           decision="NO_PERSON_INDICATED", radar_seq=None, radar_status="STREAMING"):
    return {"t": t, "camera_status": status, "camera_available": status == "READY", "frame_id": frame,
            "receive_age_ms": 100 if status == "READY" else None, "fetch_duration_ms": 300,
            "node_uptime_ms": uptime, "node_rssi_dbm": -50,
            "detection_status": "READY" if detected else "CAMERA_UNAVAILABLE",
            "detection_frame_id": detected, "inference_ms": 20 if detected else None,
            "person_count": people, "fusion_at": fusion, "decision": decision,
            "radar_status": radar_status, "radar_sequence": radar_seq, "radar_age_ms": 50}


class MeasureTests(unittest.TestCase):
    def test_percentile_uses_nearest_rank(self):
        self.assertEqual(percentile([5, 1, 3, 2, 4], 0.5), 3)
        self.assertEqual(percentile(list(range(1, 101)), 0.95), 95)
        self.assertIsNone(percentile([], 0.5))

    def test_outage_records_statuses_and_recovery_time(self):
        samples = [sample(0), sample(1, "ERROR"), sample(2, "STALE"), sample(3, "ERROR"), sample(4.5),
                   sample(5, "ERROR")]
        found = outages(samples)
        self.assertEqual(found[0], {"start_s": 1, "statuses": ["ERROR", "STALE", "ERROR"],
                                    "end_s": 4.5, "duration_s": 3.5})
        self.assertEqual(found[1]["duration_s"], None)  # Still down when the run ended.

    def test_summary_counts_distinct_frames_detections_ticks_and_reboots(self):
        samples = [
            sample(0.0, frame="f1", uptime=1000, detected="f1", people=1, fusion="a", radar_seq=10),
            sample(0.5, frame="f1", uptime=1000, detected="f1", people=1, fusion="b", radar_seq=15),
            sample(1.0, frame="f2", uptime=1800, detected="f1", fusion="b", radar_seq=20,
                   decision="POSSIBLE_PERSON"),
            sample(1.5, "ERROR", fusion="c", radar_seq=25),
            sample(2.0, frame="f3", uptime=300, detected="f3", people=0, fusion="d", radar_seq=30),
        ]
        summary = summarise(samples, 2.0)
        self.assertEqual(summary["camera"]["frames"], 3)
        self.assertEqual(summary["camera"]["fps"], 1.5)
        self.assertEqual(summary["camera"]["node_reboots_seen"], 1)
        self.assertEqual(summary["camera"]["available_fraction"], 0.8)
        self.assertEqual(summary["detection"]["frames_detected"], 2)
        self.assertAlmostEqual(summary["detection"]["coverage_of_frames"], 0.667)
        self.assertEqual(summary["detection"]["frames_with_person"], 1)
        self.assertEqual(summary["fusion"]["updates"], 4)
        self.assertEqual(summary["fusion"]["decision_changes"], 2)  # NO -> POSSIBLE -> NO.
        self.assertEqual(summary["radar"]["reports"], 20)
        self.assertEqual(summary["radar"]["rate_hz"], 10.0)
        self.assertEqual(summary["camera"]["outages"][0]["duration_s"], 0.5)
