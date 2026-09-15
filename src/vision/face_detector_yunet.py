import cv2
import math
import numpy as np

from pathlib import Path


class YuNetFaceDetector:

    def __init__(
        self,
        model_path=None,
        input_size=(320, 320),
        confidence_threshold=0.60,
        nms_threshold=0.30,
        top_k=500,
        rotation_angles=(-15, 15),
    ):
        """
        YuNet face detector.

        Responsibilities:
        - Load YuNet
        - Detect faces
        - Return bounding boxes
        - Return confidence
        - Return facial landmarks
        - Remove duplicate detections
        - Optional rotation fallback

        This class does NOT:
        - Open the camera
        - Save evidence
        - Create JSON files
        - Send API requests
        - Send Socket.IO events
        - Control kiosk mode
        - Decide whether an anomaly should terminate an exam
        """

        self.input_size = (
            int(input_size[0]),
            int(input_size[1]),
        )

        self.confidence_threshold = float(confidence_threshold)

        self.nms_threshold = float(nms_threshold)

        self.top_k = int(top_k)

        self.rotation_angles = tuple(rotation_angles)

        self.detector = None

        self.model_path = self._resolve_model_path(model_path)

        self._load_model()

    # =========================================================
    # MODEL PATH
    # =========================================================

    def _resolve_model_path(
        self,
        model_path,
    ):
        """
        Default model:

        src/
            models/
                face_detection_yunet_2023mar.onnx

        Since this file is:

        src/vision/face_detector_yunet.py

        project root is parents[2].
        """

        if model_path:

            path = Path(str(model_path))

            if path.is_absolute():

                return path

            project_root = Path(__file__).resolve().parents[2]

            return project_root / path

        project_root = Path(__file__).resolve().parents[2]

        return project_root / "src" / "models" / "face_detection_yunet_2023mar.onnx"

    # =========================================================
    # LOAD MODEL
    # =========================================================

    def _load_model(self):

        if not self.model_path.exists():

            raise FileNotFoundError(
                "YuNet model file was not found: " f"{self.model_path}"
            )

        try:

            self.detector = cv2.FaceDetectorYN.create(
                str(self.model_path),
                "",
                self.input_size,
                self.confidence_threshold,
                self.nms_threshold,
                self.top_k,
            )

        except AttributeError:

            raise RuntimeError(
                "This OpenCV installation does not "
                "provide FaceDetectorYN. "
                "Please install or upgrade opencv-python."
            )

        except Exception as error:

            raise RuntimeError("Unable to initialize YuNet face detector: " f"{error}")

    # =========================================================
    # IOU
    # =========================================================

    def _iou(
        self,
        first,
        second,
    ):
        x1 = max(
            first["x"],
            second["x"],
        )

        y1 = max(
            first["y"],
            second["y"],
        )

        x2 = min(
            first["x2"],
            second["x2"],
        )

        y2 = min(
            first["y2"],
            second["y2"],
        )

        intersection_width = max(
            0,
            x2 - x1,
        )

        intersection_height = max(
            0,
            y2 - y1,
        )

        intersection = intersection_width * intersection_height

        first_area = (first["x2"] - first["x"]) * (first["y2"] - first["y"])

        second_area = (second["x2"] - second["x"]) * (second["y2"] - second["y"])

        union = first_area + second_area - intersection

        if union <= 0:

            return 0.0

        return intersection / union

    # =========================================================
    # CENTER DISTANCE
    # =========================================================

    def _center_distance(
        self,
        first,
        second,
    ):
        first_center_x = (first["x"] + first["x2"]) / 2

        first_center_y = (first["y"] + first["y2"]) / 2

        second_center_x = (second["x"] + second["x2"]) / 2

        second_center_y = (second["y"] + second["y2"]) / 2

        return math.sqrt(
            (first_center_x - second_center_x) ** 2
            + (first_center_y - second_center_y) ** 2
        )

    # =========================================================
    # AVERAGE FACE SIZE
    # =========================================================

    def _average_size(
        self,
        face,
    ):
        width = face["x2"] - face["x"]

        height = face["y2"] - face["y"]

        return (width + height) / 2

    # =========================================================
    # SAME PERSON
    # =========================================================

    def _same_person(
        self,
        first,
        second,
    ):
        overlap = self._iou(
            first,
            second,
        )

        if overlap >= 0.15:

            return True

        distance = self._center_distance(
            first,
            second,
        )

        average_size = (self._average_size(first) + self._average_size(second)) / 2

        if average_size <= 0:

            return False

        normalized_distance = distance / average_size

        return normalized_distance <= 0.35

    # =========================================================
    # MERGE DUPLICATES
    # =========================================================

    def _merge_faces(
        self,
        first,
        second,
    ):
        confidence = max(
            float(
                first.get(
                    "confidence",
                    0.0,
                )
            ),
            float(
                second.get(
                    "confidence",
                    0.0,
                )
            ),
        )

        if first.get("orientation") == second.get("orientation"):

            orientation = first.get("orientation")

        else:

            orientation = "MIXED"

        return {
            "x": min(
                first["x"],
                second["x"],
            ),
            "y": min(
                first["y"],
                second["y"],
            ),
            "x2": max(
                first["x2"],
                second["x2"],
            ),
            "y2": max(
                first["y2"],
                second["y2"],
            ),
            "width": (
                max(
                    first["x2"],
                    second["x2"],
                )
                - min(
                    first["x"],
                    second["x"],
                )
            ),
            "height": (
                max(
                    first["y2"],
                    second["y2"],
                )
                - min(
                    first["y"],
                    second["y"],
                )
            ),
            "confidence": confidence,
            "orientation": orientation,
            "landmarks": (first.get("landmarks") or second.get("landmarks")),
            "detection_source": (
                first.get(
                    "detection_source",
                    "NORMAL",
                )
            ),
            "rotation_angle": (
                first.get(
                    "rotation_angle",
                    0.0,
                )
            ),
        }

    # =========================================================
    # REMOVE DUPLICATES
    # =========================================================

    def _remove_duplicates(
        self,
        faces,
    ):
        merged_faces = []

        for face in faces:

            matched_index = None

            for index, existing in enumerate(merged_faces):

                if self._same_person(
                    face,
                    existing,
                ):

                    matched_index = index

                    break

            if matched_index is None:

                merged_faces.append(face)

            else:

                merged_faces[matched_index] = self._merge_faces(
                    merged_faces[matched_index],
                    face,
                )

        return merged_faces

    # =========================================================
    # ROTATE IMAGE
    # =========================================================

    def _rotate_image(
        self,
        frame,
        angle,
    ):
        height, width = frame.shape[:2]

        center = (
            width / 2,
            height / 2,
        )

        matrix = cv2.getRotationMatrix2D(
            center,
            angle,
            1.0,
        )

        rotated = cv2.warpAffine(
            frame,
            matrix,
            (
                width,
                height,
            ),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REPLICATE,
        )

        return (
            rotated,
            matrix,
        )

    # =========================================================
    # MAP ROTATED FACE
    # =========================================================

    def _map_rotated_face(
        self,
        x,
        y,
        w,
        h,
        rotation_matrix,
        frame_width,
        frame_height,
    ):
        inverse_matrix = cv2.invertAffineTransform(rotation_matrix)

        points = np.array(
            [
                [x, y],
                [x + w, y],
                [x, y + h],
                [x + w, y + h],
            ],
            dtype=np.float32,
        )

        points = points.reshape(
            -1,
            1,
            2,
        )

        mapped_points = cv2.transform(
            points,
            inverse_matrix,
        ).reshape(
            -1,
            2,
        )

        minimum_x = max(
            0,
            int(np.min(mapped_points[:, 0])),
        )

        minimum_y = max(
            0,
            int(np.min(mapped_points[:, 1])),
        )

        maximum_x = min(
            frame_width,
            int(np.max(mapped_points[:, 0])),
        )

        maximum_y = min(
            frame_height,
            int(np.max(mapped_points[:, 1])),
        )

        if maximum_x <= minimum_x or maximum_y <= minimum_y:

            return None

        return {
            "x": minimum_x,
            "y": minimum_y,
            "x2": maximum_x,
            "y2": maximum_y,
        }

    # =========================================================
    # LANDMARK EXTRACTION
    # =========================================================

    def _extract_landmarks(
        self,
        detection,
    ):
        if detection is None:

            return None

        if len(detection) < 14:

            return None

        return {
            "right_eye": {
                "x": float(detection[4]),
                "y": float(detection[5]),
            },
            "left_eye": {
                "x": float(detection[6]),
                "y": float(detection[7]),
            },
            "nose": {
                "x": float(detection[8]),
                "y": float(detection[9]),
            },
            "right_mouth": {
                "x": float(detection[10]),
                "y": float(detection[11]),
            },
            "left_mouth": {
                "x": float(detection[12]),
                "y": float(detection[13]),
            },
        }

    # =========================================================
    # NORMAL YUNET DETECTION
    # =========================================================

    def _detect_normal(
        self,
        frame,
    ):
        height, width = frame.shape[:2]

        self.detector.setInputSize(
            (
                width,
                height,
            )
        )

        _, detections = self.detector.detect(frame)

        faces = []

        if detections is None:

            return faces

        for detection in detections:

            if len(detection) < 15:

                continue

            x = int(detection[0])

            y = int(detection[1])

            w = int(detection[2])

            h = int(detection[3])

            confidence = float(detection[-1])

            x = max(0, x)

            y = max(0, y)

            x2 = min(width, x + max(0, w))

            y2 = min(height, y + max(0, h))

            if x2 <= x or y2 <= y:

                continue

            faces.append(
                {
                    "x": x,
                    "y": y,
                    "x2": x2,
                    "y2": y2,
                    "width": (x2 - x),
                    "height": (y2 - y),
                    "confidence": confidence,
                    "orientation": "YUNET_FACE",
                    "landmarks": self._extract_landmarks(detection),
                    "detection_source": "NORMAL",
                    "rotation_angle": 0.0,
                }
            )

        return faces

    # =========================================================
    # ROTATION FALLBACK
    # =========================================================

    def _detect_rotated_faces(
        self,
        frame,
    ):
        frame_height, frame_width = frame.shape[:2]

        faces = []

        for angle in self.rotation_angles:

            rotated_frame, rotation_matrix = self._rotate_image(
                frame,
                angle,
            )

            rotated_faces = self._detect_normal(rotated_frame)

            for face in rotated_faces:

                mapped = self._map_rotated_face(
                    face["x"],
                    face["y"],
                    face["width"],
                    face["height"],
                    rotation_matrix,
                    frame_width,
                    frame_height,
                )

                if mapped is None:

                    continue

                mapped["width"] = mapped["x2"] - mapped["x"]

                mapped["height"] = mapped["y2"] - mapped["y"]

                mapped["confidence"] = face.get(
                    "confidence",
                    0.0,
                )

                mapped["orientation"] = "TILT_LEFT" if angle < 0 else "TILT_RIGHT"

                mapped["landmarks"] = face.get("landmarks")

                mapped["detection_source"] = "ROTATION_FALLBACK"

                mapped["rotation_angle"] = float(angle)

                faces.append(mapped)

        return self._remove_duplicates(faces)

    # =========================================================
    # PUBLIC DETECT
    # =========================================================

    def detect(
        self,
        frame,
    ):
        """
        Detect faces.

        Returns:

            []       -> no face

            [face]   -> one face

            [face1,
             face2]  -> multiple faces
        """

        if frame is None:

            return []

        if not isinstance(
            frame,
            np.ndarray,
        ):

            raise TypeError("Frame must be a numpy.ndarray.")

        if frame.size == 0:

            return []

        faces = self._detect_normal(frame)

        faces = self._remove_duplicates(faces)

        # Only use the more expensive
        # rotation fallback when normal
        # detection finds nothing.

        if not faces:

            faces = self._detect_rotated_faces(frame)

        return faces

    # =========================================================
    # FACE COUNT
    # =========================================================

    def get_face_count(
        self,
        frame,
    ):
        return len(self.detect(frame))

    # =========================================================
    # MODEL INFORMATION
    # =========================================================

    def get_model_info(
        self,
    ):
        return {
            "model": "YuNet",
            "model_path": str(self.model_path),
            "input_size": self.input_size,
            "confidence_threshold": self.confidence_threshold,
            "nms_threshold": self.nms_threshold,
            "top_k": self.top_k,
            "rotation_angles": self.rotation_angles,
        }

    # =========================================================
    # CLOSE
    # =========================================================

    def close(
        self,
    ):
        self.detector = None
