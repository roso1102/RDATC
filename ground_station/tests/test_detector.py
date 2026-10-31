from io import BytesIO
import math
import unittest

import numpy as np
from PIL import Image

from ares.backend import DEFAULT_DETECTOR_MODEL
from ares.detector import COCO_PERSON, PAD_VALUE, decode, letterbox, nms, select_people


def jpeg(size, colour):
    output = BytesIO()
    Image.new("RGB", size, colour).save(output, format="JPEG")
    return output.getvalue()


class DecodeTests(unittest.TestCase):
    def test_grid_offsets_and_strides_follow_yolox_layout(self):
        raw = np.zeros((3549, 85), dtype=np.float32)
        # Stride-8 grid is 52 x 52; cell (x=3, y=2) is row 2 * 52 + 3.
        raw[2 * 52 + 3, :4] = [0.5, 0.5, 0.0, math.log(2)]
        # First stride-16 cell follows all 2704 stride-8 cells.
        raw[2704, :4] = [0.0, 0.0, 0.0, 0.0]
        decoded = decode(raw, 416)
        np.testing.assert_allclose(decoded[107, :4], [28, 20, 8, 16], rtol=1e-6)
        np.testing.assert_allclose(decoded[2704, :4], [0, 0, 16, 16], rtol=1e-6)

    def test_unexpected_output_size_is_rejected(self):
        with self.assertRaises(ValueError):
            decode(np.zeros((100, 85), dtype=np.float32), 416)


class SelectionTests(unittest.TestCase):
    def test_nms_keeps_best_of_overlapping_boxes_only(self):
        boxes = np.array([[0, 0, 10, 10], [1, 1, 11, 11], [50, 50, 60, 60]], dtype=np.float32)
        self.assertEqual(nms(boxes, np.array([0.6, 0.9, 0.5]), 0.45), [1, 2])

    def test_people_are_mapped_to_source_pixels_and_other_classes_ignored(self):
        decoded = np.zeros((3, 85), dtype=np.float32)
        decoded[0, :5] = [130, 130, 52, 104, 0.9]
        decoded[0, 5 + COCO_PERSON] = 0.9
        decoded[1, :5] = [300, 300, 40, 40, 0.95]
        decoded[1, 5 + 16] = 0.95  # COCO "dog": not a person.
        decoded[2, :5] = [10, 10, 60, 60, 0.9]
        decoded[2, 5 + COCO_PERSON] = 0.2  # Below threshold.
        people = select_people(decoded, 1.3, 320, 240, 0.35, 0.45)
        self.assertEqual(len(people), 1)
        self.assertEqual(people[0]["label"], "person")
        self.assertEqual(people[0]["box_basis"], "SOURCE_PIXELS")
        np.testing.assert_allclose(people[0]["box_xyxy"], [80, 60, 120, 140], atol=0.1)
        self.assertAlmostEqual(people[0]["score"], 0.81, places=3)

    def test_boxes_are_clipped_to_the_image(self):
        decoded = np.zeros((1, 85), dtype=np.float32)
        decoded[0, :6] = [5, 5, 40, 40, 1.0, 1.0]
        box = select_people(decoded, 1.0, 320, 240, 0.35, 0.45)[0]["box_xyxy"]
        self.assertEqual(box[:2], [0.0, 0.0])


class LetterboxTests(unittest.TestCase):
    def test_qvga_frame_is_scaled_padded_and_converted_to_bgr(self):
        tensor, ratio = letterbox(Image.new("RGB", (320, 240), (255, 0, 0)), 416)
        self.assertEqual(tensor.shape, (1, 3, 416, 416))
        self.assertEqual(tensor.dtype, np.float32)
        self.assertAlmostEqual(ratio, 1.3)
        self.assertEqual(tensor[0, 2, 100, 100], 255)  # Red lands in the last (R of BGR) channel.
        self.assertEqual(tensor[0, 0, 100, 100], 0)
        self.assertTrue((tensor[0, :, 312:, :] == PAD_VALUE).all())


@unittest.skipUnless(DEFAULT_DETECTOR_MODEL.is_file(), "YOLOX-Nano model file not downloaded")
class ModelTests(unittest.TestCase):
    def test_real_model_finds_nobody_in_a_blank_frame(self):
        from ares.detector import YoloxPersonDetector

        detector = YoloxPersonDetector(DEFAULT_DETECTOR_MODEL)
        result = detector.detect(jpeg((320, 240), (128, 128, 128)))
        self.assertEqual(result["person_count"], 0)
        self.assertEqual((result["input_width"], result["input_height"]), (320, 240))
        self.assertEqual(detector.info.licence, "Apache-2.0")
        self.assertEqual(len(detector.info.sha256), 64)
        self.assertEqual(detector.inference_location, "LAPTOP")

    def test_pi5_profile_is_labelled_as_a_laptop_approximation(self):
        from ares.detector import YoloxPersonDetector

        detector = YoloxPersonDetector(DEFAULT_DETECTOR_MODEL, profile="pi5_emulated")
        self.assertEqual(detector.inference_location, "LAPTOP_PI5_CONSTRAINED")
        self.assertIn("not a Raspberry Pi 5 measurement", detector.profile_note)
        self.assertEqual(detector.detect(jpeg((320, 240), (0, 0, 0)))["person_count"], 0)
        with self.assertRaises(ValueError):
            YoloxPersonDetector(DEFAULT_DETECTOR_MODEL, profile="esp32")
