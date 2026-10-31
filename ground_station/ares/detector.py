"""Laptop person detection on single camera frames (YOLOX-Nano, ONNX Runtime CPU).

Results are LAPTOP inference on one frame. A detection count is camera evidence only:
it is not a fused presence probability and its accuracy on OV7670 frames is unmeasured.
"""

from dataclasses import dataclass
import hashlib
from io import BytesIO
from pathlib import Path
import time

import numpy as np
from PIL import Image

COCO_PERSON = 0
PAD_VALUE = 114
STRIDES = (8, 16, 32)

# Thread caps approximate smaller hosts on this laptop; they are not measurements on that hardware.
PROFILES = {
    "laptop": {"threads": 0, "location": "LAPTOP", "note": "Full laptop CPU"},
    "pi5_emulated": {"threads": 4, "location": "LAPTOP_PI5_CONSTRAINED",
                     "note": "Laptop limited to 4 inference threads; approximation, not a Raspberry Pi 5 measurement"},
}


@dataclass(frozen=True)
class ModelInfo:
    name: str
    version: str
    licence: str
    source: str
    sha256: str
    input_size: int

    def to_record(self):
        return {"name": self.name, "version": self.version, "licence": self.licence,
                "source": self.source, "sha256": self.sha256, "input_size": self.input_size}


def letterbox(image: Image.Image, size: int):
    """Resize keeping aspect ratio and pad to size x size, as YOLOX preprocessing does.

    Returns a 1x3xSxS float32 BGR tensor (0-255, no normalisation) and the scale ratio.
    """
    ratio = min(size / image.width, size / image.height)
    resized = image.convert("RGB").resize(
        (max(1, round(image.width * ratio)), max(1, round(image.height * ratio))), Image.BILINEAR)
    canvas = np.full((size, size, 3), PAD_VALUE, dtype=np.float32)
    canvas[:resized.height, :resized.width] = np.asarray(resized, dtype=np.float32)[:, :, ::-1]
    return np.ascontiguousarray(canvas.transpose(2, 0, 1)[None]), ratio


def decode(raw: np.ndarray, size: int, strides=STRIDES) -> np.ndarray:
    """Convert raw YOLOX grid outputs (N x 85) to centre/size boxes in input pixels."""
    grids, scales = [], []
    for stride in strides:
        cells = size // stride
        ys, xs = np.meshgrid(np.arange(cells), np.arange(cells), indexing="ij")
        grids.append(np.stack((xs, ys), axis=-1).reshape(-1, 2))
        scales.append(np.full((cells * cells, 1), stride))
    grid = np.concatenate(grids).astype(np.float32)
    scale = np.concatenate(scales).astype(np.float32)
    if grid.shape[0] != raw.shape[0]:
        raise ValueError(f"Model output has {raw.shape[0]} rows; expected {grid.shape[0]} for {size}px input")
    decoded = raw.astype(np.float32).copy()
    decoded[:, :2] = (decoded[:, :2] + grid) * scale
    decoded[:, 2:4] = np.exp(decoded[:, 2:4]) * scale
    return decoded


def nms(boxes: np.ndarray, scores: np.ndarray, iou_threshold: float) -> list[int]:
    """Greedy non-maximum suppression over x1, y1, x2, y2 boxes; returns kept indices."""
    order = scores.argsort()[::-1]
    areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    keep = []
    while order.size:
        best, rest = order[0], order[1:]
        keep.append(int(best))
        x1 = np.maximum(boxes[best, 0], boxes[rest, 0])
        y1 = np.maximum(boxes[best, 1], boxes[rest, 1])
        x2 = np.minimum(boxes[best, 2], boxes[rest, 2])
        y2 = np.minimum(boxes[best, 3], boxes[rest, 3])
        overlap = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
        iou = overlap / np.maximum(areas[best] + areas[rest] - overlap, 1e-9)
        order = rest[iou <= iou_threshold]
    return keep


def select_people(decoded: np.ndarray, ratio: float, width: int, height: int,
                  score_threshold: float, nms_threshold: float) -> list[dict]:
    """Keep person-class boxes above threshold, mapped back to source-image pixels."""
    scores = decoded[:, 4] * decoded[:, 5 + COCO_PERSON]
    mask = scores >= score_threshold
    if not mask.any():
        return []
    centre, extent, scores = decoded[mask, :2], decoded[mask, 2:4], scores[mask]
    boxes = np.concatenate((centre - extent / 2, centre + extent / 2), axis=1) / ratio
    boxes[:, [0, 2]] = boxes[:, [0, 2]].clip(0, width)
    boxes[:, [1, 3]] = boxes[:, [1, 3]].clip(0, height)
    return [{"label": "person", "score": round(float(scores[i]), 3),
             "box_xyxy": [round(float(value), 1) for value in boxes[i]],
             "box_basis": "SOURCE_PIXELS"}
            for i in nms(boxes, scores, nms_threshold)]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


class YoloxPersonDetector:
    """YOLOX-Nano COCO detector restricted to the person class, run on the laptop CPU."""

    def __init__(self, model_path: Path, score_threshold: float = 0.35, nms_threshold: float = 0.45,
                 profile: str = "laptop"):
        import onnxruntime  # Imported lazily so the backend runs without the detector installed.

        if profile not in PROFILES:
            raise ValueError(f"Unknown detector profile {profile!r}; choose from {sorted(PROFILES)}")
        self.profile = profile
        self.inference_location = PROFILES[profile]["location"]
        self.profile_note = PROFILES[profile]["note"]
        self.score_threshold = score_threshold
        self.nms_threshold = nms_threshold
        options = onnxruntime.SessionOptions()
        options.intra_op_num_threads = PROFILES[profile]["threads"]  # 0 lets ONNX Runtime choose.
        self.session = onnxruntime.InferenceSession(
            str(model_path), options, providers=["CPUExecutionProvider"])
        model_input = self.session.get_inputs()[0]
        self.input_name = model_input.name
        size = model_input.shape[2]
        if not isinstance(size, int) or size != model_input.shape[3]:
            raise ValueError("Expected a fixed square YOLOX input")
        self.info = ModelInfo(
            name="YOLOX-Nano (COCO, person class only)", version="Megvii YOLOX release 0.1.1rc0",
            licence="Apache-2.0", source="github.com/Megvii-BaseDetection/YOLOX",
            sha256=file_sha256(model_path), input_size=size,
        )

    def detect(self, jpeg: bytes) -> dict:
        with Image.open(BytesIO(jpeg)) as image:
            width, height = image.size
            tensor, ratio = letterbox(image, self.info.input_size)
        started = time.perf_counter()
        raw = self.session.run(None, {self.input_name: tensor})[0][0]
        people = select_people(decode(raw, self.info.input_size), ratio, width, height,
                               self.score_threshold, self.nms_threshold)
        return {"detections": people, "person_count": len(people),
                "inference_ms": round((time.perf_counter() - started) * 1000, 1),
                "input_width": width, "input_height": height}
