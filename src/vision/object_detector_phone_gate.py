from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort


class YOLO26ObjectDetector:
    """
    Gate-1 phone/object detector.

    Backward-compatible public interface:
        detector = YOLO26ObjectDetector()
        detections = detector.detect(frame)
        detector.close()

    Strategy:
        1. Run normal YOLOv8n on the full camera frame.
        2. If a phone is already detected, return those results.
        3. If no phone is detected, run ONE zoomed overlapping tile.
        4. Rotate through four overlapping tiles across successive detect() calls.

    This improves:
        - partial phone detection
        - edge-of-frame phones
        - small phones
        - angled phones

    without running 4 extra YOLO passes every time.

    IMPORTANT:
        This detector never mirrors/flips the frame.
    """

    MONITORED_CLASSES = {
        0: "PERSON",
        67: "CELL_PHONE",
        73: "BOOK",
    }

    CLASS_THRESHOLDS = {
        0: 0.45,
        67: 0.25,
        73: 0.35,
    }

    DEFAULT_THRESHOLD = 0.45

    DEFAULT_INPUT_WIDTH = 640
    DEFAULT_INPUT_HEIGHT = 640

    DEFAULT_NMS_THRESHOLD = 0.45

    PERSON_CLASS_ID = 0
    PHONE_CLASS_ID = 67
    BOOK_CLASS_ID = 73

    TILE_PHONE_THRESHOLD = 0.20

    TILE_SCALE = 0.68

    MAX_TILE_PHONE_CANDIDATES = 4

    def __init__(
        self,
        model_path=None,
        nms_threshold=DEFAULT_NMS_THRESHOLD,
        intra_op_num_threads=1,
        inter_op_num_threads=1,
    ):
        if model_path is None:
            project_root = Path(__file__).resolve().parents[2]

            model_path = project_root / "models" / "yolov8n.onnx"

        self.model_path = Path(model_path)

        if not self.model_path.exists():
            raise RuntimeError(f"YOLOv8n ONNX model not found: {self.model_path}")

        self.nms_threshold = float(nms_threshold)

        if not 0.0 <= self.nms_threshold <= 1.0:
            raise ValueError("nms_threshold must be between 0.0 and 1.0.")

        session_options = ort.SessionOptions()

        session_options.graph_optimization_level = (
            ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        )

        session_options.intra_op_num_threads = int(intra_op_num_threads)

        session_options.inter_op_num_threads = int(inter_op_num_threads)

        self.session = ort.InferenceSession(
            str(self.model_path),
            sess_options=session_options,
            providers=["CPUExecutionProvider"],
        )

        inputs = self.session.get_inputs()

        if not inputs:
            raise RuntimeError("YOLOv8n ONNX model has no inputs.")

        self.input = inputs[0]

        self.input_name = self.input.name

        input_shape = self.input.shape

        self.input_height = self.DEFAULT_INPUT_HEIGHT

        self.input_width = self.DEFAULT_INPUT_WIDTH

        if len(input_shape) >= 4:
            if isinstance(
                input_shape[2],
                int,
            ):
                self.input_height = int(input_shape[2])

            if isinstance(
                input_shape[3],
                int,
            ):
                self.input_width = int(input_shape[3])

        outputs = self.session.get_outputs()

        self.output_names = [output.name for output in outputs]

        if not self.output_names:
            raise RuntimeError("YOLOv8n ONNX model has no outputs.")

        self.closed = False

        self._next_tile_index = 0

        print("[PHONE GATE] " "YOLOv8n loaded successfully.")

        print("[PHONE GATE] " f"Model: {self.model_path}")

        print("[PHONE GATE] " f"Input: " f"{self.input_width}x" f"{self.input_height}")

        print(
            "[PHONE GATE] "
            "Full-frame phone threshold: "
            f"{self.CLASS_THRESHOLDS[self.PHONE_CLASS_ID]:.2f}"
        )

        print(
            "[PHONE GATE] " "Tile phone threshold: " f"{self.TILE_PHONE_THRESHOLD:.2f}"
        )

        print("[PHONE GATE] " "Rotating 2x2 overlapping " "tile fallback enabled.")

    def _letterbox(
        self,
        frame,
    ):
        (
            frame_height,
            frame_width,
        ) = frame.shape[:2]

        if frame_height <= 0 or frame_width <= 0:
            raise ValueError("Invalid frame dimensions.")

        scale = min(
            self.input_width / float(frame_width),
            self.input_height / float(frame_height),
        )

        resized_width = max(
            1,
            int(round(frame_width * scale)),
        )

        resized_height = max(
            1,
            int(round(frame_height * scale)),
        )

        resized = cv2.resize(
            frame,
            (
                resized_width,
                resized_height,
            ),
            interpolation=(cv2.INTER_LINEAR),
        )

        canvas = np.full(
            (
                self.input_height,
                self.input_width,
                3,
            ),
            114,
            dtype=np.uint8,
        )

        pad_x = (self.input_width - resized_width) // 2

        pad_y = (self.input_height - resized_height) // 2

        canvas[
            pad_y : pad_y + resized_height,
            pad_x : pad_x + resized_width,
        ] = resized

        rgb = cv2.cvtColor(
            canvas,
            cv2.COLOR_BGR2RGB,
        )

        blob = rgb.astype(np.float32) / 255.0

        blob = np.transpose(
            blob,
            (
                2,
                0,
                1,
            ),
        )

        blob = np.expand_dims(
            blob,
            axis=0,
        )

        blob = np.ascontiguousarray(
            blob,
            dtype=np.float32,
        )

        return (
            blob,
            scale,
            pad_x,
            pad_y,
        )

    def _prepare_output(
        self,
        output,
    ):
        if output is None:
            return np.empty(
                (
                    0,
                    84,
                ),
                dtype=np.float32,
            )

        predictions = np.asarray(output)

        predictions = np.squeeze(predictions)

        if predictions.ndim != 2:
            return np.empty(
                (
                    0,
                    84,
                ),
                dtype=np.float32,
            )

        if predictions.shape[0] < predictions.shape[1] and predictions.shape[0] <= 100:
            predictions = predictions.T

        return predictions.astype(
            np.float32,
            copy=False,
        )

    def _convert_box(
        self,
        center_x,
        center_y,
        width,
        height,
        scale,
        pad_x,
        pad_y,
        original_width,
        original_height,
    ):
        x1 = (center_x - width / 2.0 - pad_x) / scale

        y1 = (center_y - height / 2.0 - pad_y) / scale

        x2 = (center_x + width / 2.0 - pad_x) / scale

        y2 = (center_y + height / 2.0 - pad_y) / scale

        x1 = max(
            0.0,
            min(
                float(original_width - 1),
                x1,
            ),
        )

        y1 = max(
            0.0,
            min(
                float(original_height - 1),
                y1,
            ),
        )

        x2 = max(
            0.0,
            min(
                float(original_width - 1),
                x2,
            ),
        )

        y2 = max(
            0.0,
            min(
                float(original_height - 1),
                y2,
            ),
        )

        return (
            int(round(x1)),
            int(round(y1)),
            int(round(x2)),
            int(round(y2)),
        )

    def _class_aware_nms(
        self,
        detections,
    ):
        if not detections:
            return []

        kept = []

        class_ids = sorted({int(detection["class_id"]) for detection in detections})

        for class_id in class_ids:
            class_detections = [
                detection
                for detection in detections
                if int(detection["class_id"]) == class_id
            ]

            if not class_detections:
                continue

            boxes = []
            scores = []

            for detection in class_detections:
                x1 = int(detection["x"])

                y1 = int(detection["y"])

                x2 = int(detection["x2"])

                y2 = int(detection["y2"])

                boxes.append(
                    [
                        x1,
                        y1,
                        max(
                            1,
                            x2 - x1,
                        ),
                        max(
                            1,
                            y2 - y1,
                        ),
                    ]
                )

                scores.append(float(detection["confidence"]))

            indexes = cv2.dnn.NMSBoxes(
                boxes,
                scores,
                score_threshold=0.0,
                nms_threshold=(self.nms_threshold),
            )

            if indexes is None or len(indexes) == 0:
                continue

            indexes = np.asarray(indexes).reshape(-1)

            for index in indexes:
                index = int(index)

                if index < 0 or index >= len(class_detections):
                    continue

                kept.append(class_detections[index])

        kept.sort(
            key=lambda detection: (detection["confidence"]),
            reverse=True,
        )

        return kept

    def _detect_on_image(
        self,
        image,
        *,
        allowed_class_ids=None,
        threshold_overrides=None,
        offset_x=0,
        offset_y=0,
        detection_source=("full_frame"),
        tile_index=None,
        partial_candidate=False,
    ):
        if image is None:
            return []

        if not isinstance(
            image,
            np.ndarray,
        ):
            return []

        if image.ndim != 3:
            return []

        if image.shape[2] != 3:
            return []

        (
            original_height,
            original_width,
        ) = image.shape[:2]

        if original_width <= 0 or original_height <= 0:
            return []

        (
            blob,
            scale,
            pad_x,
            pad_y,
        ) = self._letterbox(image)

        outputs = self.session.run(
            None,
            {
                self.input_name: blob,
            },
        )

        if not outputs:
            return []

        predictions = self._prepare_output(outputs[0])

        if predictions.size == 0:
            return []

        raw_detections = []

        for prediction in predictions:
            if prediction.shape[0] < 5:
                continue

            center_x = float(prediction[0])

            center_y = float(prediction[1])

            width = float(prediction[2])

            height = float(prediction[3])

            if width <= 0.0 or height <= 0.0:
                continue

            class_scores = prediction[4:]

            if class_scores is None or len(class_scores) == 0:
                continue

            class_id = int(np.argmax(class_scores))

            if class_id not in self.MONITORED_CLASSES:
                continue

            if allowed_class_ids is not None and class_id not in allowed_class_ids:
                continue

            confidence = float(class_scores[class_id])

            if not np.isfinite(confidence):
                continue

            threshold = float(
                self.CLASS_THRESHOLDS.get(
                    class_id,
                    self.DEFAULT_THRESHOLD,
                )
            )

            if threshold_overrides is not None and class_id in threshold_overrides:
                threshold = float(threshold_overrides[class_id])

            if confidence < threshold:
                continue

            (
                x1,
                y1,
                x2,
                y2,
            ) = self._convert_box(
                center_x,
                center_y,
                width,
                height,
                scale,
                pad_x,
                pad_y,
                original_width,
                original_height,
            )

            if x2 <= x1 or y2 <= y1:
                continue

            raw_detections.append(
                {
                    "class_id": int(class_id),
                    "label": (self.MONITORED_CLASSES[class_id]),
                    "confidence": float(confidence),
                    "x": int(x1 + offset_x),
                    "y": int(y1 + offset_y),
                    "x2": int(x2 + offset_x),
                    "y2": int(y2 + offset_y),
                    "detection_source": (detection_source),
                    "candidate_type": (
                        "partial_or_zoomed" if partial_candidate else "full_or_regular"
                    ),
                    "is_partial_candidate": bool(partial_candidate),
                    "tile_index": (tile_index),
                    "gate1_passed": True,
                }
            )

        return self._class_aware_nms(raw_detections)

    def _build_tiles(
        self,
        frame,
    ):
        (
            frame_height,
            frame_width,
        ) = frame.shape[:2]

        tile_width = max(
            2,
            int(round(frame_width * self.TILE_SCALE)),
        )

        tile_height = max(
            2,
            int(round(frame_height * self.TILE_SCALE)),
        )

        tile_width = min(
            tile_width,
            frame_width,
        )

        tile_height = min(
            tile_height,
            frame_height,
        )

        right_x = max(
            0,
            frame_width - tile_width,
        )

        bottom_y = max(
            0,
            frame_height - tile_height,
        )

        tile_specs = [
            (
                0,
                0,
                tile_width,
                tile_height,
            ),
            (
                right_x,
                0,
                frame_width,
                tile_height,
            ),
            (
                0,
                bottom_y,
                tile_width,
                frame_height,
            ),
            (
                right_x,
                bottom_y,
                frame_width,
                frame_height,
            ),
        ]

        tiles = []

        for index, (
            x1,
            y1,
            x2,
            y2,
        ) in enumerate(tile_specs):
            crop = frame[
                y1:y2,
                x1:x2,
            ]

            if crop is None or crop.size == 0:
                continue

            tiles.append(
                {
                    "index": (index),
                    "x1": int(x1),
                    "y1": int(y1),
                    "x2": int(x2),
                    "y2": int(y2),
                    "image": (crop),
                }
            )

        return tiles

    def _detect_rotating_tile(
        self,
        frame,
    ):
        tiles = self._build_tiles(frame)

        if not tiles:
            return []

        tile_position = self._next_tile_index % len(tiles)

        tile = tiles[tile_position]

        self._next_tile_index = (tile_position + 1) % len(tiles)

        detections = self._detect_on_image(
            tile["image"],
            allowed_class_ids={self.PHONE_CLASS_ID},
            threshold_overrides={self.PHONE_CLASS_ID: self.TILE_PHONE_THRESHOLD},
            offset_x=tile["x1"],
            offset_y=tile["y1"],
            detection_source=("tile"),
            tile_index=tile["index"],
            partial_candidate=True,
        )

        phone_detections = [
            detection
            for detection in detections
            if int(
                detection.get(
                    "class_id",
                    -1,
                )
            )
            == self.PHONE_CLASS_ID
        ]

        phone_detections.sort(
            key=lambda detection: (detection["confidence"]),
            reverse=True,
        )

        return phone_detections[: self.MAX_TILE_PHONE_CANDIDATES]

    def detect(
        self,
        frame,
    ):
        if self.closed:
            return []

        if frame is None:
            return []

        if not isinstance(
            frame,
            np.ndarray,
        ):
            return []

        if frame.ndim != 3:
            return []

        if frame.shape[2] != 3:
            return []

        # IMPORTANT:
        # No cv2.flip(frame, 1) here.
        # Orientation stays exactly as supplied.

        full_frame_detections = self._detect_on_image(
            frame,
            detection_source=("full_frame"),
            partial_candidate=False,
        )

        full_frame_phone_detections = [
            detection
            for detection in full_frame_detections
            if int(
                detection.get(
                    "class_id",
                    -1,
                )
            )
            == self.PHONE_CLASS_ID
        ]

        # Normal full-frame YOLO already sees a phone.
        # No need to spend CPU on tile fallback.
        if full_frame_phone_detections:
            return full_frame_detections

        # Normal YOLO missed the phone.
        # Run one zoomed tile from the rotating 2x2 set.
        tile_phone_detections = self._detect_rotating_tile(frame)

        if not tile_phone_detections:
            return full_frame_detections

        combined = full_frame_detections + tile_phone_detections

        return self._class_aware_nms(combined)

    def close(
        self,
    ):
        if self.closed:
            return

        self.session = None
        self.closed = True

        print("[PHONE GATE] " "YOLOv8n closed.")


ObjectDetector = YOLO26ObjectDetector

PhoneGateObjectDetector = YOLO26ObjectDetector
