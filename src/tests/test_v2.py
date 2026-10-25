import os
import queue
import time
from datetime import datetime, timezone

import cv2

from src.vision.face_detector_mediapipe import MediaPipeFaceDetector
from src.vision.face_landmarker import FaceLandmarker
from src.vision.gaze_tracker import GazeTracker
from src.vision.head_tracker import HeadTracker
from src.vision.pose_landmarker import PoseLandmarker
from src.vision.object_detector_yolo26 import YOLO26ObjectDetector

from src.core.posture_monitor import PostureMonitor
from src.core.anomaly_manager import AnomalyManager
from src.core.audio_device_manager import AudioDeviceManager
from src.core.voice_activity_detector import VoiceActivityDetector
from src.core.audio_monitor import AudioMonitor

CAMERA_INDEX = 0
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

WINDOW_NAME = "Skolariq Proctoring - Production Engine Preview Test"


# Voice detection tuning for test_v2 only.
# Human speech starts a logical incident, but speech by itself is NOT immediately
# a violation. Only cumulative HUMAN-SPEECH time counts toward the threshold.
# Short pauses are excluded from the speech total and preserve the same incident.
# The incident ends only after 5 continuous seconds without human speech.
VOICE_TRIGGER_SECONDS = 1.5
VOICE_SMOOTHING_WINDOW_SECONDS = 0.06
VOICE_DETECTOR_SILENCE_RESET_SECONDS = 5.0
# Kept for backward compatibility with existing status/metadata consumers.
VOICE_SHORT_GAP_GRACE_SECONDS = 5.0
VOICE_INCIDENT_END_SILENCE_SECONDS = 5.0


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
    "VOICE_DETECTED",
]


class NoEvidenceStore:
    """
    EvidenceStore-compatible test double.

    It deliberately writes NOTHING to disk. Frames and audio buffers are not
    copied or persisted. A tiny metadata-only marker is returned so the real
    AnomalyManager keeps its normal confirmed/cooldown/capture-once behavior
    and the preview UI can still show a violation immediately.
    """

    def __init__(
        self,
        student_id=None,
        exam_id=None,
        schedule_id=None,
        session_id=None,
        *args,
        **kwargs,
    ):
        self.student_id = student_id
        self.exam_id = exam_id
        self.schedule_id = schedule_id
        self.session_id = session_id
        self.closed = False

    def _build_marker(
        self,
        event_type,
        evidence_type,
        metadata=None,
    ):
        captured_at = datetime.now(timezone.utc).isoformat()

        return {
            "event_type": str(event_type or "").upper().strip(),
            "evidence_type": evidence_type,
            "file_path": None,
            "image_path": None,
            "audio_path": None,
            "metadata_path": None,
            "client_captured_at": captured_at,
            "metadata": dict(metadata or {}),
            "event": {
                "event_type": str(event_type or "").upper().strip(),
                "captured_at": captured_at,
                "evidence_disabled": True,
            },
            "evidence_disabled": True,
        }

    def capture(
        self,
        frame,
        event_type,
        metadata=None,
        *args,
        **kwargs,
    ):
        # Intentionally do not copy, encode, save, or retain `frame`.
        return self._build_marker(
            event_type=event_type,
            evidence_type="image",
            metadata=metadata,
        )

    def capture_audio(
        self,
        pcm,
        sample_rate,
        channels=1,
        sample_width=2,
        event_type="VOICE_DETECTED",
        metadata=None,
        *args,
        **kwargs,
    ):
        # Intentionally do not copy, encode, save, or retain `pcm`.
        return self._build_marker(
            event_type=event_type,
            evidence_type="audio",
            metadata=metadata,
        )

    def close(self):
        self.closed = True
        return True


def open_camera():

    if os.name == "nt":

        camera = cv2.VideoCapture(
            CAMERA_INDEX,
            cv2.CAP_DSHOW,
        )

    else:

        camera = cv2.VideoCapture(CAMERA_INDEX)

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

    success, frame = camera.read()

    if not success or frame is None:

        camera.release()

        raise RuntimeError("Camera opened but failed to provide a valid frame.")

    return camera


def get_face_coordinates(
    face,
):

    x = None
    y = None
    width = None
    height = None

    if isinstance(
        face,
        dict,
    ):

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


