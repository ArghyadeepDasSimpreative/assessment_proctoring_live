import time
from pathlib import Path

import cv2
import numpy as np


class MediaPipeFaceDetector:
    """
    Lightweight MediaPipe/BlazeFace face-count detector.

    The public API intentionally mirrors the parts of YuNetFaceDetector used by
    the proctoring project:

        detector = MediaPipeFaceDetector()
        faces = detector.detect(frame)
        count = detector.get_face_count(frame)
        info = detector.get_model_info()
        detector.close()

    Returned faces use the same basic dictionary shape as YuNetFaceDetector:
        x, y, x2, y2, width, height, confidence, orientation,
        landmarks, detection_source, rotation_angle

    `person_detections` is accepted by detect()/get_face_count() for drop-in
    compatibility with YuNetFaceDetector. MediaPipe does not require it.
    """

    DEFAULT_MODEL_NAMES = (
        "blaze_face_short_range.tflite",
        "face_detection_short_range.tflite",
        "face_detector.tflite",
        "face_detector.task",
    )

    OFFICIAL_MODEL_URL = (
        "https://storage.googleapis.com/mediapipe-models/face_detector/"
        "blaze_face_short_range/float16/latest/blaze_face_short_range.tflite"
    )

    def __init__(
        self,
        model_path=None,
        min_detection_confidence=0.60,
        min_suppression_threshold=0.30,
        minimum_face_dimension=16,
        minimum_face_area_ratio=0.0008,
        maximum_aspect_ratio=2.20,
        minimum_aspect_ratio=0.35,
        max_faces=None,
        running_mode="VIDEO",
    ):
        self.min_detection_confidence = float(min_detection_confidence)
        self.min_suppression_threshold = float(min_suppression_threshold)
        self.minimum_face_dimension = max(1, int(minimum_face_dimension))
        self.minimum_face_area_ratio = max(0.0, float(minimum_face_area_ratio))
        self.minimum_aspect_ratio = max(0.01, float(minimum_aspect_ratio))
        self.maximum_aspect_ratio = max(
            self.minimum_aspect_ratio,
            float(maximum_aspect_ratio),
        )
        self.max_faces = None if max_faces is None else max(1, int(max_faces))
        self.running_mode_name = str(running_mode or "VIDEO").upper().strip()

        if self.running_mode_name not in {"IMAGE", "VIDEO"}:
            raise ValueError(
                "MediaPipeFaceDetector running_mode must be 'IMAGE' or 'VIDEO'."
            )

        self.model_path = self._resolve_model_path(model_path)
        self.detector = None
        self._mp = None
        self._vision = None
        self._last_timestamp_ms = -1
        self._closed = False

        self._load_model()

    def _resolve_model_path(self, model_path):
        if model_path:
            path = Path(str(model_path)).expanduser()
            if not path.is_absolute():
                project_root = Path(__file__).resolve().parents[2]
                path = project_root / path
            return path.resolve()

        project_root = Path(__file__).resolve().parents[2]
        models_dir = project_root / "src" / "models"

        for model_name in self.DEFAULT_MODEL_NAMES:
            candidate = models_dir / model_name
            if candidate.exists():
                return candidate.resolve()

        return (models_dir / self.DEFAULT_MODEL_NAMES[0]).resolve()

    def _load_model(self):
        if not self.model_path.exists():
            raise FileNotFoundError(
                "MediaPipe BlazeFace model file was not found: "
                f"{self.model_path}\n"
                "Place blaze_face_short_range.tflite inside src/models/.\n"
                "Official model URL:\n"
                f"{self.OFFICIAL_MODEL_URL}"
            )

        try:
            import mediapipe as mp
            from mediapipe.tasks.python import vision
        except ImportError as error:
            raise RuntimeError(
                "MediaPipe is not installed in the active Python environment. "
                "Install it with: python -m pip install mediapipe"
            ) from error

        self._mp = mp
        self._vision = vision

        try:
            if self.running_mode_name == "VIDEO":
                running_mode = vision.RunningMode.VIDEO
            else:
                running_mode = vision.RunningMode.IMAGE

            options = vision.FaceDetectorOptions(
                base_options=mp.tasks.BaseOptions(
                    model_asset_path=str(self.model_path),
                ),
                running_mode=running_mode,
                min_detection_confidence=self.min_detection_confidence,
                min_suppression_threshold=self.min_suppression_threshold,
            )

            self.detector = vision.FaceDetector.create_from_options(options)
        except Exception as error:
            raise RuntimeError(
                "Unable to initialize MediaPipe Face Detector with model: "
                f"{self.model_path}"
            ) from error

    def _next_timestamp_ms(self):
        timestamp_ms = int(time.monotonic() * 1000.0)

        if timestamp_ms <= self._last_timestamp_ms:
            timestamp_ms = self._last_timestamp_ms + 1

        self._last_timestamp_ms = timestamp_ms
        return timestamp_ms

    def _get_face_area_ratio(self, face, frame_width, frame_height):
        width = max(0, int(face["x2"]) - int(face["x"]))
        height = max(0, int(face["y2"]) - int(face["y"]))
        frame_area = int(frame_width) * int(frame_height)

        if frame_area <= 0:
            return 0.0

        return (width * height) / float(frame_area)

    def _is_box_plausible(self, face, frame_width, frame_height):
        width = int(face["x2"]) - int(face["x"])
        height = int(face["y2"]) - int(face["y"])

        if width <= 0 or height <= 0:
            return False

        if width < self.minimum_face_dimension or height < self.minimum_face_dimension:
            return False

        area_ratio = self._get_face_area_ratio(
            face,
            frame_width,
            frame_height,
        )

        if area_ratio < self.minimum_face_area_ratio:
            return False

        aspect_ratio = width / float(height)

        if (
            aspect_ratio < self.minimum_aspect_ratio
            or aspect_ratio > self.maximum_aspect_ratio
        ):
            return False

        return True

    def _get_confidence(self, detection):
        categories = getattr(detection, "categories", None) or []

        if not categories:
            return 0.0

        try:
            return float(categories[0].score)
        except (AttributeError, TypeError, ValueError):
            return 0.0

    def _extract_keypoints(self, detection, frame_width, frame_height):
        keypoints = getattr(detection, "keypoints", None) or []

        converted = []

        for keypoint in keypoints:
            try:
                normalized_x = float(keypoint.x)
                normalized_y = float(keypoint.y)
            except (AttributeError, TypeError, ValueError):
                continue

            converted.append(
                {
                    "x": normalized_x * frame_width,
                    "y": normalized_y * frame_height,
                    "normalized_x": normalized_x,
                    "normalized_y": normalized_y,
                }
            )

        # BlazeFace returns six approximate facial keypoints. Keep names close
        # to the YuNet structure where possible while retaining the complete
        # list under `keypoints`.
        conventional_names = (
            "right_eye",
            "left_eye",
            "nose",
            "mouth",
            "right_ear_tragion",
            "left_ear_tragion",
        )

        landmarks = {
            "keypoints": converted,
        }

        for index, name in enumerate(conventional_names):
            if index < len(converted):
                landmarks[name] = {
                    "x": converted[index]["x"],
                    "y": converted[index]["y"],
                }

        return landmarks

    def _convert_detection(self, detection, frame_width, frame_height):
        bounding_box = getattr(detection, "bounding_box", None)

        if bounding_box is None:
            return None

        try:
            raw_x = int(bounding_box.origin_x)
            raw_y = int(bounding_box.origin_y)
            raw_width = int(bounding_box.width)
            raw_height = int(bounding_box.height)
        except (AttributeError, TypeError, ValueError):
            return None

        x = max(0, raw_x)
        y = max(0, raw_y)
        x2 = min(frame_width, raw_x + max(0, raw_width))
        y2 = min(frame_height, raw_y + max(0, raw_height))

        if x2 <= x or y2 <= y:
            return None

        confidence = self._get_confidence(detection)

        face = {
            "x": x,
            "y": y,
            "x2": x2,
            "y2": y2,
            "width": x2 - x,
            "height": y2 - y,
            "confidence": confidence,
            "orientation": "MEDIAPIPE_FACE",
            "landmarks": self._extract_keypoints(
                detection,
                frame_width,
                frame_height,
            ),
            "detection_source": "MEDIAPIPE_BLAZEFACE",
            "rotation_angle": 0.0,
        }

        if not self._is_box_plausible(face, frame_width, frame_height):
            return None

        return face

    def detect(
        self,
        frame,
        person_detections=None,
        timestamp_ms=None,
    ):
        # `person_detections` is deliberately accepted for compatibility with
        # YuNetFaceDetector. BlazeFace does not need YOLO person support.
        _ = person_detections

        if self._closed or self.detector is None:
            return []

        if frame is None:
            return []

        if not isinstance(frame, np.ndarray):
            raise TypeError("Frame must be a numpy.ndarray.")

        if frame.size == 0:
            return []

        frame_height, frame_width = frame.shape[:2]

        if frame_height <= 0 or frame_width <= 0:
            return []

        if frame.ndim == 2:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
        elif frame.ndim == 3 and frame.shape[2] == 4:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGB)
        else:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        rgb_frame = np.ascontiguousarray(rgb_frame)

        mp_image = self._mp.Image(
            image_format=self._mp.ImageFormat.SRGB,
            data=rgb_frame,
        )

        if self.running_mode_name == "VIDEO":
            if timestamp_ms is None:
                timestamp_ms = self._next_timestamp_ms()
            else:
                timestamp_ms = int(timestamp_ms)
                if timestamp_ms <= self._last_timestamp_ms:
                    timestamp_ms = self._last_timestamp_ms + 1
                self._last_timestamp_ms = timestamp_ms

            result = self.detector.detect_for_video(
                mp_image,
                timestamp_ms,
            )
        else:
            result = self.detector.detect(mp_image)

        detections = getattr(result, "detections", None) or []
        faces = []

        for detection in detections:
            face = self._convert_detection(
                detection,
                frame_width,
                frame_height,
            )

            if face is not None:
                faces.append(face)

        faces.sort(
            key=lambda face: float(face.get("confidence", 0.0)),
            reverse=True,
        )

        if self.max_faces is not None:
            faces = faces[: self.max_faces]

        return faces

    def get_face_count(
        self,
        frame,
        person_detections=None,
        timestamp_ms=None,
    ):
        return len(
            self.detect(
                frame,
                person_detections=person_detections,
                timestamp_ms=timestamp_ms,
            )
        )

    def get_model_info(self):
        return {
            "model": "MediaPipe BlazeFace Short Range",
            "backend": "MediaPipe Tasks FaceDetector",
            "model_path": str(self.model_path),
            "running_mode": self.running_mode_name,
            "min_detection_confidence": self.min_detection_confidence,
            "min_suppression_threshold": self.min_suppression_threshold,
            "minimum_face_dimension": self.minimum_face_dimension,
            "minimum_face_area_ratio": self.minimum_face_area_ratio,
            "minimum_aspect_ratio": self.minimum_aspect_ratio,
            "maximum_aspect_ratio": self.maximum_aspect_ratio,
            "max_faces": self.max_faces,
        }

    def close(self):
        if self._closed:
            return

        self._closed = True

        if self.detector is not None:
            try:
                self.detector.close()
            finally:
                self.detector = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False
