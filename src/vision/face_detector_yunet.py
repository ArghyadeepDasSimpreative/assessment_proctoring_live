import cv2
import math
import time
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
        strong_confidence_threshold=0.86,
        medium_confidence_threshold=0.72,
        minimum_face_dimension=16,
        minimum_face_area_ratio=0.0008,
        minimum_aspect_ratio=0.35,
        maximum_aspect_ratio=2.20,
        landmark_box_margin=0.30,
        temporal_confirmation_frames=3,
        temporal_track_timeout=0.80,
        enable_candidate_validation=True,
        debug_rejections=False,
    ):
        self.input_size = (
            int(input_size[0]),
            int(input_size[1]),
        )

        self.confidence_threshold = float(confidence_threshold)

        self.nms_threshold = float(nms_threshold)

        self.top_k = int(top_k)

        self.rotation_angles = tuple(rotation_angles)

        self.strong_confidence_threshold = float(strong_confidence_threshold)

        self.medium_confidence_threshold = float(medium_confidence_threshold)

        self.minimum_face_dimension = int(minimum_face_dimension)

        self.minimum_face_area_ratio = float(minimum_face_area_ratio)

        self.minimum_aspect_ratio = float(minimum_aspect_ratio)

        self.maximum_aspect_ratio = float(maximum_aspect_ratio)

        self.landmark_box_margin = float(landmark_box_margin)

        self.temporal_confirmation_frames = max(
            1,
            int(temporal_confirmation_frames),
        )

        self.temporal_track_timeout = max(
            0.1,
            float(temporal_track_timeout),
        )

        self.enable_candidate_validation = bool(enable_candidate_validation)

        self.debug_rejections = bool(debug_rejections)

        self.detector = None

        self.model_path = self._resolve_model_path(model_path)

        self._secondary_tracks = []

        self._load_model()

    def _resolve_model_path(
        self,
        model_path,
    ):
        if model_path:

            path = Path(str(model_path))

            if path.is_absolute():

                return path

            project_root = Path(__file__).resolve().parents[2]

            return project_root / path

        project_root = Path(__file__).resolve().parents[2]

        return project_root / "src" / "models" / "face_detection_yunet_2023mar.onnx"

    def _load_model(
        self,
    ):
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
                "This OpenCV installation does not provide FaceDetectorYN. "
                "Please install or upgrade opencv-python."
            )

        except Exception as error:

            raise RuntimeError("Unable to initialize YuNet face detector: " f"{error}")

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

    def _center_distance(
        self,
        first,
        second,
    ):
        first_center_x = (first["x"] + first["x2"]) / 2.0

        first_center_y = (first["y"] + first["y2"]) / 2.0

        second_center_x = (second["x"] + second["x2"]) / 2.0

        second_center_y = (second["y"] + second["y2"]) / 2.0

        return math.sqrt(
            (first_center_x - second_center_x) ** 2
            + (first_center_y - second_center_y) ** 2
        )

    def _average_size(
        self,
        face,
    ):
        width = face["x2"] - face["x"]

        height = face["y2"] - face["y"]

        return (width + height) / 2.0

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

        average_size = (self._average_size(first) + self._average_size(second)) / 2.0

        if average_size <= 0:

            return False

        normalized_distance = distance / average_size

        return normalized_distance <= 0.35

    def _merge_faces(
        self,
        first,
        second,
    ):
        first_confidence = float(
            first.get(
                "confidence",
                0.0,
            )
        )

        second_confidence = float(
            second.get(
                "confidence",
                0.0,
            )
        )

        if first_confidence >= second_confidence:

            preferred = first

        else:

            preferred = second

        x = min(
            first["x"],
            second["x"],
        )

        y = min(
            first["y"],
            second["y"],
        )

        x2 = max(
            first["x2"],
            second["x2"],
        )

        y2 = max(
            first["y2"],
            second["y2"],
        )

        if first.get("orientation") == second.get("orientation"):

            orientation = first.get("orientation")

        else:

            orientation = "MIXED"

        return {
            "x": x,
            "y": y,
            "x2": x2,
            "y2": y2,
            "width": x2 - x,
            "height": y2 - y,
            "confidence": max(
                first_confidence,
                second_confidence,
            ),
            "orientation": orientation,
            "landmarks": preferred.get("landmarks"),
            "detection_source": preferred.get(
                "detection_source",
                "NORMAL",
            ),
            "rotation_angle": preferred.get(
                "rotation_angle",
                0.0,
            ),
        }

    def _remove_duplicates(
        self,
        faces,
    ):
        if not faces:

            return []

        sorted_faces = sorted(
            faces,
            key=lambda face: float(
                face.get(
                    "confidence",
                    0.0,
                )
            ),
            reverse=True,
        )

        merged_faces = []

        for face in sorted_faces:

            matched_index = None

            for (
                index,
                existing,
            ) in enumerate(merged_faces):

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

    def _get_face_area_ratio(
        self,
        face,
        frame_width,
        frame_height,
    ):
        width = max(
            0,
            face["x2"] - face["x"],
        )

        height = max(
            0,
            face["y2"] - face["y"],
        )

        frame_area = frame_width * frame_height

        if frame_area <= 0:

            return 0.0

        return (width * height) / float(frame_area)

    def _is_box_plausible(
        self,
        face,
        frame_width,
        frame_height,
    ):
        width = face["x2"] - face["x"]

        height = face["y2"] - face["y"]

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

    def _point_inside_expanded_box(
        self,
        point,
        face,
    ):
        if not isinstance(
            point,
            dict,
        ):

            return False

        try:

            px = float(point["x"])

            py = float(point["y"])

        except (
            KeyError,
            TypeError,
            ValueError,
        ):

            return False

        width = face["x2"] - face["x"]

        height = face["y2"] - face["y"]

        margin_x = width * self.landmark_box_margin

        margin_y = height * self.landmark_box_margin

        return (face["x"] - margin_x) <= px <= (face["x2"] + margin_x) and (
            face["y"] - margin_y
        ) <= py <= (face["y2"] + margin_y)

    def _get_landmark_plausibility_score(
        self,
        face,
    ):
        landmarks = face.get("landmarks")

        if not isinstance(
            landmarks,
            dict,
        ):

            return 0

        right_eye = landmarks.get("right_eye")

        left_eye = landmarks.get("left_eye")

        nose = landmarks.get("nose")

        right_mouth = landmarks.get("right_mouth")

        left_mouth = landmarks.get("left_mouth")

        points = [
            right_eye,
            left_eye,
            nose,
            right_mouth,
            left_mouth,
        ]

        score = 0

        inside_count = sum(
            1
            for point in points
            if self._point_inside_expanded_box(
                point,
                face,
            )
        )

        if inside_count >= 4:

            score += 1

        width = max(
            1.0,
            float(face["x2"] - face["x"]),
        )

        height = max(
            1.0,
            float(face["y2"] - face["y"]),
        )

        average_eye_y = None
        average_mouth_y = None

        try:

            eye_dx = abs(float(left_eye["x"]) - float(right_eye["x"]))

            eye_dy = abs(float(left_eye["y"]) - float(right_eye["y"]))

            eye_distance = math.sqrt(eye_dx**2 + eye_dy**2)

            normalized_eye_distance = eye_distance / width

            if 0.08 <= normalized_eye_distance <= 0.90:

                score += 1

        except (
            KeyError,
            TypeError,
            ValueError,
        ):

            pass

        try:

            average_eye_y = (float(right_eye["y"]) + float(left_eye["y"])) / 2.0

            average_mouth_y = (float(right_mouth["y"]) + float(left_mouth["y"])) / 2.0

            if average_mouth_y > (average_eye_y - (height * 0.12)):

                score += 1

        except (
            KeyError,
            TypeError,
            ValueError,
        ):

            pass

        try:

            nose_y = float(nose["y"])

            if average_eye_y is not None and average_mouth_y is not None:

                if (
                    (average_eye_y - height * 0.20)
                    <= nose_y
                    <= (average_mouth_y + height * 0.20)
                ):

                    score += 1

        except (
            KeyError,
            TypeError,
            ValueError,
        ):

            pass

        try:

            mouth_distance = abs(float(left_mouth["x"]) - float(right_mouth["x"]))

            normalized_mouth_distance = mouth_distance / width

            if 0.05 <= normalized_mouth_distance <= 0.90:

                score += 1

        except (
            KeyError,
            TypeError,
            ValueError,
        ):

            pass

        return score

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

    def _detect_raw(
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

        _,
        detections = self.detector.detect(frame)

        faces = []

        if detections is None:

            return faces

        for detection in detections:

            if len(detection) < 15:

                continue

            raw_x = int(detection[0])

            raw_y = int(detection[1])

            raw_width = int(detection[2])

            raw_height = int(detection[3])

            confidence = float(detection[-1])

            x = max(
                0,
                raw_x,
            )

            y = max(
                0,
                raw_y,
            )

            x2 = min(
                width,
                raw_x
                + max(
                    0,
                    raw_width,
                ),
            )

            y2 = min(
                height,
                raw_y
                + max(
                    0,
                    raw_height,
                ),
            )

            if x2 <= x or y2 <= y:

                continue

            faces.append(
                {
                    "x": x,
                    "y": y,
                    "x2": x2,
                    "y2": y2,
                    "width": x2 - x,
                    "height": y2 - y,
                    "confidence": confidence,
                    "orientation": "YUNET_FACE",
                    "landmarks": self._extract_landmarks(detection),
                    "detection_source": "NORMAL",
                    "rotation_angle": 0.0,
                }
            )

        return faces

    def _rotate_image(
        self,
        frame,
        angle,
    ):
        height, width = frame.shape[:2]

        center = (
            width / 2.0,
            height / 2.0,
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
                [
                    x,
                    y,
                ],
                [
                    x + w,
                    y,
                ],
                [
                    x,
                    y + h,
                ],
                [
                    x + w,
                    y + h,
                ],
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

    def _map_rotated_point(
        self,
        point,
        rotation_matrix,
        frame_width,
        frame_height,
    ):
        if not isinstance(
            point,
            dict,
        ):

            return None

        try:

            x = float(point["x"])

            y = float(point["y"])

        except (
            KeyError,
            TypeError,
            ValueError,
        ):

            return None

        inverse_matrix = cv2.invertAffineTransform(rotation_matrix)

        source = np.array(
            [
                [
                    [
                        x,
                        y,
                    ]
                ]
            ],
            dtype=np.float32,
        )

        mapped = cv2.transform(
            source,
            inverse_matrix,
        )[
            0
        ][0]

        mapped_x = max(
            0.0,
            min(
                float(frame_width),
                float(mapped[0]),
            ),
        )

        mapped_y = max(
            0.0,
            min(
                float(frame_height),
                float(mapped[1]),
            ),
        )

        return {
            "x": mapped_x,
            "y": mapped_y,
        }

    def _map_rotated_landmarks(
        self,
        landmarks,
        rotation_matrix,
        frame_width,
        frame_height,
    ):
        if not isinstance(
            landmarks,
            dict,
        ):

            return None

        mapped_landmarks = {}

        for (
            name,
            point,
        ) in landmarks.items():

            mapped_point = self._map_rotated_point(
                point,
                rotation_matrix,
                frame_width,
                frame_height,
            )

            if mapped_point is not None:

                mapped_landmarks[name] = mapped_point

        if not mapped_landmarks:

            return None

        return mapped_landmarks

    def _detect_rotated_faces(
        self,
        frame,
    ):
        frame_height, frame_width = frame.shape[:2]

        faces = []

        for angle in self.rotation_angles:

            (
                rotated_frame,
                rotation_matrix,
            ) = self._rotate_image(
                frame,
                angle,
            )

            rotated_faces = self._detect_raw(rotated_frame)

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

                mapped["landmarks"] = self._map_rotated_landmarks(
                    face.get("landmarks"),
                    rotation_matrix,
                    frame_width,
                    frame_height,
                )

                mapped["detection_source"] = "ROTATION_FALLBACK"

                mapped["rotation_angle"] = float(angle)

                faces.append(mapped)

        return self._remove_duplicates(faces)

    def _person_overlap_score(
        self,
        face,
        person,
    ):
        if not isinstance(
            person,
            dict,
        ):

            return 0.0

        try:

            person_x = float(person["x"])

            person_y = float(person["y"])

            person_x2 = float(person["x2"])

            person_y2 = float(person["y2"])

        except (
            KeyError,
            TypeError,
            ValueError,
        ):

            return 0.0

        face_center_x = (face["x"] + face["x2"]) / 2.0

        face_center_y = (face["y"] + face["y2"]) / 2.0

        if (
            person_x <= face_center_x <= person_x2
            and person_y <= face_center_y <= person_y2
        ):

            return 1.0

        return 0.0

    def _has_person_support(
        self,
        face,
        person_detections,
    ):
        if not person_detections:

            return False

        for detection in person_detections:

            if not isinstance(
                detection,
                dict,
            ):

                continue

            label = str(
                detection.get(
                    "label",
                    "",
                )
            ).upper()

            if label != "PERSON":

                continue

            if (
                self._person_overlap_score(
                    face,
                    detection,
                )
                > 0
            ):

                return True

        return False

    def _find_matching_track(
        self,
        face,
    ):
        best_track = None

        best_score = 0.0

        for track in self._secondary_tracks:

            tracked_face = track.get("face")

            if not tracked_face:

                continue

            overlap = self._iou(
                face,
                tracked_face,
            )

            distance = self._center_distance(
                face,
                tracked_face,
            )

            average_size = (
                self._average_size(face) + self._average_size(tracked_face)
            ) / 2.0

            if average_size <= 0:

                continue

            normalized_distance = distance / average_size

            score = max(
                overlap,
                max(
                    0.0,
                    1.0 - normalized_distance,
                ),
            )

            if (overlap >= 0.10 or normalized_distance <= 0.65) and score > best_score:

                best_score = score

                best_track = track

        return best_track

    def _update_secondary_tracks(
        self,
        candidates,
    ):
        current_time = time.monotonic()

        self._secondary_tracks = [
            track
            for track in self._secondary_tracks
            if (
                current_time
                - track.get(
                    "last_seen",
                    current_time,
                )
            )
            <= self.temporal_track_timeout
        ]

        matched_track_ids = set()

        for candidate in candidates:

            track = self._find_matching_track(candidate)

            landmark_score = self._get_landmark_plausibility_score(candidate)

            confidence = float(
                candidate.get(
                    "confidence",
                    0.0,
                )
            )

            if track is None:

                track = {
                    "face": candidate,
                    "hits": 1,
                    "last_seen": current_time,
                    "best_confidence": confidence,
                    "best_landmark_score": landmark_score,
                }

                self._secondary_tracks.append(track)

            else:

                track["face"] = candidate

                track["hits"] = (
                    int(
                        track.get(
                            "hits",
                            0,
                        )
                    )
                    + 1
                )

                track["last_seen"] = current_time

                track["best_confidence"] = max(
                    float(
                        track.get(
                            "best_confidence",
                            0.0,
                        )
                    ),
                    confidence,
                )

                track["best_landmark_score"] = max(
                    int(
                        track.get(
                            "best_landmark_score",
                            0,
                        )
                    ),
                    landmark_score,
                )

            matched_track_ids.add(id(track))

        return self._secondary_tracks

    def _secondary_candidate_accepted(
        self,
        candidate,
        frame_width,
        frame_height,
        person_detections=None,
    ):
        if not self._is_box_plausible(
            candidate,
            frame_width,
            frame_height,
        ):

            return False

        if not self.enable_candidate_validation:

            return True

        confidence = float(
            candidate.get(
                "confidence",
                0.0,
            )
        )

        landmark_score = self._get_landmark_plausibility_score(candidate)

        person_supported = self._has_person_support(
            candidate,
            person_detections,
        )

        if person_supported:

            if confidence >= self.confidence_threshold:

                return True

        if confidence >= 0.92:

            return True

        if confidence >= self.strong_confidence_threshold and landmark_score >= 1:

            return True

        if confidence >= self.medium_confidence_threshold and landmark_score >= 1:

            return True

        if confidence >= 0.64 and landmark_score >= 2:

            return True

        matching_track = self._find_matching_track(candidate)

        if matching_track is None:

            return False

        hits = int(
            matching_track.get(
                "hits",
                0,
            )
        )

        best_confidence = float(
            matching_track.get(
                "best_confidence",
                confidence,
            )
        )

        best_landmark_score = int(
            matching_track.get(
                "best_landmark_score",
                landmark_score,
            )
        )

        if hits >= self.temporal_confirmation_frames:

            if best_landmark_score >= 1 and best_confidence >= 0.63:

                return True

        return False

    def _primary_candidate_accepted(
        self,
        candidate,
        frame_width,
        frame_height,
    ):
        if not self._is_box_plausible(
            candidate,
            frame_width,
            frame_height,
        ):

            return False

        if not self.enable_candidate_validation:

            return True

        confidence = float(
            candidate.get(
                "confidence",
                0.0,
            )
        )

        landmark_score = self._get_landmark_plausibility_score(candidate)

        area_ratio = self._get_face_area_ratio(
            candidate,
            frame_width,
            frame_height,
        )

        if confidence >= self.medium_confidence_threshold:

            return True

        if landmark_score >= 1:

            return True

        if confidence >= 0.64 and area_ratio >= 0.004:

            return True

        return False

    def detect(
        self,
        frame,
        person_detections=None,
    ):
        if frame is None:

            return []

        if not isinstance(
            frame,
            np.ndarray,
        ):

            raise TypeError("Frame must be a numpy.ndarray.")

        if frame.size == 0:

            return []

        frame_height, frame_width = frame.shape[:2]

        faces = self._detect_raw(frame)

        faces = self._remove_duplicates(faces)

        faces = [
            face
            for face in faces
            if self._is_box_plausible(
                face,
                frame_width,
                frame_height,
            )
        ]

        if not faces:

            rotated_faces = self._detect_rotated_faces(frame)

            rotated_faces = [
                face
                for face in rotated_faces
                if self._is_box_plausible(
                    face,
                    frame_width,
                    frame_height,
                )
            ]

            rotated_faces = sorted(
                rotated_faces,
                key=lambda face: float(
                    face.get(
                        "confidence",
                        0.0,
                    )
                ),
                reverse=True,
            )

            if not rotated_faces:

                self._secondary_tracks = []

                return []

            primary = rotated_faces[0]

            accepted = []

            if self._primary_candidate_accepted(
                primary,
                frame_width,
                frame_height,
            ):

                accepted.append(primary)

            secondary_candidates = rotated_faces[1:]

            self._update_secondary_tracks(secondary_candidates)

            for candidate in secondary_candidates:

                if self._secondary_candidate_accepted(
                    candidate,
                    frame_width,
                    frame_height,
                    person_detections,
                ):

                    accepted.append(candidate)

            return accepted

        faces = sorted(
            faces,
            key=lambda face: float(
                face.get(
                    "confidence",
                    0.0,
                )
            ),
            reverse=True,
        )

        primary = faces[0]

        accepted_faces = []

        if self._primary_candidate_accepted(
            primary,
            frame_width,
            frame_height,
        ):

            accepted_faces.append(primary)

        secondary_candidates = faces[1:]

        self._update_secondary_tracks(secondary_candidates)

        for candidate in secondary_candidates:

            if self._secondary_candidate_accepted(
                candidate,
                frame_width,
                frame_height,
                person_detections,
            ):

                accepted_faces.append(candidate)

            elif self.debug_rejections:

                print(
                    "[YUNET][SECONDARY REJECTED]",
                    {
                        "confidence": float(
                            candidate.get(
                                "confidence",
                                0.0,
                            )
                        ),
                        "landmark_score": self._get_landmark_plausibility_score(
                            candidate
                        ),
                        "box": (
                            candidate.get("x"),
                            candidate.get("y"),
                            candidate.get("x2"),
                            candidate.get("y2"),
                        ),
                    },
                )

        return accepted_faces

    def get_face_count(
        self,
        frame,
        person_detections=None,
    ):
        return len(
            self.detect(
                frame,
                person_detections=person_detections,
            )
        )

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
            "strong_confidence_threshold": self.strong_confidence_threshold,
            "medium_confidence_threshold": self.medium_confidence_threshold,
            "minimum_face_dimension": self.minimum_face_dimension,
            "minimum_face_area_ratio": self.minimum_face_area_ratio,
            "minimum_aspect_ratio": self.minimum_aspect_ratio,
            "maximum_aspect_ratio": self.maximum_aspect_ratio,
            "temporal_confirmation_frames": self.temporal_confirmation_frames,
            "temporal_track_timeout": self.temporal_track_timeout,
            "enable_candidate_validation": self.enable_candidate_validation,
        }

    def close(
        self,
    ):
        self._secondary_tracks = []

        self.detector = None
