import os
import time

import cv2

from src.vision.face_detector_yunet import YuNetFaceDetector
from src.vision.face_landmarker import FaceLandmarker
from src.vision.gaze_tracker import GazeTracker
from src.vision.head_tracker import HeadTracker
from src.vision.object_detector_yolo26 import YOLO26ObjectDetector
from src.vision.pose_landmarker import PoseLandmarker

from src.core.posture_monitor import PostureMonitor
from src.core.anomaly_manager import AnomalyManager

from src.evidence.evidence_store import EvidenceStore

CAMERA_INDEX = 0
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
POSE_INTERVAL = 0.4

WINDOW_NAME = "Skolariq Proctoring - Full Anomaly Test"


ANOMALY_ORDER = [
    "NO_FACE",
    "MULTIPLE_FACES",
    "GAZE_AWAY",
    "HEAD_AWAY",
    "PHONE_DETECTED",
    "BOOK_DETECTED",
    "EXTRA_PERSON",
    "BODY_LEAN_LEFT",
    "BODY_LEAN_RIGHT",
    "LEFT_ARM_RAISED",
    "RIGHT_ARM_RAISED",
    "UNUSUAL_ARM_MOVEMENT",
    "UPPER_BODY_NOT_VISIBLE",
]


def open_camera():

    if os.name == "nt":

        camera = cv2.VideoCapture(
            CAMERA_INDEX,
            cv2.CAP_DSHOW,
        )

    else:

        camera = cv2.VideoCapture(
            CAMERA_INDEX,
        )

    if not camera.isOpened():

        raise RuntimeError(f"Unable to open camera index {CAMERA_INDEX}.")

    camera.set(
        cv2.CAP_PROP_FRAME_WIDTH,
        CAMERA_WIDTH,
    )

    camera.set(
        cv2.CAP_PROP_FRAME_HEIGHT,
        CAMERA_HEIGHT,
    )

    return camera


def empty_pose_result():

    return {
        "valid": False,
        "pose_count": 0,
        "landmarks": None,
        "world_landmarks": None,
    }


def empty_posture_state():

    return {
        "valid": False,
        "upper_body_visible": False,
        "leaning_left": False,
        "leaning_right": False,
        "left_arm_raised": False,
        "right_arm_raised": False,
        "unusual_arm_movement": False,
        "left_arm_movement": 0.0,
        "right_arm_movement": 0.0,
        "shoulder_center_x": None,
        "shoulder_width": None,
        "left_shoulder_visibility": 0.0,
        "right_shoulder_visibility": 0.0,
        "left_elbow_visible": False,
        "right_elbow_visible": False,
        "left_wrist_visible": False,
        "right_wrist_visible": False,
    }


def get_face_coordinates(face):

    x = None
    y = None
    width = None
    height = None

    if isinstance(face, dict):

        if "x" in face and "y" in face and "x2" in face and "y2" in face:

            x = int(face["x"])
            y = int(face["y"])
            width = int(face["x2"] - face["x"])
            height = int(face["y2"] - face["y"])

        elif "x" in face and "y" in face and "w" in face and "h" in face:

            x = int(face["x"])
            y = int(face["y"])
            width = int(face["w"])
            height = int(face["h"])

        elif "x" in face and "y" in face and "width" in face and "height" in face:

            x = int(face["x"])
            y = int(face["y"])
            width = int(face["width"])
            height = int(face["height"])

        elif "bbox" in face and len(face["bbox"]) >= 4:

            x = int(face["bbox"][0])
            y = int(face["bbox"][1])
            width = int(face["bbox"][2])
            height = int(face["bbox"][3])

    elif isinstance(
        face,
        (
            list,
            tuple,
        ),
    ):

        if len(face) >= 4:

            x = int(face[0])
            y = int(face[1])
            width = int(face[2])
            height = int(face[3])

    if x is None or y is None or width is None or height is None:

        return None

    return {
        "x": x,
        "y": y,
        "width": width,
        "height": height,
    }