def get_object_anomalies(
    object_detections,
):

    phone_detections = []
    book_detections = []
    person_detections = []

    for detection in object_detections:

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

            phone_detections.append(detection)

        elif label == "BOOK":

            book_detections.append(detection)

        elif label == "PERSON":

            person_detections.append(detection)

    return {
        "phone_detected": bool(phone_detections),
        "book_detected": bool(book_detections),
        "extra_person_detected": (len(person_detections) > 1),
        "phone_detections": phone_detections,
        "book_detections": book_detections,
        "person_detections": person_detections,
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

    cv2.putText(
        frame,
        (f"{label} " f"{confidence:.2f}"),
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

    return (
        width - 1 - raw_x,
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


def draw_anomaly_panel(
    frame,
    results,
):

    panel_height = min(
        40 + (len(ANOMALY_ORDER) * 22),
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

            status = "VIOLATION"

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

        cv2.putText(
            frame,
            (f"{event_type.replace('_', ' ')}: " f"{status}"),
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
    landmark_valid,
    gaze_result,
    head_result,
    pose_result,
    posture_result,
    object_anomalies,
):

    cv2.rectangle(
        frame,
        (
            0,
            0,
        ),
        (
            335,
            164,
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

        face_text = f"MULTIPLE FACES " f"({face_count})"

    rows = [
        (
            f"Face: {face_text}",
            22,
            0.45,
        ),
        (
            "Landmarks: " f"{'VALID' if landmark_valid else 'NOT AVAILABLE'}",
            44,
            0.40,
        ),
        (
            "Gaze: "
            f"{gaze_result.get('direction', 'UNKNOWN')} "
            "| away="
            f"{gaze_result.get('away', False)}",
            66,
            0.38,
        ),
        (
            "Head: "
            f"{head_result.get('direction', 'UNKNOWN')} "
            "| away="
            f"{head_result.get('away', False)}",
            88,
            0.38,
        ),
        (
            "Pose: "
            f"{'VALID' if pose_result.get('valid', False) else 'INVALID'} "
            "| upper_body="
            f"{posture_result.get('upper_body_visible', False)}",
            110,
            0.36,
        ),
        (
            "Arms: "
            f"L={posture_result.get('left_arm_raised', False)} "
            f"R={posture_result.get('right_arm_raised', False)} "
            f"Move={posture_result.get('unusual_arm_movement', False)}",
            132,
            0.34,
        ),
        (
            "Objects: "
            f"P={len(object_anomalies['person_detections'])} "
            f"Phone={object_anomalies['phone_detected']} "
            f"Book={object_anomalies['book_detected']}",
            154,
            0.31,
        ),
    ]

    for (
        text,
        y,
        scale,
    ) in rows:

        cv2.putText(
            frame,
            text,
            (
                10,
                y,
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            scale,
            (
                255,
                255,
                255,
            ),
            1,
            cv2.LINE_AA,
        )


def draw_audio_status(
    frame,
    audio_status,
    voice_anomaly_result,
):
    panel_width = min(
        300,
        frame.shape[1] - 10,
    )
    panel_height = 138
    x1 = 5
    y1 = max(
        170,
        frame.shape[0] - panel_height - 5,
    )
    x2 = x1 + panel_width
    y2 = min(
        frame.shape[0] - 5,
        y1 + panel_height,
    )

    overlay = frame.copy()
    cv2.rectangle(
        overlay,
        (x1, y1),
        (x2, y2),
        (0, 0, 0),
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

    if not isinstance(audio_status, dict):
        audio_status = {}
    if not isinstance(voice_anomaly_result, dict):
        voice_anomaly_result = {}

    active_microphone = audio_status.get("active_microphone")
    microphone_name = (
        active_microphone.get("name") if isinstance(active_microphone, dict) else None
    )
    if not microphone_name:
        microphone_name = "Unavailable"
    microphone_name = str(microphone_name)
    if len(microphone_name) > 34:
        microphone_name = microphone_name[:31] + "..."

    microphone_available = bool(audio_status.get("microphone_available", False))
    calibrating = bool(audio_status.get("calibrating", False))
    voice_active = bool(audio_status.get("voice_active", False))
    voice_confirmed = bool(audio_status.get("voice_confirmed", False))

    voice_duration = float(audio_status.get("voice_duration_seconds", 0.0) or 0.0)
    cumulative_voice_duration = float(
        audio_status.get(
            "cumulative_voice_duration_seconds",
            voice_duration,
        )
        or 0.0
    )

    whisper_candidate = bool(audio_status.get("whisper_candidate", False))
    detection_source = audio_status.get("detection_source") or "-"
    dbfs = float(audio_status.get("dbfs", -100.0) or -100.0)
    noise_floor = float(audio_status.get("noise_floor_dbfs", -60.0) or -60.0)

    evidence_captured = bool(voice_anomaly_result.get("captured", False))
    incident_active = bool(
        audio_status.get("incident_active", False)
        or voice_anomaly_result.get("_voice_incident_active", False)
    )
    incident_confirmed = bool(
        voice_anomaly_result.get("confirmed", False) or voice_confirmed
    )
    incident_silence = float(
        audio_status.get(
            "silence_duration_seconds",
            voice_anomaly_result.get("silence_duration_seconds", 0.0),
        )
        or 0.0
    )

    required_voice_duration = float(
        audio_status.get(
            "required_voice_duration_seconds",
            VOICE_TRIGGER_SECONDS,
        )
        or VOICE_TRIGGER_SECONDS
    )

    if calibrating:
        voice_text = "CALIBRATING"
        voice_color = (0, 255, 255)
    elif incident_active and incident_confirmed:
        voice_text = "VIOLATION / HOLD" if incident_silence > 0.0 else "VIOLATION"
        voice_color = (0, 0, 255)
    elif incident_active:
        # Human speech has been detected, but cumulative speech has NOT yet
        # crossed the anomaly threshold. This is tracking, not a violation.
        voice_text = "TRACKING / HOLD" if incident_silence > 0.0 else "TRACKING"
        voice_color = (0, 255, 255)
    elif evidence_captured:
        voice_text = "VIOLATION"
        voice_color = (0, 0, 255)
    elif voice_active:
        voice_text = "SPEECH"
        voice_color = (0, 255, 255)
    else:
        voice_text = "QUIET"
        voice_color = (0, 255, 0)

    microphone_color = (0, 255, 0) if microphone_available else (0, 0, 255)

    if incident_active:
        progress_text = (
            f"Speech: {cumulative_voice_duration:.2f}/{required_voice_duration:.2f}s "
            f"| gap={incident_silence:.2f}s"
        )
    else:
        progress_text = (
            f"Speech: {cumulative_voice_duration:.2f}/{required_voice_duration:.2f}s"
        )

    rows = [
        ("AUDIO STATUS", y1 + 20, 0.46, (255, 255, 255), 2),
        (f"Mic: {microphone_name}", y1 + 42, 0.32, microphone_color, 1),
        (f"Voice: {voice_text}", y1 + 64, 0.36, voice_color, 1),
        (progress_text, y1 + 86, 0.31, (255, 255, 255), 1),
        (
            f"Source: {detection_source} | whisper={whisper_candidate}",
            y1 + 108,
            0.31,
            (255, 255, 255),
            1,
        ),
        (
            f"Level: {dbfs:.1f} dBFS | noise={noise_floor:.1f}",
            y1 + 130,
            0.30,
            (255, 255, 255),
            1,
        ),
    ]

    for text, y, scale, color, thickness in rows:
        cv2.putText(
            frame,
            text,
            (x1 + 10, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            scale,
            color,
            thickness,
            cv2.LINE_AA,
        )


def empty_voice_anomaly_result():
    return {
        "event_type": "VOICE_DETECTED",
        # `active` means anomaly-active for the AnomalyManager/UI. Human speech
        # tracking before 3 cumulative seconds intentionally leaves this False.
        "active": False,
        "confirmed": False,
        "captured": False,
        "duration": 0.0,
        "required_duration": VOICE_TRIGGER_SECONDS,
        "cooldown": 0.0,
        "cooldown_remaining": 0.0,
        "evidence": None,
        "api_violation": None,
        "incident_duration_seconds": 0.0,
        "cumulative_voice_duration_seconds": 0.0,
        "silence_duration_seconds": 0.0,
        "short_gap_grace_seconds": VOICE_SHORT_GAP_GRACE_SECONDS,
        "incident_end_silence_seconds": VOICE_INCIDENT_END_SILENCE_SECONDS,
        "_voice_incident_active": False,
        "_voice_incident_started_at": None,
        "_voice_last_activity_at": None,
        "_voice_silence_started_at": None,
        "_voice_speech_active": False,
        "_voice_incident_captured": False,
        "_voice_incident_number": 0,
        "_voice_core_incident_events_seen": False,
    }


def configure_voice_anomaly_for_test(anomaly_manager):
    """
    Configure the AnomalyManager to accept a VOICE_DETECTED event immediately
    AFTER the core VoiceActivityDetector has already accumulated the required
    3 seconds of actual human speech.

    Human speech itself is not an anomaly here. The core detector owns the
    cumulative-speech threshold and the 5-second continuous-silence boundary.
    """
    rules = getattr(anomaly_manager, "rules", None)
    if not isinstance(rules, dict):
        print(
            "[AUDIO] Warning: AnomalyManager rules are not exposed; "
            "core-confirmed voice events will use the manager defaults."
        )
        return False

    voice_rule = rules.get("VOICE_DETECTED")
    if not isinstance(voice_rule, dict):
        print(
            "[AUDIO] Warning: VOICE_DETECTED anomaly rule is unavailable; "
            "core-confirmed voice events will use the manager defaults."
        )
        return False

    # The 3-second threshold is already enforced by VoiceActivityDetector. Do
    # not make AnomalyManager wait another 3 seconds after confirmation arrives.
    voice_rule["duration"] = 0.0
    voice_rule["minimum_audio_duration"] = 0.0
    voice_rule["recovery_grace"] = 0.0
    voice_rule["capture_once_per_incident"] = True

    print(
        "[AUDIO] VOICE_DETECTED uses cumulative human-speech confirmation "
        f"| speech_threshold={VOICE_TRIGGER_SECONDS:.1f}s "
        f"| incident_end_silence={VOICE_INCIDENT_END_SILENCE_SECONDS:.1f}s "
        "| pause_time_excluded=True"
    )
    return True


def _start_voice_tracking_incident(
    result,
    now,
    incident_number=None,
    core_event=False,
):
    if result.get("_voice_incident_active", False):
        if core_event:
            result["_voice_core_incident_events_seen"] = True
        return result

    previous_number = int(result.get("_voice_incident_number", 0) or 0)
    if incident_number is None:
        incident_number = previous_number + 1
    else:
        try:
            incident_number = int(incident_number)
        except (TypeError, ValueError):
            incident_number = previous_number + 1

    result.update(
        {
            "active": False,
            "confirmed": False,
            "captured": False,
            "duration": 0.0,
            "required_duration": VOICE_TRIGGER_SECONDS,
            "incident_duration_seconds": 0.0,
            "cumulative_voice_duration_seconds": 0.0,
            "silence_duration_seconds": 0.0,
            "_voice_incident_active": True,
            "_voice_incident_started_at": now,
            "_voice_last_activity_at": now,
            "_voice_silence_started_at": None,
            "_voice_speech_active": True,
            "_voice_incident_captured": False,
            "_voice_incident_number": incident_number,
        }
    )
    if core_event:
        result["_voice_core_incident_events_seen"] = True

    print(
        "[AUDIO][VOICE TRACKING STARTED] "
        f"incident={incident_number} "
        f"threshold={VOICE_TRIGGER_SECONDS:.1f}s cumulative speech"
    )
    return result


def _refresh_voice_tracking_state(result, now):
    if not result.get("_voice_incident_active", False):
        result["silence_duration_seconds"] = 0.0
        return result

    silence_started_at = result.get("_voice_silence_started_at")
    if silence_started_at is None:
        result["silence_duration_seconds"] = 0.0
    else:
        try:
            result["silence_duration_seconds"] = max(
                0.0,
                float(now) - float(silence_started_at),
            )
        except (TypeError, ValueError):
            result["silence_duration_seconds"] = 0.0

    result["required_duration"] = VOICE_TRIGGER_SECONDS
    result["short_gap_grace_seconds"] = VOICE_SHORT_GAP_GRACE_SECONDS
    result["incident_end_silence_seconds"] = VOICE_INCIDENT_END_SILENCE_SECONDS

    # Before 3 cumulative seconds, this is TRACKING only, not an anomaly.
    if not result.get("confirmed", False):
        result["active"] = False
    else:
        # Once confirmed, short pauses do not deactivate the anomaly.
        result["active"] = True

    return result


def _close_voice_tracking_incident(
    result,
    anomaly_manager,
    now,
    cumulative_voice_duration=None,
    continuous_silence=None,
    confirmed=None,
    ended_by_core=False,
):
    if not result.get("_voice_incident_active", False):
        return result

    incident_number = int(result.get("_voice_incident_number", 0) or 0)
    was_confirmed = bool(
        result.get("confirmed", False) if confirmed is None else confirmed
    )

    if cumulative_voice_duration is None:
        cumulative_voice_duration = float(
            result.get("cumulative_voice_duration_seconds", 0.0) or 0.0
        )
    else:
        cumulative_voice_duration = float(cumulative_voice_duration or 0.0)

    if continuous_silence is None:
        continuous_silence = float(result.get("silence_duration_seconds", 0.0) or 0.0)
    else:
        continuous_silence = float(continuous_silence or 0.0)

    ended_result = None
    if was_confirmed:
        ended_result = anomaly_manager.update_audio(
            event_type="VOICE_DETECTED",
            active=False,
            audio_evidence=None,
            metadata={
                "incident_number": incident_number,
                "cumulative_voice_duration_seconds": round(
                    cumulative_voice_duration,
                    3,
                ),
                "continuous_silence_seconds": round(continuous_silence, 3),
                "confirmation_threshold_seconds": VOICE_TRIGGER_SECONDS,
                "pause_time_excluded": True,
                "ended_by_core_incident_event": bool(ended_by_core),
            },
        )

    fresh = empty_voice_anomaly_result()
    fresh["_voice_incident_number"] = incident_number
    fresh["_voice_core_incident_events_seen"] = bool(
        result.get("_voice_core_incident_events_seen", False) or ended_by_core
    )

    if isinstance(ended_result, dict):
        fresh["cooldown"] = float(ended_result.get("cooldown", 0.0) or 0.0)
        fresh["cooldown_remaining"] = float(
            ended_result.get("cooldown_remaining", 0.0) or 0.0
        )

    print(
        "[AUDIO][VOICE INCIDENT ENDED] "
        f"incident={incident_number} "
        f"cumulative_speech={cumulative_voice_duration:.2f}s "
        f"continuous_silence={continuous_silence:.2f}s "
        f"anomaly={was_confirmed}"
    )
    return fresh


def _legacy_finish_voice_incident_if_needed(
    result,
    anomaly_manager,
    now,
):
    """Fallback for older AudioMonitor versions without INCIDENT_ENDED."""
    result = _refresh_voice_tracking_state(result, now)

    if not result.get("_voice_incident_active", False):
        return result

    if result.get("_voice_core_incident_events_seen", False):
        return result

    silence_elapsed = float(result.get("silence_duration_seconds", 0.0) or 0.0)
    if silence_elapsed < VOICE_INCIDENT_END_SILENCE_SECONDS:
        return result

    return _close_voice_tracking_incident(
        result=result,
        anomaly_manager=anomaly_manager,
        now=now,
        continuous_silence=silence_elapsed,
        ended_by_core=False,
    )


def process_audio_events(
    audio_event_queue,
    anomaly_manager,
    current_result,
):
    """
    Convert AudioMonitor events into the preview's VOICE_DETECTED state.

    Required behavior:
    - Proper human speech starts TRACKING, not an anomaly.
    - Only actual detected human-speech frames contribute to cumulative speech.
    - Silence/pause time contributes zero seconds to the anomaly threshold.
    - Speech returning before 5 continuous seconds of silence continues the same
      incident and continues from the previous cumulative speech total.
    - The anomaly is confirmed only once cumulative speech reaches 3 seconds.
    - Once confirmed, it remains the same anomaly through short pauses.
    - The logical incident ends only after 5 continuous seconds without speech.
    - No evidence media is written because NoEvidenceStore remains in use.

    New AudioMonitor versions emit VOICE_INCIDENT_STARTED/ENDED. Legacy
    VOICE_ACTIVITY_STARTED/ENDED behavior is retained as a fallback.
    """
    result = dict(current_result or empty_voice_anomaly_result())
    now = time.monotonic()
    result = _legacy_finish_voice_incident_if_needed(
        result=result,
        anomaly_manager=anomaly_manager,
        now=now,
    )

    while True:
        try:
            payload = audio_event_queue.get_nowait()
        except queue.Empty:
            break

        if not isinstance(payload, dict):
            continue

        event_type = str(payload.get("event_type", "")).upper().strip()
        now = time.monotonic()

        if event_type == "VOICE_INCIDENT_STARTED":
            result = _start_voice_tracking_incident(
                result=result,
                now=now,
                incident_number=payload.get("incident_number"),
                core_event=True,
            )
            continue

        if event_type == "VOICE_ACTIVITY_STARTED":
            if not result.get("_voice_incident_active", False):
                result = _start_voice_tracking_incident(
                    result=result,
                    now=now,
                    incident_number=payload.get("incident_number"),
                    core_event=False,
                )

            result["_voice_speech_active"] = True
            result["_voice_last_activity_at"] = now
            result["_voice_silence_started_at"] = None
            result["silence_duration_seconds"] = 0.0
            continue

        if event_type == "VOICE_ACTIVITY_ENDED":
            if result.get("_voice_incident_active", False):
                result["_voice_speech_active"] = False
                if result.get("_voice_silence_started_at") is None:
                    result["_voice_silence_started_at"] = now
                    print(
                        "[AUDIO][VOICE PAUSE] "
                        "Speech stopped; cumulative speech is preserved. "
                        f"Waiting {VOICE_INCIDENT_END_SILENCE_SECONDS:.1f}s "
                        "of continuous silence before ending the incident."
                    )
                result = _refresh_voice_tracking_state(result, now)
            continue

        if event_type == "VOICE_DETECTED":
            if not result.get("_voice_incident_active", False):
                result = _start_voice_tracking_incident(
                    result=result,
                    now=now,
                    incident_number=payload.get("incident_number"),
                    core_event=False,
                )

            cumulative_voice_duration = float(
                payload.get(
                    "cumulative_voice_duration_seconds",
                    payload.get("voice_duration_seconds", VOICE_TRIGGER_SECONDS),
                )
                or 0.0
            )
            result["cumulative_voice_duration_seconds"] = cumulative_voice_duration
            result["incident_duration_seconds"] = cumulative_voice_duration
            result["duration"] = cumulative_voice_duration
            result["_voice_last_activity_at"] = now
            result["_voice_silence_started_at"] = None
            result["_voice_speech_active"] = True
            result["silence_duration_seconds"] = 0.0

            audio_evidence = payload.get("evidence_audio")
            metadata = {
                key: value
                for key, value in payload.items()
                if key not in {"event_type", "evidence_audio"}
            }
            metadata.update(
                {
                    "incident_number": result.get("_voice_incident_number", 0),
                    "cumulative_voice_duration_seconds": round(
                        cumulative_voice_duration,
                        3,
                    ),
                    "confirmation_threshold_seconds": VOICE_TRIGGER_SECONDS,
                    "incident_end_silence_seconds": (
                        VOICE_INCIDENT_END_SILENCE_SECONDS
                    ),
                    "pause_time_excluded": True,
                    "evidence_file_saving_disabled": True,
                }
            )

            manager_result = anomaly_manager.update_audio(
                event_type="VOICE_DETECTED",
                active=True,
                audio_evidence=audio_evidence,
                metadata=metadata,
            )
            if not isinstance(manager_result, dict):
                manager_result = {}

            result["active"] = True
            result["confirmed"] = True
            result["captured"] = bool(
                result.get("_voice_incident_captured", False)
                or manager_result.get("captured", False)
            )
            result["_voice_incident_captured"] = result["captured"]
            result["evidence"] = manager_result.get("evidence")
            result["api_violation"] = manager_result.get("api_violation")
            result["cooldown"] = float(manager_result.get("cooldown", 0.0) or 0.0)
            result["cooldown_remaining"] = float(
                manager_result.get("cooldown_remaining", 0.0) or 0.0
            )

            print(
                "[AUDIO][VOICE VIOLATION CONFIRMED] "
                f"incident={result.get('_voice_incident_number', 0)} "
                f"cumulative_speech={cumulative_voice_duration:.2f}s "
                f"threshold={VOICE_TRIGGER_SECONDS:.1f}s"
            )
            continue

        if event_type == "VOICE_INCIDENT_ENDED":
            result["_voice_core_incident_events_seen"] = True
            cumulative_voice_duration = float(
                payload.get(
                    "cumulative_voice_duration_seconds",
                    result.get("cumulative_voice_duration_seconds", 0.0),
                )
                or 0.0
            )
            continuous_silence = float(
                payload.get(
                    "continuous_silence_seconds",
                    result.get("silence_duration_seconds", 0.0),
                )
                or 0.0
            )
            result = _close_voice_tracking_incident(
                result=result,
                anomaly_manager=anomaly_manager,
                now=now,
                cumulative_voice_duration=cumulative_voice_duration,
                continuous_silence=continuous_silence,
                confirmed=bool(
                    payload.get(
                        "confirmed",
                        result.get("confirmed", False),
                    )
                ),
                ended_by_core=True,
            )
            continue

        if event_type in {
            "MIC_UNAVAILABLE",
            "MIC_CHANGE_REQUIRED",
            "MIC_STREAM_ERROR",
            "MIC_DEVICE_LIST_CHANGED",
            "DEFAULT_MIC_CHANGED",
            "MIC_RECOVERED",
            "MIC_DEVICE_CHANGED",
            "MIC_CHANGE_FAILED",
            "MIC_INPUT_OVERFLOW",
            "AUDIO_MONITOR_ERROR",
            "VOICE_DETECTION_ERROR",
        }:
            safe_payload = {
                key: value for key, value in payload.items() if key != "evidence_audio"
            }
            print(f"[AUDIO][{event_type}]", safe_payload)

    now = time.monotonic()
    result = _legacy_finish_voice_incident_if_needed(
        result=result,
        anomaly_manager=anomaly_manager,
        now=now,
    )
    result = _refresh_voice_tracking_state(result, now)
    return result


def print_instructions():

    print()

    print("=" * 80)

    print("SKOLARIQ PRODUCTION PROCTORING ENGINE PREVIEW TEST")

    print("=" * 80)

    print()

    print(
        "This test uses the same camera, microphone, "
        "detectors and anomaly manager intended for the native "
        "proctor application. Evidence files are NOT saved in test_v2."
    )

    print()

    print(
        "Kiosk, keyboard lockdown, authentication, REST "
        "submission and Socket.IO transport are omitted."
    )

    print()

    print("Q : Quit")

    print()

    print("FACE")

    print("  No face              -> NO_FACE")

    print("  Second face          -> MULTIPLE_FACES (MediaPipe Face Detector)")

    print("  Second person        -> EXTRA_PERSON (YOLO)")

    print()

    print("GAZE")

    print("  Look away            -> GAZE_AWAY")

    print()

    print("HEAD")

    print("  Turn head away       -> HEAD_AWAY")

    print()

    print("OBJECTS")

    print("  Show phone           -> PHONE_DETECTED")

    print("  Show book            -> BOOK_DETECTED")

    print("  Second person        -> EXTRA_PERSON")

    print()

    print("POSTURE")

    print("  Lean LEFT            -> BODY_LEAN_LEFT")

    print("  Lean RIGHT           -> BODY_LEAN_RIGHT")

    print("  Raise LEFT arm       -> LEFT_ARM_RAISED")

    print("  Raise RIGHT arm      -> RIGHT_ARM_RAISED")

    print("  Move arms rapidly    -> UNUSUAL_ARM_MOVEMENT")

    print("  Upper body hidden    -> UPPER_BODY_NOT_VISIBLE")

    print()

    print("AUDIO")

    print("  Valid human speech   -> starts TRACKING; not a violation yet")

    print("  Cumulative speech    -> VOICE_DETECTED only after 3.0 sec")

    print("  Quiet whisper        -> whisper-sensitive human-speech tracking")

    print("  Pauses under 5 sec   -> same incident; pause time is NOT counted")

    print("  5 sec full silence   -> current voice incident ends")

    print()

    print("=" * 80)

    print()


def main():

    camera = None

    face_detector = None

    face_landmarker = None

    gaze_tracker = None

    head_tracker = None

    pose_landmarker = None

    posture_monitor = None

    object_detector = None

    evidence_store = None

    anomaly_manager = None

    audio_device_manager = None

    voice_activity_detector = None

    audio_monitor = None

    audio_event_queue = queue.Queue()

    audio_anomaly_result = empty_voice_anomaly_result()

    try:

        print_instructions()

        print("[TEST] Performing mandatory camera and microphone check...")

        print("[CAMERA] Starting camera...")

        camera = open_camera()

        print("[CAMERA] Camera opened successfully.")

        print("[MICROPHONE] Discovering microphone devices...")

        audio_device_manager = AudioDeviceManager()

        microphone_selection = audio_device_manager.select_default_microphone()

        if not microphone_selection.get("success"):

            raise RuntimeError(
                "No valid physical microphone could be selected. "
                f"Reason: "
                f"{microphone_selection.get('reason', 'UNKNOWN')}"
            )

        selected_microphone = microphone_selection["device"]

        print(
            "[MICROPHONE] Selected and validated: "
            f"{selected_microphone.get('name')} "
            f"| index="
            f"{selected_microphone.get('index')} "
            f"| sample_rate="
            f"{selected_microphone.get('sample_rate')}"
        )

        print("[VOICE] Initializing voice activity detector...")

        voice_activity_detector = VoiceActivityDetector(
            frame_duration_ms=30,
            required_voice_duration=VOICE_TRIGGER_SECONDS,
            aggressiveness=1,
            calibration_seconds=1.0,
            smoothing_window_seconds=VOICE_SMOOTHING_WINDOW_SECONDS,
            minimum_voice_ratio=0.40,
            silence_reset_seconds=VOICE_DETECTOR_SILENCE_RESET_SECONDS,
            whisper_noise_margin_db=6.0,
            whisper_absolute_floor_db=-58.0,
        )

        print("[VOICE] Voice activity detector initialized.")

        print("[MEDIAPIPE FACE DETECTOR] Loading face detector...")

        face_detector = MediaPipeFaceDetector()

        print("[MEDIAPIPE FACE DETECTOR] Face detector loaded successfully.")

        print("[FACE LANDMARKER] Loading MediaPipe Face Landmarker...")

        face_landmarker = FaceLandmarker()

        print("[FACE LANDMARKER] MediaPipe model loaded successfully.")

        print("[GAZE] Initializing gaze tracker...")

        gaze_tracker = GazeTracker()

        print("[GAZE] Gaze tracker initialized.")

        print("[HEAD] Initializing head tracker...")

        head_tracker = HeadTracker()

        print("[HEAD] Head tracker initialized.")

        print("[POSE] Loading MediaPipe Pose Landmarker...")

        pose_landmarker = PoseLandmarker()

        print("[POSE] Pose Landmarker loaded successfully.")

        print("[POSTURE] Initializing posture monitor...")

        posture_monitor = PostureMonitor()

        print("[POSTURE] Posture monitor initialized.")

        print("[YOLO26] Loading object detector...")

        object_detector = YOLO26ObjectDetector()

        print("[YOLO26] Object detector loaded successfully.")

        print("[EVIDENCE] Evidence file saving is DISABLED for test_v2.")

        evidence_store = NoEvidenceStore(
            student_id="local_test",
            exam_id="local_test",
            schedule_id="local_test",
            session_id="local_test",
        )

        print("[EVIDENCE] No-write evidence adapter initialized.")

        print("[ANOMALY] Initializing anomaly manager...")

        anomaly_manager = AnomalyManager(evidence_store=evidence_store)

        configure_voice_anomaly_for_test(anomaly_manager)

        print("[ANOMALY] Anomaly manager initialized.")

        print("[AUDIO] Starting audio monitor...")

        audio_monitor = AudioMonitor(
            device_manager=audio_device_manager,
            voice_detector=voice_activity_detector,
            event_callback=audio_event_queue.put,
            device_poll_interval=2.0,
            evidence_buffer_seconds=8.0,
            reconnect_interval=2.0,
        )

        if not audio_monitor.start():

            raise RuntimeError("Unable to start audio monitor.")

        print("[AUDIO] Audio monitor started successfully.")

        print()

        print("[TEST] Production-equivalent detection pipeline initialized.")

        print("[TEST] Starting full detection loop with camera preview.")

        print()

        cv2.namedWindow(
            WINDOW_NAME,
            cv2.WINDOW_NORMAL,
        )

        cv2.resizeWindow(
            WINDOW_NAME,
            1100,
            720,
        )

        frame_count = 0

        last_log_time = 0.0

        while True:

            success, frame = camera.read()

            if not success or frame is None:

                print("[CAMERA] Failed to read frame.")

                time.sleep(0.05)

                continue

            frame_count += 1

            audio_anomaly_result = process_audio_events(
                audio_event_queue=audio_event_queue,
                anomaly_manager=anomaly_manager,
                current_result=audio_anomaly_result,
            )

            try:

                faces = face_detector.detect(frame)

                if faces is None:

                    faces = []

            except Exception as error:

                print(
                    "[MEDIAPIPE FACE DETECTOR] Detection error:",
                    error,
                )

                faces = []

            face_count = len(faces)

            try:

                landmark_result = face_landmarker.process(frame)

            except Exception as error:

                print(
                    "[FACE LANDMARKER] Processing error:",
                    error,
                )

                landmark_result = {
                    "valid": False,
                    "landmarks": None,
                    "face_count": 0,
                }

            landmark_valid = bool(
                landmark_result.get(
                    "valid",
                    False,
                )
            )

            landmarks = landmark_result.get("landmarks") if landmark_result else None

            if landmarks is not None and landmark_valid:

                try:

                    gaze_result = gaze_tracker.process(
                        landmarks,
                        frame.shape,
                    )

                except Exception as error:

                    print(
                        "[GAZE] Processing error:",
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

            if landmarks is not None and landmark_valid:

                try:

                    head_result = head_tracker.process(
                        landmarks,
                        frame.shape,
                    )

                except Exception as error:

                    print(
                        "[HEAD] Processing error:",
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

                pose_result = pose_landmarker.process(frame)

            except Exception as error:

                print(
                    "[POSE] Processing error:",
                    error,
                )

                pose_result = {
                    "valid": False,
                    "pose_count": 0,
                    "landmarks": None,
                    "world_landmarks": None,
                }

            try:

                posture_result = posture_monitor.process(
                    pose_result,
                    frame.shape,
                )

            except Exception as error:

                print(
                    "[POSTURE] Processing error:",
                    error,
                )

                posture_result = {
                    "valid": False,
                    "upper_body_visible": False,
                    "leaning_left": False,
                    "leaning_right": False,
                    "left_arm_raised": False,
                    "right_arm_raised": False,
                    "unusual_arm_movement": False,
                    "left_arm_movement": 0.0,
                    "right_arm_movement": 0.0,
                }

            try:

                object_detections = object_detector.detect(frame)

                if object_detections is None:

                    object_detections = []

            except Exception as error:

                print(
                    "[YOLO26] Detection error:",
                    error,
                )

                object_detections = []

            object_anomaly_state = get_object_anomalies(object_detections)

            anomaly_metadata = {
                "frame_number": frame_count,
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
                "pose": {
                    "valid": posture_result.get(
                        "valid",
                        False,
                    ),
                    "pose_count": pose_result.get(
                        "pose_count",
                        0,
                    ),
                    "upper_body_visible": posture_result.get(
                        "upper_body_visible",
                        False,
                    ),
                    "leaning_left": posture_result.get(
                        "leaning_left",
                        False,
                    ),
                    "leaning_right": posture_result.get(
                        "leaning_right",
                        False,
                    ),
                    "left_arm_raised": posture_result.get(
                        "left_arm_raised",
                        False,
                    ),
                    "right_arm_raised": posture_result.get(
                        "right_arm_raised",
                        False,
                    ),
                    "unusual_arm_movement": posture_result.get(
                        "unusual_arm_movement",
                        False,
                    ),
                    "left_arm_movement": posture_result.get(
                        "left_arm_movement",
                        0.0,
                    ),
                    "right_arm_movement": posture_result.get(
                        "right_arm_movement",
                        0.0,
                    ),
                    "shoulder_center_x": posture_result.get("shoulder_center_x"),
                    "shoulder_width": posture_result.get("shoulder_width"),
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
                    "PHONE_DETECTED": object_anomaly_state["phone_detected"],
                    "BOOK_DETECTED": object_anomaly_state["book_detected"],
                    "EXTRA_PERSON": object_anomaly_state["extra_person_detected"],
                    "BODY_LEAN_LEFT": bool(
                        posture_result.get(
                            "leaning_left",
                            False,
                        )
                    ),
                    "BODY_LEAN_RIGHT": bool(
                        posture_result.get(
                            "leaning_right",
                            False,
                        )
                    ),
                    "LEFT_ARM_RAISED": bool(
                        posture_result.get(
                            "left_arm_raised",
                            False,
                        )
                    ),
                    "RIGHT_ARM_RAISED": bool(
                        posture_result.get(
                            "right_arm_raised",
                            False,
                        )
                    ),
                    "UNUSUAL_ARM_MOVEMENT": bool(
                        posture_result.get(
                            "unusual_arm_movement",
                            False,
                        )
                    ),
                    "UPPER_BODY_NOT_VISIBLE": (
                        posture_result.get(
                            "valid",
                            False,
                        )
                        and not posture_result.get(
                            "upper_body_visible",
                            False,
                        )
                    ),
                },
                frame=frame,
                metadata=anomaly_metadata,
            )

            anomaly_results["VOICE_DETECTED"] = dict(audio_anomaly_result)

            if audio_monitor is not None:

                audio_status = audio_monitor.get_status()

            else:

                audio_status = {
                    "running": False,
                    "microphone_available": False,
                    "active_microphone": None,
                    "calibrating": False,
                    "voice_active": False,
                    "voice_confirmed": False,
                    "voice_duration_seconds": 0.0,
                    "whisper_candidate": False,
                    "detection_source": None,
                    "dbfs": -100.0,
                    "noise_floor_dbfs": -60.0,
                }

            preview_frame = cv2.flip(
                frame,
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
                landmark_valid,
                gaze_result,
                head_result,
                pose_result,
                posture_result,
                object_anomaly_state,
            )

            draw_anomaly_panel(
                preview_frame,
                anomaly_results,
            )

            draw_audio_status(
                preview_frame,
                audio_status,
                audio_anomaly_result,
            )

            current_time = time.time()

            if current_time - last_log_time >= 1.0:

                if face_count == 0:

                    print("[DETECTION] NO FACE")

                elif face_count == 1:

                    print("[DETECTION] SINGLE FACE")

                else:

                    print("[DETECTION] " f"MULTIPLE FACES: " f"{face_count}")

                if landmark_valid:

                    print("[FACE LANDMARKER] VALID")

                else:

                    print("[FACE LANDMARKER] NOT AVAILABLE")

                print(
                    "[GAZE] "
                    f"{gaze_result.get('direction', 'UNKNOWN')} "
                    "| valid="
                    f"{gaze_result.get('valid', False)} "
                    "| calibrated="
                    f"{gaze_result.get('calibrated', False)} "
                    "| away="
                    f"{gaze_result.get('away', False)}"
                )

                print(
                    "[HEAD] "
                    f"{head_result.get('direction', 'UNKNOWN')} "
                    "| yaw="
                    f"{head_result.get('yaw')} "
                    "| pitch="
                    f"{head_result.get('pitch')} "
                    "| roll="
                    f"{head_result.get('roll')} "
                    "| away="
                    f"{head_result.get('away', False)}"
                )

                print(
                    "[POSE] "
                    f"valid="
                    f"{posture_result.get('valid', False)} "
                    "| upper_body="
                    f"{posture_result.get('upper_body_visible', False)} "
                    "| lean_left="
                    f"{posture_result.get('leaning_left', False)} "
                    "| lean_right="
                    f"{posture_result.get('leaning_right', False)} "
                    "| left_arm="
                    f"{posture_result.get('left_arm_raised', False)} "
                    "| right_arm="
                    f"{posture_result.get('right_arm_raised', False)} "
                    "| unusual_movement="
                    f"{posture_result.get('unusual_arm_movement', False)}"
                )

                if object_detections:

                    for detection in object_detections:

                        print(
                            "[OBJECT] "
                            f"{detection.get('label', 'OBJECT')} "
                            "| confidence="
                            f"{float(detection.get('confidence', 0.0)):.3f} "
                            "| box=("
                            f"{detection.get('x')},"
                            f"{detection.get('y')},"
                            f"{detection.get('x2')},"
                            f"{detection.get('y2')}"
                            ")"
                        )

                else:

                    print("[OBJECT] No monitored objects detected.")

                active_microphone = audio_status.get("active_microphone") or {}

                print(
                    "[AUDIO] "
                    f"mic="
                    f"{active_microphone.get('name', 'Unavailable')} "
                    "| available="
                    f"{audio_status.get('microphone_available', False)} "
                    "| calibrating="
                    f"{audio_status.get('calibrating', False)} "
                    "| voice_active="
                    f"{audio_status.get('voice_active', False)} "
                    "| voice_confirmed="
                    f"{audio_status.get('voice_confirmed', False)} "
                    "| duration="
                    f"{float(audio_status.get('voice_duration_seconds', 0.0)):.2f}s "
                    "| whisper="
                    f"{audio_status.get('whisper_candidate', False)} "
                    "| source="
                    f"{audio_status.get('detection_source')} "
                    "| dbfs="
                    f"{float(audio_status.get('dbfs', -100.0)):.1f}"
                )

                for (
                    event_type,
                    result,
                ) in anomaly_results.items():

                    if result.get(
                        "confirmed",
                        False,
                    ):

                        cooldown_remaining = float(
                            result.get(
                                "cooldown_remaining",
                                0.0,
                            )
                        )

                        print(
                            "[ANOMALY] "
                            f"{event_type} "
                            "| confirmed=True "
                            "| captured="
                            f"{result.get('captured', False)} "
                            "| cooldown_remaining="
                            f"{cooldown_remaining:.1f}s"
                        )

                last_log_time = current_time

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

        print()

        print("[TEST] Keyboard interrupt.")

    except Exception as error:

        print()

        print(
            "[TEST] Fatal error:",
            error,
        )

    finally:

        print()

        print("[TEST] Cleaning up...")

        if audio_monitor is not None:

            try:

                audio_monitor.close()

            except Exception as error:

                print(
                    "[AUDIO] Cleanup error:",
                    error,
                )

        if anomaly_manager is not None:

            try:

                anomaly_manager.close()

            except Exception as error:

                print(
                    "[ANOMALY] Cleanup error:",
                    error,
                )

        if evidence_store is not None:

            try:

                evidence_store.close()

            except Exception as error:

                print(
                    "[EVIDENCE] Cleanup error:",
                    error,
                )

        if posture_monitor is not None:

            try:

                posture_monitor.reset()

            except Exception as error:

                print(
                    "[POSTURE] Cleanup error:",
                    error,
                )

        if camera is not None:

            try:

                camera.release()

            except Exception as error:

                print(
                    "[CAMERA] Cleanup error:",
                    error,
                )

        if object_detector is not None:

            try:

                object_detector.close()

            except Exception as error:

                print(
                    "[YOLO26] Cleanup error:",
                    error,
                )

        if pose_landmarker is not None:

            try:

                pose_landmarker.close()

            except Exception as error:

                print(
                    "[POSE] Cleanup error:",
                    error,
                )

        if gaze_tracker is not None:

            try:

                gaze_tracker.close()

            except Exception as error:

                print(
                    "[GAZE] Cleanup error:",
                    error,
                )

        if head_tracker is not None:

            try:

                head_tracker.close()

            except Exception as error:

                print(
                    "[HEAD] Cleanup error:",
                    error,
                )

        if face_landmarker is not None:

            try:

                face_landmarker.close()

            except Exception as error:

                print(
                    "[FACE LANDMARKER] Cleanup error:",
                    error,
                )

        if face_detector is not None:

            try:

                face_detector.close()

            except Exception as error:

                print(
                    "[MEDIAPIPE FACE DETECTOR] Cleanup error:",
                    error,
                )

        try:

            cv2.destroyAllWindows()

        except Exception:

            pass

        print("[TEST] Finished.")


if __name__ == "__main__":

    main()
