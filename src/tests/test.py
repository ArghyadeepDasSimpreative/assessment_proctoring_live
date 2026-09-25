import os
import queue
import tempfile
import threading
import time
from collections import deque
from datetime import datetime, timezone

import cv2

from src.vision.face_detector_yunet import YuNetFaceDetector
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

from src.evidence.evidence_store import EvidenceStore

CAMERA_INDEX = 0
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

WINDOW_NAME = "Skolariq Proctoring - Production Engine Preview Test"


# Voice detection tuning for test.py only.
# The core detector still decides whether a sound is human speech. Once it
# recognizes a valid speech burst, the test confirms the anomaly immediately.
VOICE_TRIGGER_SECONDS = 0.03
VOICE_SMOOTHING_WINDOW_SECONDS = 0.06
VOICE_DETECTOR_SILENCE_RESET_SECONDS = 0.35
VOICE_SHORT_GAP_GRACE_SECONDS = 2.5
VOICE_INCIDENT_END_SILENCE_SECONDS = 5.0
VOICE_EVIDENCE_PRE_ROLL_SECONDS = 0.75
VOICE_EVIDENCE_SPOOL_MEMORY_BYTES = 4 * 1024 * 1024


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


class DeferredAudioEvidenceStore:
    """
    EvidenceStore-compatible adapter used by this test.

    Image evidence is saved immediately exactly as before.

    Audio evidence is different:
    AnomalyManager receives a small metadata marker immediately so its normal
    confirmation, cooldown, capture-once and UI behavior stays intact, but the
    WAV file itself is deferred until the full VOICE_DETECTED incident ends.
    """

    def __init__(
        self,
        evidence_store,
    ):
        if evidence_store is None:
            raise ValueError("DeferredAudioEvidenceStore requires an EvidenceStore.")

        self.evidence_store = evidence_store
        self.closed = False

    def __getattr__(
        self,
        name,
    ):
        return getattr(
            self.evidence_store,
            name,
        )

    def capture(
        self,
        frame,
        event_type,
        metadata=None,
        *args,
        **kwargs,
    ):
        return self.evidence_store.capture(
            frame=frame,
            event_type=event_type,
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
        captured_at = datetime.now(timezone.utc).isoformat()

        return {
            "event_type": str(event_type or "").upper().strip(),
            "evidence_type": "audio",
            "file_path": None,
            "audio_path": None,
            "metadata_path": None,
            "client_captured_at": captured_at,
            "metadata": dict(metadata or {}),
            "event": {
                "event_type": str(event_type or "").upper().strip(),
                "captured_at": captured_at,
                "audio_capture_deferred": True,
            },
            "audio_capture_deferred": True,
        }

    def persist_audio(
        self,
        pcm,
        sample_rate,
        channels=1,
        sample_width=2,
        event_type="VOICE_DETECTED",
        metadata=None,
    ):
        return self.evidence_store.capture_audio(
            pcm=pcm,
            sample_rate=sample_rate,
            channels=channels,
            sample_width=sample_width,
            event_type=event_type,
            metadata=metadata,
        )

    def update_context(
        self,
        *args,
        **kwargs,
    ):
        update_context = getattr(
            self.evidence_store,
            "update_context",
            None,
        )

        if callable(update_context):
            return update_context(
                *args,
                **kwargs,
            )

        return None

    def close(
        self,
    ):
        if self.closed:
            return True

        self.closed = True

        close = getattr(
            self.evidence_store,
            "close",
            None,
        )

        if callable(close):
            close()

        return True


class VoiceIncidentEvidenceRecorder:
    """
    Records one complete voice incident without keeping an unlimited PCM
    recording in RAM.

    Small recordings stay in memory. Longer incidents automatically spill to a
    temporary file through SpooledTemporaryFile and are converted to the final
    WAV evidence only when the incident ends.
    """

    def __init__(
        self,
        pre_roll_seconds=VOICE_EVIDENCE_PRE_ROLL_SECONDS,
        spool_memory_limit_bytes=VOICE_EVIDENCE_SPOOL_MEMORY_BYTES,
    ):
        self.pre_roll_seconds = max(
            0.0,
            float(pre_roll_seconds),
        )

        self.spool_memory_limit_bytes = max(
            1024 * 1024,
            int(spool_memory_limit_bytes),
        )

        self._lock = threading.RLock()
        self._pre_roll = deque()
        self._pre_roll_duration = 0.0

        self._active = False
        self._sample_rate = None
        self._sample_width = 2
        self._channels = 1
        self._spool = None
        self._bytes_written = 0
        self._sample_rate_change_detected = False

    def _frame_duration(
        self,
        pcm_bytes,
        sample_rate,
    ):
        try:
            sample_rate = int(sample_rate)
        except (
            TypeError,
            ValueError,
        ):
            return 0.0

        if sample_rate <= 0:
            return 0.0

        bytes_per_frame = self._sample_width * self._channels

        if bytes_per_frame <= 0:
            return 0.0

        frame_count = len(pcm_bytes) // bytes_per_frame

        return frame_count / float(sample_rate)

    def _trim_pre_roll(
        self,
    ):
        while self._pre_roll and self._pre_roll_duration > self.pre_roll_seconds:
            old = self._pre_roll.popleft()

            self._pre_roll_duration = max(
                0.0,
                self._pre_roll_duration
                - float(
                    old.get(
                        "duration",
                        0.0,
                    )
                    or 0.0
                ),
            )

    def feed_pcm(
        self,
        pcm_bytes,
        sample_rate,
    ):
        if not pcm_bytes:
            return

        pcm_bytes = bytes(pcm_bytes)

        try:
            sample_rate = int(sample_rate)
        except (
            TypeError,
            ValueError,
        ):
            return

        if sample_rate <= 0:
            return

        duration = self._frame_duration(
            pcm_bytes,
            sample_rate,
        )

        if duration <= 0.0:
            return

        with self._lock:
            frame = {
                "pcm": pcm_bytes,
                "sample_rate": sample_rate,
                "duration": duration,
            }

            self._pre_roll.append(frame)

            self._pre_roll_duration += duration

            self._trim_pre_roll()

            if not self._active:
                return

            if self._sample_rate is None:
                self._sample_rate = sample_rate

            if sample_rate != self._sample_rate:
                self._sample_rate_change_detected = True
                return

            if self._spool is None:
                return

            self._spool.write(pcm_bytes)

            self._bytes_written += len(pcm_bytes)

    def start(
        self,
    ):
        with self._lock:
            if self._active:
                return True

            selected_rate = None

            for frame in reversed(self._pre_roll):
                frame_rate = frame.get("sample_rate")

                if frame_rate:
                    selected_rate = int(frame_rate)
                    break

            if not selected_rate:
                return False

            self._spool = tempfile.SpooledTemporaryFile(
                max_size=self.spool_memory_limit_bytes,
                mode="w+b",
            )

            self._sample_rate = selected_rate
            self._bytes_written = 0
            self._sample_rate_change_detected = False

            for frame in self._pre_roll:
                if (
                    int(
                        frame.get(
                            "sample_rate",
                            0,
                        )
                        or 0
                    )
                    != self._sample_rate
                ):
                    continue

                pcm = frame.get("pcm")

                if not pcm:
                    continue

                self._spool.write(pcm)

                self._bytes_written += len(pcm)

            self._active = True

            print(
                "[AUDIO][EVIDENCE RECORDING STARTED] "
                f"sample_rate={self._sample_rate} "
                f"| pre_roll={self.pre_roll_seconds:.2f}s"
            )

            return True

    def stop(
        self,
    ):
        with self._lock:
            if not self._active:
                return None

            spool = self._spool
            sample_rate = self._sample_rate
            bytes_written = self._bytes_written
            sample_rate_change_detected = self._sample_rate_change_detected

            self._active = False
            self._spool = None
            self._sample_rate = None
            self._bytes_written = 0
            self._sample_rate_change_detected = False

        if spool is None:
            return None

        try:
            spool.seek(0)

            pcm = spool.read()

        finally:
            try:
                spool.close()
            except Exception:
                pass

        if not pcm:
            return None

        bytes_per_frame = self._channels * self._sample_width

        frame_count = len(pcm) // bytes_per_frame

        duration_seconds = frame_count / float(sample_rate) if sample_rate else 0.0

        return {
            "pcm": pcm,
            "sample_rate": sample_rate,
            "channels": self._channels,
            "sample_width": self._sample_width,
            "duration_seconds": round(
                duration_seconds,
                3,
            ),
            "bytes_written": bytes_written,
            "sample_rate_change_detected": (sample_rate_change_detected),
        }

    def discard(
        self,
    ):
        with self._lock:
            spool = self._spool

            self._active = False
            self._spool = None
            self._sample_rate = None
            self._bytes_written = 0
            self._sample_rate_change_detected = False

        if spool is not None:
            try:
                spool.close()
            except Exception:
                pass

    def close(
        self,
    ):
        self.discard()


class IncidentRecordingAudioMonitor(AudioMonitor):
    """
    Backward-compatible AudioMonitor subclass for this evidence test.

    AudioMonitor continues to own device management, VAD processing, event
    emission and its normal rolling evidence buffer. This subclass only mirrors
    the original high-quality PCM frames into VoiceIncidentEvidenceRecorder.
    """

    def __init__(
        self,
        *args,
        voice_incident_recorder=None,
        **kwargs,
    ):
        self.voice_incident_recorder = voice_incident_recorder

        super().__init__(
            *args,
            **kwargs,
        )

    def _append_audio_buffer(
        self,
        pcm_bytes,
        sample_rate,
    ):
        super()._append_audio_buffer(
            pcm_bytes,
            sample_rate,
        )

        recorder = self.voice_incident_recorder

        if recorder is not None:
            recorder.feed_pcm(
                pcm_bytes,
                sample_rate,
            )


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

    active_microphone = (
        audio_status.get("active_microphone")
        if isinstance(
            audio_status,
            dict,
        )
        else None
    )

    microphone_name = (
        active_microphone.get("name")
        if isinstance(
            active_microphone,
            dict,
        )
        else None
    )

    if not microphone_name:

        microphone_name = "Unavailable"

    microphone_name = str(microphone_name)

    if len(microphone_name) > 34:

        microphone_name = microphone_name[:31] + "..."

    microphone_available = bool(
        audio_status.get(
            "microphone_available",
            False,
        )
    )

    calibrating = bool(
        audio_status.get(
            "calibrating",
            False,
        )
    )

    voice_active = bool(
        audio_status.get(
            "voice_active",
            False,
        )
    )

    voice_confirmed = bool(
        audio_status.get(
            "voice_confirmed",
            False,
        )
    )

    voice_duration = float(
        audio_status.get(
            "voice_duration_seconds",
            0.0,
        )
        or 0.0
    )

    whisper_candidate = bool(
        audio_status.get(
            "whisper_candidate",
            False,
        )
    )

    detection_source = audio_status.get("detection_source") or "-"

    dbfs = float(
        audio_status.get(
            "dbfs",
            -100.0,
        )
        or -100.0
    )

    noise_floor = float(
        audio_status.get(
            "noise_floor_dbfs",
            -60.0,
        )
        or -60.0
    )

    evidence_captured = bool(
        voice_anomaly_result.get(
            "captured",
            False,
        )
        if isinstance(
            voice_anomaly_result,
            dict,
        )
        else False
    )

    incident_active = bool(
        voice_anomaly_result.get(
            "_voice_incident_active",
            False,
        )
        if isinstance(
            voice_anomaly_result,
            dict,
        )
        else False
    )

    incident_confirmed = bool(
        voice_anomaly_result.get(
            "confirmed",
            False,
        )
        if isinstance(
            voice_anomaly_result,
            dict,
        )
        else False
    )

    incident_duration = float(
        voice_anomaly_result.get(
            "incident_duration_seconds",
            0.0,
        )
        or 0.0
    )

    incident_silence = float(
        voice_anomaly_result.get(
            "silence_duration_seconds",
            0.0,
        )
        or 0.0
    )

    if calibrating:

        voice_text = "CALIBRATING"

        voice_color = (
            0,
            255,
            255,
        )

    elif incident_active and incident_confirmed:

        if incident_silence > 0.0:
            voice_text = "VIOLATION / HOLD"
        else:
            voice_text = "VIOLATION"

        voice_color = (
            0,
            0,
            255,
        )

    elif evidence_captured:

        voice_text = "VIOLATION"

        voice_color = (
            0,
            0,
            255,
        )

    elif voice_confirmed:

        voice_text = "CONFIRMED"

        voice_color = (
            0,
            165,
            255,
        )

    elif voice_active:

        voice_text = "ACTIVE"

        voice_color = (
            0,
            255,
            255,
        )

    else:

        voice_text = "QUIET"

        voice_color = (
            0,
            255,
            0,
        )

    microphone_color = (
        (
            0,
            255,
            0,
        )
        if microphone_available
        else (
            0,
            0,
            255,
        )
    )

    rows = [
        (
            "AUDIO STATUS",
            y1 + 20,
            0.46,
            (
                255,
                255,
                255,
            ),
            2,
        ),
        (
            f"Mic: {microphone_name}",
            y1 + 42,
            0.32,
            microphone_color,
            1,
        ),
        (
            f"Voice: {voice_text}",
            y1 + 64,
            0.36,
            voice_color,
            1,
        ),
        (
            (
                "Incident: "
                f"{incident_duration:.2f}s "
                f"| silence={incident_silence:.2f}s"
                if incident_active
                else f"Voice time: {voice_duration:.2f}s"
            ),
            y1 + 86,
            0.34,
            (
                255,
                255,
                255,
            ),
            1,
        ),
        (
            "Source: " f"{detection_source} " "| whisper=" f"{whisper_candidate}",
            y1 + 108,
            0.31,
            (
                255,
                255,
                255,
            ),
            1,
        ),
        (
            "Level: " f"{dbfs:.1f} dBFS " "| noise=" f"{noise_floor:.1f}",
            y1 + 130,
            0.30,
            (
                255,
                255,
                255,
            ),
            1,
        ),
    ]

    for (
        text,
        y,
        scale,
        color,
        thickness,
    ) in rows:

        cv2.putText(
            frame,
            text,
            (
                x1 + 10,
                y,
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            scale,
            color,
            thickness,
            cv2.LINE_AA,
        )


def empty_voice_anomaly_result():

    return {
        "event_type": "VOICE_DETECTED",
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
        "silence_duration_seconds": 0.0,
        "short_gap_grace_seconds": VOICE_SHORT_GAP_GRACE_SECONDS,
        "incident_end_silence_seconds": VOICE_INCIDENT_END_SILENCE_SECONDS,
        "_voice_incident_active": False,
        "_voice_incident_started_at": None,
        "_voice_last_activity_at": None,
        "_voice_silence_started_at": None,
        "_voice_incident_captured": False,
        "_voice_incident_number": 0,
    }


def configure_voice_anomaly_for_test(
    anomaly_manager,
):
    """
    Configure only the VOICE_DETECTED rule for this preview test.

    The detector itself still has to classify the input as human voice. The
    anomaly layer then confirms that first valid speech event immediately,
    regardless of how short the utterance was. Existing cooldown is preserved.
    """
    rules = getattr(
        anomaly_manager,
        "rules",
        None,
    )

    if not isinstance(
        rules,
        dict,
    ):
        print(
            "[AUDIO] Warning: AnomalyManager rules are not exposed; "
            "instant voice confirmation could not be configured."
        )
        return False

    voice_rule = rules.get("VOICE_DETECTED")

    if not isinstance(
        voice_rule,
        dict,
    ):
        print(
            "[AUDIO] Warning: VOICE_DETECTED anomaly rule is unavailable; "
            "instant voice confirmation could not be configured."
        )
        return False

    # No minimum anomaly duration once the VAD has already declared that
    # human speech exists. Keep the configured evidence cooldown untouched.
    voice_rule["duration"] = 0.0
    voice_rule["minimum_audio_duration"] = 0.0
    voice_rule["recovery_grace"] = 0.0
    voice_rule["capture_once_per_incident"] = True

    print(
        "[AUDIO] VOICE_DETECTED configured for immediate confirmation "
        f"| trigger={VOICE_TRIGGER_SECONDS:.2f}s "
        f"| short_gap_grace={VOICE_SHORT_GAP_GRACE_SECONDS:.1f}s "
        f"| incident_end_silence={VOICE_INCIDENT_END_SILENCE_SECONDS:.1f}s"
    )

    return True


def _voice_incident_elapsed(
    result,
    now,
):
    started_at = result.get("_voice_incident_started_at")

    if started_at is None:
        return 0.0

    try:
        return max(
            0.0,
            float(now) - float(started_at),
        )
    except (
        TypeError,
        ValueError,
    ):
        return 0.0


def _voice_silence_elapsed(
    result,
    now,
):
    silence_started_at = result.get("_voice_silence_started_at")

    if silence_started_at is None:
        return 0.0

    try:
        return max(
            0.0,
            float(now) - float(silence_started_at),
        )
    except (
        TypeError,
        ValueError,
    ):
        return 0.0


def _keep_voice_incident_visible(
    result,
    now,
):
    if not result.get(
        "_voice_incident_active",
        False,
    ):
        return result

    result["active"] = True
    result["confirmed"] = True
    result["captured"] = bool(
        result.get(
            "_voice_incident_captured",
            False,
        )
    )
    result["incident_duration_seconds"] = _voice_incident_elapsed(
        result,
        now,
    )
    result["silence_duration_seconds"] = _voice_silence_elapsed(
        result,
        now,
    )
    result["required_duration"] = VOICE_TRIGGER_SECONDS
    result["short_gap_grace_seconds"] = VOICE_SHORT_GAP_GRACE_SECONDS
    result["incident_end_silence_seconds"] = VOICE_INCIDENT_END_SILENCE_SECONDS

    return result


def _finish_voice_incident_if_silent(
    result,
    anomaly_manager,
    now,
    voice_incident_recorder=None,
    evidence_store=None,
):
    if not result.get(
        "_voice_incident_active",
        False,
    ):
        return result

    silence_started_at = result.get("_voice_silence_started_at")

    if silence_started_at is None:
        return _keep_voice_incident_visible(
            result,
            now,
        )

    silence_elapsed = _voice_silence_elapsed(
        result,
        now,
    )

    if silence_elapsed < VOICE_INCIDENT_END_SILENCE_SECONDS:
        return _keep_voice_incident_visible(
            result,
            now,
        )

    incident_duration = _voice_incident_elapsed(
        result,
        now,
    )

    incident_number = result.get(
        "_voice_incident_number",
        0,
    )

    completed_evidence = None
    recorded_audio = None

    if voice_incident_recorder is not None:
        recorded_audio = voice_incident_recorder.stop()

    should_persist_audio = bool(
        result.get(
            "_voice_incident_captured",
            False,
        )
    )

    if (
        should_persist_audio
        and isinstance(
            recorded_audio,
            dict,
        )
        and recorded_audio.get("pcm")
        and evidence_store is not None
    ):
        persist_audio = getattr(
            evidence_store,
            "persist_audio",
            None,
        )

        if callable(persist_audio):
            evidence_metadata = {
                "incident_number": incident_number,
                "incident_duration_seconds": round(
                    incident_duration,
                    3,
                ),
                "continuous_silence_seconds": round(
                    silence_elapsed,
                    3,
                ),
                "recorded_audio_duration_seconds": (
                    recorded_audio.get("duration_seconds")
                ),
                "recording_started_on_first_voice": True,
                "voice_incident_end_silence_seconds": (
                    VOICE_INCIDENT_END_SILENCE_SECONDS
                ),
                "voice_evidence_pre_roll_seconds": (VOICE_EVIDENCE_PRE_ROLL_SECONDS),
                "sample_rate_change_detected": bool(
                    recorded_audio.get(
                        "sample_rate_change_detected",
                        False,
                    )
                ),
            }

            try:
                completed_evidence = persist_audio(
                    pcm=recorded_audio["pcm"],
                    sample_rate=recorded_audio["sample_rate"],
                    channels=recorded_audio.get(
                        "channels",
                        1,
                    ),
                    sample_width=recorded_audio.get(
                        "sample_width",
                        2,
                    ),
                    event_type="VOICE_DETECTED",
                    metadata=evidence_metadata,
                )

                if completed_evidence:
                    print(
                        "[AUDIO][VOICE EVIDENCE SAVED] "
                        f"incident={incident_number} "
                        f"| duration="
                        f"{float(recorded_audio.get('duration_seconds', 0.0)):.2f}s "
                        f"| path="
                        f"{completed_evidence.get('audio_path')}"
                    )

            except Exception as error:
                print(
                    "[AUDIO][VOICE EVIDENCE SAVE ERROR] "
                    f"incident={incident_number} "
                    f"| error={error}"
                )

    elif isinstance(
        recorded_audio,
        dict,
    ) and recorded_audio.get("pcm"):
        print(
            "[AUDIO][VOICE EVIDENCE NOT PERSISTED] "
            f"incident={incident_number} "
            "| anomaly evidence cooldown/capture-once did not arm "
            "a new evidence capture."
        )

    ended_result = anomaly_manager.update_audio(
        event_type="VOICE_DETECTED",
        active=False,
        audio_evidence=None,
        metadata={
            "incident_number": incident_number,
            "incident_duration_seconds": round(
                incident_duration,
                3,
            ),
            "continuous_silence_seconds": round(
                silence_elapsed,
                3,
            ),
            "ended_by_voice_incident_hold": True,
        },
    )

    if not isinstance(
        ended_result,
        dict,
    ):
        ended_result = empty_voice_anomaly_result()

    ended_result["incident_duration_seconds"] = incident_duration
    ended_result["silence_duration_seconds"] = silence_elapsed
    ended_result["required_duration"] = VOICE_TRIGGER_SECONDS
    ended_result["short_gap_grace_seconds"] = VOICE_SHORT_GAP_GRACE_SECONDS
    ended_result["incident_end_silence_seconds"] = VOICE_INCIDENT_END_SILENCE_SECONDS
    ended_result["completed_audio_evidence"] = completed_evidence
    ended_result["_voice_incident_active"] = False
    ended_result["_voice_incident_started_at"] = None
    ended_result["_voice_last_activity_at"] = None
    ended_result["_voice_silence_started_at"] = None
    ended_result["_voice_incident_captured"] = False
    ended_result["_voice_incident_number"] = incident_number

    print(
        "[AUDIO][VOICE INCIDENT ENDED] "
        f"incident={incident_number} "
        f"duration={incident_duration:.2f}s "
        f"continuous_silence={silence_elapsed:.2f}s"
    )

    return ended_result


def process_audio_events(
    audio_event_queue,
    anomaly_manager,
    current_result,
    voice_incident_recorder=None,
    evidence_store=None,
):
    """
    Convert raw AudioMonitor speech events into one held VOICE_DETECTED incident.

    Behavior:
    - First VAD-confirmed human speech starts and confirms the violation.
    - No multi-second anomaly confirmation wait exists in test.py.
    - VOICE_ACTIVITY_ENDED does NOT immediately end the anomaly.
    - Speech resuming during the hold continues the same incident.
    - Only 5 seconds of continuous no-voice time closes the incident.
    - High-quality PCM recording starts with the first confirmed speech.
    - The complete incident is saved as one WAV after 5 seconds of silence.
    """
    result = dict(current_result or empty_voice_anomaly_result())

    now = time.monotonic()

    # If the previous detector-level speech segment ended long enough ago,
    # close the held anomaly before consuming a possible new speech segment.
    result = _finish_voice_incident_if_silent(
        result=result,
        anomaly_manager=anomaly_manager,
        now=now,
        voice_incident_recorder=voice_incident_recorder,
        evidence_store=evidence_store,
    )

    while True:

        try:

            payload = audio_event_queue.get_nowait()

        except queue.Empty:

            break

        if not isinstance(
            payload,
            dict,
        ):

            continue

        event_type = (
            str(
                payload.get(
                    "event_type",
                    "",
                )
            )
            .upper()
            .strip()
        )

        now = time.monotonic()

        if event_type == "VOICE_DETECTED":

            was_incident_active = bool(
                result.get(
                    "_voice_incident_active",
                    False,
                )
            )

            previous_incident_started_at = result.get("_voice_incident_started_at")

            previous_incident_number = int(
                result.get(
                    "_voice_incident_number",
                    0,
                )
                or 0
            )

            previous_incident_captured = bool(
                result.get(
                    "_voice_incident_captured",
                    False,
                )
            )

            if not was_incident_active:
                previous_incident_number += 1
                previous_incident_started_at = now
                previous_incident_captured = False

                if voice_incident_recorder is not None:
                    voice_incident_recorder.start()

                print(
                    "[AUDIO][VOICE INCIDENT STARTED] "
                    f"incident={previous_incident_number}"
                )

            audio_evidence = payload.get("evidence_audio")

            metadata = {
                key: value
                for (
                    key,
                    value,
                ) in payload.items()
                if key
                not in {
                    "event_type",
                    "evidence_audio",
                }
            }

            metadata.update(
                {
                    "incident_number": previous_incident_number,
                    "instant_confirmation": True,
                    "incident_hold_silence_seconds": (
                        VOICE_INCIDENT_END_SILENCE_SECONDS
                    ),
                    "continuous_audio_evidence": True,
                    "evidence_write_deferred_until_incident_end": True,
                }
            )

            manager_result = anomaly_manager.update_audio(
                event_type="VOICE_DETECTED",
                active=True,
                audio_evidence=audio_evidence,
                metadata=metadata,
            )

            if not isinstance(
                manager_result,
                dict,
            ):
                manager_result = empty_voice_anomaly_result()

            manager_result["_voice_incident_active"] = True
            manager_result["_voice_incident_started_at"] = previous_incident_started_at
            manager_result["_voice_last_activity_at"] = now
            manager_result["_voice_silence_started_at"] = None
            manager_result["_voice_incident_number"] = previous_incident_number
            manager_result["_voice_incident_captured"] = bool(
                previous_incident_captured
                or manager_result.get(
                    "captured",
                    False,
                )
            )

            # Once the real VAD has declared human speech, this preview's
            # anomaly is confirmed immediately. Cooldown may still suppress a
            # second evidence capture, but it does not un-confirm the incident.
            manager_result["active"] = True
            manager_result["confirmed"] = True
            manager_result["captured"] = bool(
                manager_result["_voice_incident_captured"]
            )
            manager_result["required_duration"] = VOICE_TRIGGER_SECONDS
            manager_result["incident_duration_seconds"] = _voice_incident_elapsed(
                manager_result,
                now,
            )
            manager_result["silence_duration_seconds"] = 0.0
            manager_result["short_gap_grace_seconds"] = VOICE_SHORT_GAP_GRACE_SECONDS
            manager_result["incident_end_silence_seconds"] = (
                VOICE_INCIDENT_END_SILENCE_SECONDS
            )

            result = manager_result

            if result.get(
                "captured",
                False,
            ):

                print(
                    "[AUDIO][VOICE VIOLATION CONFIRMED] "
                    f"incident={previous_incident_number} "
                    "| continuous audio evidence recording is active."
                )

            else:
                print(
                    "[AUDIO][VOICE VIOLATION CONFIRMED] "
                    f"incident={previous_incident_number} "
                    "No new evidence marker due to existing incident/cooldown."
                )

            continue

        if event_type == "VOICE_ACTIVITY_ENDED":

            if result.get(
                "_voice_incident_active",
                False,
            ):
                if result.get("_voice_silence_started_at") is None:
                    result["_voice_silence_started_at"] = now

                    print(
                        "[AUDIO][VOICE GAP] "
                        "Detector-level speech stopped; keeping the violation "
                        f"active for up to {VOICE_INCIDENT_END_SILENCE_SECONDS:.1f}s "
                        "while waiting for speech to resume."
                    )

                result = _keep_voice_incident_visible(
                    result,
                    now,
                )

            # Deliberately DO NOT call AnomalyManager(active=False) here.
            # That happens only after the full continuous-silence hold expires.
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
                key: value
                for (
                    key,
                    value,
                ) in payload.items()
                if (key != "evidence_audio")
            }

            print(
                f"[AUDIO][{event_type}]",
                safe_payload,
            )

    now = time.monotonic()

    result = _finish_voice_incident_if_silent(
        result=result,
        anomaly_manager=anomaly_manager,
        now=now,
        voice_incident_recorder=voice_incident_recorder,
        evidence_store=evidence_store,
    )

    return result


def print_instructions():

    print()

    print("=" * 80)

    print("SKOLARIQ PRODUCTION PROCTORING ENGINE PREVIEW TEST")

    print("=" * 80)

    print()

    print(
        "This test uses the same camera, microphone, detectors, "
        "anomaly manager and evidence pipeline intended for the native "
        "proctor application."
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

    print("  Second person        -> MULTIPLE_FACES / EXTRA_PERSON")

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

    print("  Valid human speech   -> VOICE_DETECTED confirmed immediately")

    print("  Quiet whisper        -> whisper-sensitive detection")

    print("  Brief speech gaps    -> same violation + recording stay active")

    print("  5 sec full silence   -> incident ends and one WAV is saved")

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

    real_evidence_store = None

    voice_incident_recorder = None

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

        print("[YUNET] Loading face detector...")

        face_detector = YuNetFaceDetector()

        print("[YUNET] Face detector loaded successfully.")

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

        print("[EVIDENCE] Initializing evidence store...")

        real_evidence_store = EvidenceStore(
            student_id="local_test",
            exam_id="local_test",
            schedule_id="local_test",
            session_id="local_test",
        )

        evidence_store = DeferredAudioEvidenceStore(real_evidence_store)

        print(
            "[EVIDENCE] Evidence store initialized. "
            "Image evidence saves immediately; voice WAV saving is "
            "deferred until the complete voice incident ends."
        )

        print("[ANOMALY] Initializing anomaly manager...")

        anomaly_manager = AnomalyManager(evidence_store=evidence_store)

        configure_voice_anomaly_for_test(anomaly_manager)

        print("[ANOMALY] Anomaly manager initialized.")

        voice_incident_recorder = VoiceIncidentEvidenceRecorder(
            pre_roll_seconds=VOICE_EVIDENCE_PRE_ROLL_SECONDS,
            spool_memory_limit_bytes=VOICE_EVIDENCE_SPOOL_MEMORY_BYTES,
        )

        print("[AUDIO] Starting audio monitor...")

        audio_monitor = IncidentRecordingAudioMonitor(
            device_manager=audio_device_manager,
            voice_detector=voice_activity_detector,
            event_callback=audio_event_queue.put,
            device_poll_interval=2.0,
            evidence_buffer_seconds=8.0,
            reconnect_interval=2.0,
            voice_incident_recorder=voice_incident_recorder,
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
                voice_incident_recorder=voice_incident_recorder,
                evidence_store=evidence_store,
            )

            try:

                faces = face_detector.detect(frame)

                if faces is None:

                    faces = []

            except Exception as error:

                print(
                    "[YUNET] Detection error:",
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

        if voice_incident_recorder is not None:

            try:

                voice_incident_recorder.close()

            except Exception as error:

                print(
                    "[AUDIO] Voice incident recorder cleanup error:",
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
                    "[YUNET] Cleanup error:",
                    error,
                )

        try:

            cv2.destroyAllWindows()

        except Exception:

            pass

        print("[TEST] Finished.")


if __name__ == "__main__":

    main()