def draw_face_box(
    frame,
    face,
    mirrored=False,
):

    coordinates = get_face_coordinates(face)

    if coordinates is None:

        return None

    x = coordinates["x"]
    y = coordinates["y"]
    width = coordinates["width"]
    height = coordinates["height"]

    frame_width = frame.shape[1]
    frame_height = frame.shape[0]

    if mirrored:

        x = frame_width - (x + width)

    x1 = max(
        0,
        x,
    )

    y1 = max(
        0,
        y,
    )

    x2 = min(
        frame_width - 1,
        x + width,
    )

    y2 = min(
        frame_height - 1,
        y + height,
    )

    if x2 <= x1 or y2 <= y1:

        return None

    cv2.rectangle(
        frame,
        (
            x1,
            y1,
        ),
        (
            x2,
            y2,
        ),
        (
            0,
            255,
            0,
        ),
        2,
    )

    return {
        "x": x1,
        "y": y1,
        "x2": x2,
        "y2": y2,
    }


def draw_object_box(
    frame,
    detection,
    mirrored=False,
):

    if not isinstance(
        detection,
        dict,
    ):

        return

    try:

        x1 = int(detection["x"])
        y1 = int(detection["y"])
        x2 = int(detection["x2"])
        y2 = int(detection["y2"])

        label = str(
            detection.get(
                "label",
                "OBJECT",
            )
        )

        confidence = float(
            detection.get(
                "confidence",
                0.0,
            )
        )

    except (
        KeyError,
        TypeError,
        ValueError,
    ):

        return

    if mirrored:

        frame_width = frame.shape[1]

        old_x1 = x1
        old_x2 = x2

        x1 = frame_width - old_x2
        x2 = frame_width - old_x1

    x1 = max(
        0,
        min(
            frame.shape[1] - 1,
            x1,
        ),
    )

    x2 = max(
        0,
        min(
            frame.shape[1] - 1,
            x2,
        ),
    )

    y1 = max(
        0,
        min(
            frame.shape[0] - 1,
            y1,
        ),
    )

    y2 = max(
        0,
        min(
            frame.shape[0] - 1,
            y2,
        ),
    )

    if x2 <= x1 or y2 <= y1:

        return

    cv2.rectangle(
        frame,
        (
            x1,
            y1,
        ),
        (
            x2,
            y2,
        ),
        (
            0,
            165,
            255,
        ),
        2,
    )

    text = f"{label} {confidence:.2f}"

    cv2.putText(
        frame,
        text,
        (
            x1,
            max(
                18,
                y1 - 6,
            ),
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        (
            0,
            165,
            255,
        ),
        2,
        cv2.LINE_AA,
    )


def get_preview_point(
    landmark,
    width,
    height,
    minimum_visibility=0.50,
):

    if landmark is None:

        return None

    if (
        getattr(
            landmark,
            "visibility",
            0.0,
        )
        < minimum_visibility
    ):

        return None

    raw_x = int(landmark.x * width)

    raw_y = int(landmark.y * height)

    mirrored_x = width - 1 - raw_x

    return (
        mirrored_x,
        raw_y,
    )


def draw_pose(
    frame,
    pose_result,
):

    if not pose_result.get(
        "valid",
        False,
    ):

        return

    landmarks = pose_result.get("landmarks")

    if landmarks is None or len(landmarks) < 17:

        return

    height, width = frame.shape[:2]

    indexes = [
        11,
        12,
        13,
        14,
        15,
        16,
    ]

    points = {}

    for index in indexes:

        point = get_preview_point(
            landmarks[index],
            width,
            height,
        )

        points[index] = point

        if point is not None:

            cv2.circle(
                frame,
                point,
                5,
                (
                    255,
                    0,
                    255,
                ),
                -1,
            )

    connections = [
        (
            11,
            12,
        ),
        (
            11,
            13,
        ),
        (
            13,
            15,
        ),
        (
            12,
            14,
        ),
        (
            14,
            16,
        ),
    ]

    for (
        start,
        end,
    ) in connections:

        start_point = points.get(start)
        end_point = points.get(end)

        if start_point is not None and end_point is not None:

            cv2.line(
                frame,
                start_point,
                end_point,
                (
                    255,
                    0,
                    255,
                ),
                2,
            )


def object_anomalies(
    detections,
):

    phone_detected = False
    book_detected = False
    extra_person = False
    person_count = 0

    for detection in detections:

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

        if label == "CELL_PHONE":

            phone_detected = True

        elif label == "BOOK":

            book_detected = True

        elif label == "PERSON":

            person_count += 1

    if person_count > 1:

        extra_person = True

    return {
        "phone_detected": phone_detected,
        "book_detected": book_detected,
        "extra_person": extra_person,
        "person_count": person_count,
    }


def pose_metadata(
    pose_result,
    posture_state,
):

    return {
        "pose_valid": bool(
            pose_result.get(
                "valid",
                False,
            )
        ),
        "pose_count": int(
            pose_result.get(
                "pose_count",
                0,
            )
        ),
        "upper_body_visible": bool(
            posture_state.get(
                "upper_body_visible",
                False,
            )
        ),
        "shoulder_center_x": posture_state.get("shoulder_center_x"),
        "shoulder_width": posture_state.get("shoulder_width"),
        "left_shoulder_visibility": posture_state.get(
            "left_shoulder_visibility",
            0.0,
        ),
        "right_shoulder_visibility": posture_state.get(
            "right_shoulder_visibility",
            0.0,
        ),
        "left_elbow_visible": bool(
            posture_state.get(
                "left_elbow_visible",
                False,
            )
        ),
        "right_elbow_visible": bool(
            posture_state.get(
                "right_elbow_visible",
                False,
            )
        ),
        "left_wrist_visible": bool(
            posture_state.get(
                "left_wrist_visible",
                False,
            )
        ),
        "right_wrist_visible": bool(
            posture_state.get(
                "right_wrist_visible",
                False,
            )
        ),
        "left_arm_movement": float(
            posture_state.get(
                "left_arm_movement",
                0.0,
            )
        ),
        "right_arm_movement": float(
            posture_state.get(
                "right_arm_movement",
                0.0,
            )
        ),
    }


def draw_anomaly_panel(
    frame,
    results,
):

    panel_height = 40 + (len(ANOMALY_ORDER) * 22)

    panel_height = min(
        panel_height,
        frame.shape[0] - 5,
    )

    x1 = frame.shape[1] - 335
    y1 = 5
    x2 = frame.shape[1] - 5
    y2 = y1 + panel_height

    overlay = frame.copy()

    cv2.rectangle(
        overlay,
        (
            x1,
            y1,
        ),
        (
            x2,
            y2,
        ),
        (
            0,
            0,
            0,
        ),
        -1,
    )

    cv2.addWeighted(
        overlay,
        0.72,
        frame,
        0.28,
        0,
        frame,
    )

    cv2.putText(
        frame,
        "ANOMALY STATUS",
        (
            x1 + 10,
            y1 + 22,
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.50,
        (
            255,
            255,
            255,
        ),
        2,
        cv2.LINE_AA,
    )

    y = y1 + 45

    for event_type in ANOMALY_ORDER:

        result = results.get(
            event_type,
            {},
        )

        confirmed = bool(
            result.get(
                "confirmed",
                False,
            )
        )

        active = bool(
            result.get(
                "active",
                False,
            )
        )

        captured = bool(
            result.get(
                "captured",
                False,
            )
        )

        if captured:

            status = "CAPTURED"

            text_color = (
                0,
                0,
                255,
            )

        elif confirmed:

            status = "CONFIRMED"

            text_color = (
                0,
                165,
                255,
            )

        elif active:

            status = "ACTIVE"

            text_color = (
                0,
                255,
                255,
            )

        else:

            status = "NORMAL"

            text_color = (
                0,
                255,
                0,
            )

        short_name = event_type.replace(
            "_",
            " ",
        )

        text = f"{short_name}: {status}"

        cv2.putText(
            frame,
            text,
            (
                x1 + 10,
                y,
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.36,
            text_color,
            1,
            cv2.LINE_AA,
        )

        y += 22

        if y >= frame.shape[0] - 8:

            break


def draw_top_status(
    frame,
    face_count,
    gaze_result,
    head_result,
    pose_result,
    posture_state,
    object_info,
):

    cv2.rectangle(
        frame,
        (
            0,
            0,
        ),
        (
            330,
            142,
        ),
        (
            0,
            0,
            0,
        ),
        -1,
    )

    if face_count == 0:

        face_text = "NO FACE"

    elif face_count == 1:

        face_text = "SINGLE FACE"

    else:

        face_text = f"MULTIPLE FACES ({face_count})"

    cv2.putText(
        frame,
        f"Face: {face_text}",
        (
            10,
            22,
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        (
            255,
            255,
            255,
        ),
        1,
        cv2.LINE_AA,
    )

    gaze_direction = str(
        gaze_result.get(
            "direction",
            "UNKNOWN",
        )
    )

    gaze_away = bool(
        gaze_result.get(
            "away",
            False,
        )
    )

    cv2.putText(
        frame,
        f"Gaze: {gaze_direction} | away={gaze_away}",
        (
            10,
            44,
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.40,
        (
            255,
            255,
            255,
        ),
        1,
        cv2.LINE_AA,
    )

    head_direction = str(
        head_result.get(
            "direction",
            "UNKNOWN",
        )
    )

    head_away = bool(
        head_result.get(
            "away",
            False,
        )
    )

    cv2.putText(
        frame,
        f"Head: {head_direction} | away={head_away}",
        (
            10,
            66,
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.40,
        (
            255,
            255,
            255,
        ),
        1,
        cv2.LINE_AA,
    )

    pose_valid = bool(
        pose_result.get(
            "valid",
            False,
        )
    )

    upper_body_visible = bool(
        posture_state.get(
            "upper_body_visible",
            False,
        )
    )

    cv2.putText(
        frame,
        (
            f"Pose: "
            f"{'VALID' if pose_valid else 'INVALID'} "
            f"| Upper body: "
            f"{'YES' if upper_body_visible else 'NO'}"
        ),
        (
            10,
            88,
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.37,
        (
            255,
            255,
            255,
        ),
        1,
        cv2.LINE_AA,
    )

    left_arm = bool(
        posture_state.get(
            "left_arm_raised",
            False,
        )
    )

    right_arm = bool(
        posture_state.get(
            "right_arm_raised",
            False,
        )
    )

    cv2.putText(
        frame,
        (
            f"Arms: "
            f"L={'UP' if left_arm else 'DOWN'} "
            f"R={'UP' if right_arm else 'DOWN'}"
        ),
        (
            10,
            110,
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.40,
        (
            255,
            255,
            255,
        ),
        1,
        cv2.LINE_AA,
    )

    cv2.putText(
        frame,
        (
            f"Objects: "
            f"P={object_info['person_count']} "
            f"Phone={'YES' if object_info['phone_detected'] else 'NO'} "
            f"Book={'YES' if object_info['book_detected'] else 'NO'}"
        ),
        (
            10,
            132,
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.32,
        (
            255,
            255,
            255,
        ),
        1,
        cv2.LINE_AA,
    )


def print_instructions():

    print()
    print("=" * 80)
    print("SKOLARIQ FULL PROCTORING CAMERA TEST")
    print("=" * 80)
    print()

    print("Q : Quit")
    print()

    print("FACE")
    print("  No face              -> NO_FACE")
    print("  Second person        -> MULTIPLE_FACES / EXTRA_PERSON")
    print()

    print("GAZE")
    print("  Look away for 3 sec  -> GAZE_AWAY")
    print()

    print("HEAD")
    print("  Turn head away       -> HEAD_AWAY")
    print()

    print("OBJECTS")
    print("  Show phone           -> PHONE_DETECTED")
    print("  Show book            -> BOOK_DETECTED")
    print("  Second person        -> EXTRA_PERSON")
    print()

    print("POSE / ARMS")
    print("  Lean LEFT            -> BODY_LEAN_LEFT")
    print("  Lean RIGHT           -> BODY_LEAN_RIGHT")
    print("  Raise LEFT arm       -> LEFT_ARM_RAISED")
    print("  Raise RIGHT arm      -> RIGHT_ARM_RAISED")
    print("  Move arm rapidly     -> UNUSUAL_ARM_MOVEMENT")
    print("  Leave upper frame    -> UPPER_BODY_NOT_VISIBLE")
    print()

    print(
        "Every confirmed anomaly goes through "
        "the real AnomalyManager/evidence pipeline."
    )

    print()
    print("=" * 80)
    print()


def main():

    camera = None
    face_detector = None
    face_landmarker = None
    gaze_tracker = None
    head_tracker = None
    object_detector = None
    pose_landmarker = None
    posture_monitor = None
    evidence_store = None
    anomaly_manager = None

    try:

        print_instructions()

        print("[CAMERA] Opening camera...")

        camera = open_camera()

        print("[CAMERA] Camera opened.")

        print("[YUNET] Loading...")

        face_detector = YuNetFaceDetector()

        print("[YUNET] Ready.")

        print("[FACE LANDMARKER] Loading...")

        face_landmarker = FaceLandmarker()

        print("[FACE LANDMARKER] Ready.")

        print("[GAZE] Initializing...")

        gaze_tracker = GazeTracker()

        print("[GAZE] Ready.")

        print("[HEAD] Initializing...")

        head_tracker = HeadTracker()

        print("[HEAD] Ready.")

        print("[YOLO26] Loading...")

        object_detector = YOLO26ObjectDetector()

        print("[YOLO26] Ready.")

        print("[POSE] Loading...")

        pose_landmarker = PoseLandmarker()

        print("[POSE] Ready.")

        print("[POSTURE] Initializing...")

        posture_monitor = PostureMonitor(
            minimum_visibility=0.50,
            lean_left_boundary=0.30,
            lean_right_boundary=0.70,
            arm_raise_margin=0.04,
            movement_window_seconds=2.0,
            excessive_movement_threshold=2.8,
        )

        print("[POSTURE] Ready.")

        evidence_store = EvidenceStore(
            student_id="local_test",
            exam_id="local_test",
            schedule_id="local_test",
            session_id="local_test",
        )

        anomaly_manager = AnomalyManager(evidence_store=evidence_store)

        print()
        print("[TEST] All components initialized.")
        print("[TEST] Starting camera loop.")

        cv2.namedWindow(
            WINDOW_NAME,
            cv2.WINDOW_NORMAL,
        )

        cv2.resizeWindow(
            WINDOW_NAME,
            1100,
            720,
        )

        last_pose_time = 0.0
        pose_result = empty_pose_result()
        posture_state = empty_posture_state()
        last_log_time = 0.0
        frame_number = 0

        while True:

            success, raw_frame = camera.read()

            if not success or raw_frame is None:

                print("[CAMERA] Failed to read frame.")

                time.sleep(0.01)

                continue

            frame_number += 1

            evidence_frame = raw_frame.copy()

            current_time = time.monotonic()

            try:

                faces = face_detector.detect(raw_frame)

                if faces is None:

                    faces = []

            except Exception as error:

                print(
                    "[YUNET ERROR]",
                    error,
                )

                faces = []

            face_count = len(faces)

            try:

                landmark_result = face_landmarker.process(raw_frame)

            except Exception as error:

                print(
                    "[FACE LANDMARKER ERROR]",
                    error,
                )

                landmark_result = {
                    "valid": False,
                    "landmarks": None,
                }

            landmark_valid = bool(
                landmark_result.get(
                    "valid",
                    False,
                )
            )

            landmarks = landmark_result.get("landmarks")

            if landmark_valid and landmarks is not None:

                try:

                    gaze_result = gaze_tracker.process(
                        landmarks,
                        raw_frame.shape,
                    )

                except Exception as error:

                    print(
                        "[GAZE ERROR]",
                        error,
                    )

                    gaze_result = {
                        "direction": "UNKNOWN",
                        "valid": False,
                        "calibrated": False,
                        "away": False,
                        "away_duration": 0.0,
                    }

            else:

                gaze_result = {
                    "direction": "UNKNOWN",
                    "valid": False,
                    "calibrated": getattr(
                        gaze_tracker,
                        "calibrated",
                        False,
                    ),
                    "away": False,
                    "away_duration": 0.0,
                }

            if landmark_valid and landmarks is not None:

                try:

                    head_result = head_tracker.process(
                        landmarks,
                        raw_frame.shape,
                    )

                except Exception as error:

                    print(
                        "[HEAD ERROR]",
                        error,
                    )

                    head_result = {
                        "direction": "UNKNOWN",
                        "valid": False,
                        "yaw": None,
                        "pitch": None,
                        "roll": None,
                        "away": False,
                        "away_duration": 0.0,
                    }

            else:

                head_result = {
                    "direction": "UNKNOWN",
                    "valid": False,
                    "yaw": None,
                    "pitch": None,
                    "roll": None,
                    "away": False,
                    "away_duration": 0.0,
                }

            try:

                object_detections = object_detector.detect(raw_frame)

                if object_detections is None:

                    object_detections = []

            except Exception as error:

                print(
                    "[YOLO26 ERROR]",
                    error,
                )

                object_detections = []

            object_info = object_anomalies(object_detections)

            pose_detection_ran = False

            if current_time - last_pose_time >= POSE_INTERVAL:

                try:

                    pose_result = pose_landmarker.process(raw_frame)

                except Exception as error:

                    print(
                        "[POSE ERROR]",
                        error,
                    )

                    pose_result = empty_pose_result()

                try:

                    posture_state = posture_monitor.process(
                        pose_result,
                        raw_frame.shape,
                    )

                except Exception as error:

                    print(
                        "[POSTURE ERROR]",
                        error,
                    )

                    posture_state = empty_posture_state()

                last_pose_time = current_time

                pose_detection_ran = True

            metadata = {
                "frame_number": frame_number,
                "face_count": face_count,
                "landmark_valid": landmark_valid,
                "gaze": {
                    "direction": gaze_result.get(
                        "direction",
                        "UNKNOWN",
                    ),
                    "valid": gaze_result.get(
                        "valid",
                        False,
                    ),
                    "calibrated": gaze_result.get(
                        "calibrated",
                        False,
                    ),
                    "away": gaze_result.get(
                        "away",
                        False,
                    ),
                    "away_duration": gaze_result.get(
                        "away_duration",
                        0.0,
                    ),
                },
                "head": {
                    "direction": head_result.get(
                        "direction",
                        "UNKNOWN",
                    ),
                    "valid": head_result.get(
                        "valid",
                        False,
                    ),
                    "yaw": head_result.get("yaw"),
                    "pitch": head_result.get("pitch"),
                    "roll": head_result.get("roll"),
                    "away": head_result.get(
                        "away",
                        False,
                    ),
                    "away_duration": head_result.get(
                        "away_duration",
                        0.0,
                    ),
                },
                "objects": object_detections,
            }

            anomaly_results = anomaly_manager.update_many(
                anomalies={
                    "NO_FACE": (face_count == 0),
                    "MULTIPLE_FACES": (face_count > 1),
                    "GAZE_AWAY": bool(
                        gaze_result.get(
                            "away",
                            False,
                        )
                    ),
                    "HEAD_AWAY": bool(
                        head_result.get(
                            "away",
                            False,
                        )
                    ),
                    "PHONE_DETECTED": (object_info["phone_detected"]),
                    "BOOK_DETECTED": (object_info["book_detected"]),
                    "EXTRA_PERSON": (object_info["extra_person"]),
                },
                frame=evidence_frame,
                metadata=metadata,
            )

            if pose_detection_ran:

                posture_valid = bool(
                    posture_state.get(
                        "valid",
                        False,
                    )
                )

                upper_body_visible = bool(
                    posture_state.get(
                        "upper_body_visible",
                        False,
                    )
                )

                pose_data = pose_metadata(
                    pose_result,
                    posture_state,
                )

                anomaly_results["BODY_LEAN_LEFT"] = anomaly_manager.update(
                    "BODY_LEAN_LEFT",
                    active=(
                        posture_valid
                        and upper_body_visible
                        and bool(
                            posture_state.get(
                                "leaning_left",
                                False,
                            )
                        )
                    ),
                    frame=evidence_frame,
                    metadata={
                        **metadata,
                        **pose_data,
                        "posture": "LEANING_LEFT",
                    },
                )

                anomaly_results["BODY_LEAN_RIGHT"] = anomaly_manager.update(
                    "BODY_LEAN_RIGHT",
                    active=(
                        posture_valid
                        and upper_body_visible
                        and bool(
                            posture_state.get(
                                "leaning_right",
                                False,
                            )
                        )
                    ),
                    frame=evidence_frame,
                    metadata={
                        **metadata,
                        **pose_data,
                        "posture": "LEANING_RIGHT",
                    },
                )

                anomaly_results["LEFT_ARM_RAISED"] = anomaly_manager.update(
                    "LEFT_ARM_RAISED",
                    active=(
                        posture_valid
                        and upper_body_visible
                        and bool(
                            posture_state.get(
                                "left_arm_raised",
                                False,
                            )
                        )
                    ),
                    frame=evidence_frame,
                    metadata={
                        **metadata,
                        **pose_data,
                        "arm": "LEFT",
                    },
                )

                anomaly_results["RIGHT_ARM_RAISED"] = anomaly_manager.update(
                    "RIGHT_ARM_RAISED",
                    active=(
                        posture_valid
                        and upper_body_visible
                        and bool(
                            posture_state.get(
                                "right_arm_raised",
                                False,
                            )
                        )
                    ),
                    frame=evidence_frame,
                    metadata={
                        **metadata,
                        **pose_data,
                        "arm": "RIGHT",
                    },
                )

                anomaly_results["UNUSUAL_ARM_MOVEMENT"] = anomaly_manager.update(
                    "UNUSUAL_ARM_MOVEMENT",
                    active=(
                        posture_valid
                        and upper_body_visible
                        and bool(
                            posture_state.get(
                                "unusual_arm_movement",
                                False,
                            )
                        )
                    ),
                    frame=evidence_frame,
                    metadata={
                        **metadata,
                        **pose_data,
                        "movement_type": ("EXCESSIVE_WRIST_MOVEMENT"),
                    },
                )

                anomaly_results["UPPER_BODY_NOT_VISIBLE"] = anomaly_manager.update(
                    "UPPER_BODY_NOT_VISIBLE",
                    active=(not posture_valid or not upper_body_visible),
                    frame=evidence_frame,
                    metadata={
                        **metadata,
                        **pose_data,
                        "reason": ("SHOULDERS_NOT_RELIABLY_VISIBLE"),
                    },
                )

            preview_frame = cv2.flip(
                raw_frame,
                1,
            )

            for face in faces:

                draw_face_box(
                    preview_frame,
                    face,
                    mirrored=True,
                )

            for detection in object_detections:

                draw_object_box(
                    preview_frame,
                    detection,
                    mirrored=True,
                )

            draw_pose(
                preview_frame,
                pose_result,
            )

            draw_top_status(
                preview_frame,
                face_count,
                gaze_result,
                head_result,
                pose_result,
                posture_state,
                object_info,
            )

            draw_anomaly_panel(
                preview_frame,
                anomaly_results,
            )

            if time.time() - last_log_time >= 1.0:

                print(
                    f"[FRAME] {frame_number} "
                    f"| faces={face_count} "
                    f"| gaze={gaze_result.get('direction')} "
                    f"| head={head_result.get('direction')} "
                    f"| pose={pose_result.get('valid')}"
                )

                for event_type in ANOMALY_ORDER:

                    result = anomaly_results.get(
                        event_type,
                        {},
                    )

                    if result.get(
                        "confirmed",
                        False,
                    ):

                        print(
                            "[ANOMALY] "
                            f"{event_type} "
                            f"| captured="
                            f"{result.get('captured', False)} "
                            f"| duration="
                            f"{float(result.get('duration', 0.0)):.2f}s "
                            f"| cooldown="
                            f"{float(result.get('cooldown_remaining', 0.0)):.2f}s"
                        )

                last_log_time = time.time()

            cv2.imshow(
                WINDOW_NAME,
                preview_frame,
            )

            key = cv2.waitKey(1) & 0xFF

            if key in (
                ord("q"),
                ord("Q"),
            ):

                print("[TEST] Q pressed.")

                break

    except KeyboardInterrupt:

        print("[TEST] Keyboard interrupt.")

    except Exception as error:

        print(
            "[TEST] Fatal error:",
            error,
        )

    finally:

        print("[TEST] Cleaning up...")

        if camera is not None:

            try:

                camera.release()

            except Exception:

                pass

        cv2.destroyAllWindows()

        if anomaly_manager is not None:

            try:

                anomaly_manager.reset_all()

            except Exception:

                pass

        if posture_monitor is not None:

            try:

                posture_monitor.reset()

            except Exception:

                pass

        if evidence_store is not None:

            try:

                evidence_store.close()

            except Exception:

                pass

        if pose_landmarker is not None:

            try:

                pose_landmarker.close()

            except Exception:

                pass

        if object_detector is not None:

            try:

                object_detector.close()

            except Exception:

                pass

        if gaze_tracker is not None:

            try:

                gaze_tracker.close()

            except Exception:

                pass

        if head_tracker is not None:

            try:

                head_tracker.close()

            except Exception:

                pass

        if face_landmarker is not None:

            try:

                face_landmarker.close()

            except Exception:

                pass

        if face_detector is not None:

            try:

                face_detector.close()

            except Exception:

                pass

        print("[TEST] Finished.")


if __name__ == "__main__":

    main()
