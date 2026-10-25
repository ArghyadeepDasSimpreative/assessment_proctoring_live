# import argparse
# import os
# import sys
# import time
# import math
# import queue
# import tempfile
# import threading
# import webbrowser
# import subprocess

# try:
#     import psutil
# except Exception:
#     psutil = None

# from collections import deque
# from datetime import datetime, timezone

# from urllib.parse import (
#     parse_qs,
#     quote,
#     urlparse,
# )

# import cv2
# import sounddevice as sd

# from src.auth import (
#     LaunchTokenError,
#     validate_launch_token,
# )

# from src.config import settings

# from src.core.kiosk_manager import (
#     KioskManager,
# )

# from src.core.keyboard_lockdown import (
#     KeyboardLockdownManager,
# )

# try:
#     from src.core.process_monitor import (
#         ProcessMonitor,
#     )

#     PROCESS_MONITOR_IMPORT_ERROR = None

# except Exception as error:
#     ProcessMonitor = None

#     PROCESS_MONITOR_IMPORT_ERROR = error

# from src.socket.proctor_socket import (
#     ProctorSocketClient,
# )

# from src.vision.face_detector_mediapipe import (
#     MediaPipeFaceDetector,
# )

# from src.vision.face_landmarker import (
#     FaceLandmarker,
# )

# from src.vision.gaze_tracker import (
#     GazeTracker,
# )

# from src.vision.head_tracker import (
#     HeadTracker,
# )

# from src.vision.pose_landmarker import (
#     PoseLandmarker,
# )

# from src.vision.object_detector_yolo26 import (
#     YOLO26ObjectDetector,
# )

# from src.core.posture_monitor import (
#     PostureMonitor,
# )

# from src.evidence.evidence_store import (
#     EvidenceStore,
# )

# from src.core.anomaly_manager import (
#     AnomalyManager,
# )

# from src.core.audio_device_manager import (
#     AudioDeviceManager,
# )

# from src.core.voice_activity_detector import (
#     VoiceActivityDetector,
# )

# from src.core.audio_monitor import (
#     AudioMonitor,
# )

# from src.api.proctoring_api import (
#     ProctoringAPI,
# )

# PROTOCOL_SCHEME = "skolariq-proctor"

# LAUNCH_ACTION = "launch"

# DEFAULT_ASSESSMENT_WEB_BASE_URL = "http://localhost:5173"

# CAMERA_INDEX = 0

# CAMERA_WIDTH = 640

# CAMERA_HEIGHT = 480

# MIC_CHANNELS = 1

# exam_completed_flag = False

# FINAL_EVIDENCE_RETRY_DELAY_SECONDS = 2.0

# PREVIOUS_PROCTOR_INSTANCE_SHUTDOWN_TIMEOUT_SECONDS = 4.0

# # Voice detection/incident behavior.
# # Keep production behavior aligned with the validated test_v2 flow:
# # - human speech starts a logical incident, but is not immediately a violation;
# # - only cumulative HUMAN-SPEECH time counts toward confirmation;
# # - silence/pause time contributes zero toward the threshold;
# # - speech resuming before 5 seconds of continuous silence continues the same
# #   logical incident and keeps the previous cumulative speech total;
# # - VOICE_DETECTED is confirmed only after 1.5 seconds cumulative speech;
# # - the logical incident ends only after 5 seconds continuous silence.
# VOICE_TRIGGER_SECONDS = 1.5
# VOICE_SMOOTHING_WINDOW_SECONDS = 0.06
# VOICE_DETECTOR_SILENCE_RESET_SECONDS = 5.0
# # Kept for backward compatibility with existing status/metadata consumers.
# VOICE_SHORT_GAP_GRACE_SECONDS = 5.0
# VOICE_INCIDENT_END_SILENCE_SECONDS = 5.0
# VOICE_EVIDENCE_PRE_ROLL_SECONDS = 0.75

# # Keep short incidents in RAM, then automatically spill longer evidence to a
# # temporary file. This protects low-memory laptops while preserving the full
# # high-quality PCM stream for the final WAV.
# VOICE_EVIDENCE_SPOOL_MEMORY_BYTES = 4 * 1024 * 1024


# class DeferredAudioEvidenceStore:
#     """
#     Backward-compatible EvidenceStore adapter for production voice incidents.

#     Image evidence is saved immediately through the existing EvidenceStore.

#     For VOICE_DETECTED, AnomalyManager receives an immediate lightweight
#     evidence marker. That marker lets the existing AnomalyManager/socket path
#     confirm and broadcast the violation immediately without waiting for the
#     complete voice incident to finish.

#     The actual WAV is written only when the held voice incident closes.
#     """

#     def __init__(
#         self,
#         evidence_store,
#     ):
#         if evidence_store is None:
#             raise ValueError("DeferredAudioEvidenceStore requires an EvidenceStore.")

#         self.evidence_store = evidence_store
#         self.closed = False

#     def __getattr__(
#         self,
#         name,
#     ):
#         return getattr(
#             self.evidence_store,
#             name,
#         )

#     def capture(
#         self,
#         frame,
#         event_type,
#         metadata=None,
#         *args,
#         **kwargs,
#     ):
#         return self.evidence_store.capture(
#             frame=frame,
#             event_type=event_type,
#             metadata=metadata,
#         )

#     def capture_audio(
#         self,
#         pcm,
#         sample_rate,
#         channels=1,
#         sample_width=2,
#         event_type="VOICE_DETECTED",
#         metadata=None,
#         *args,
#         **kwargs,
#     ):
#         captured_at = datetime.now(timezone.utc).isoformat()

#         return {
#             "event_type": str(event_type or "").upper().strip(),
#             "evidence_type": "audio",
#             "file_path": None,
#             "audio_path": None,
#             "metadata_path": None,
#             "client_captured_at": captured_at,
#             "metadata": dict(metadata or {}),
#             "event": {
#                 "event_type": str(event_type or "").upper().strip(),
#                 "captured_at": captured_at,
#                 "audio_capture_deferred": True,
#             },
#             "audio_capture_deferred": True,
#         }

#     def persist_audio(
#         self,
#         pcm,
#         sample_rate,
#         channels=1,
#         sample_width=2,
#         event_type="VOICE_DETECTED",
#         metadata=None,
#     ):
#         return self.evidence_store.capture_audio(
#             pcm=pcm,
#             sample_rate=sample_rate,
#             channels=channels,
#             sample_width=sample_width,
#             event_type=event_type,
#             metadata=metadata,
#         )

#     def update_context(
#         self,
#         *args,
#         **kwargs,
#     ):
#         update_context = getattr(
#             self.evidence_store,
#             "update_context",
#             None,
#         )

#         if callable(update_context):
#             return update_context(
#                 *args,
#                 **kwargs,
#             )

#         return None

#     def close(
#         self,
#     ):
#         if self.closed:
#             return True

#         self.closed = True

#         close = getattr(
#             self.evidence_store,
#             "close",
#             None,
#         )

#         if callable(close):
#             close()

#         return True


# class VoiceIncidentEvidenceRecorder:
#     """
#     Preserve the complete original PCM stream for one voice incident.

#     A short pre-roll is continuously retained so the beginning of the first
#     utterance is not clipped while the VOICE_DETECTED event travels through
#     the queue. Once an incident starts, every original PCM frame is appended,
#     including natural silence between speech segments.

#     SpooledTemporaryFile keeps short evidence in memory and automatically
#     spills longer evidence to disk after the configured memory threshold.
#     """

#     def __init__(
#         self,
#         pre_roll_seconds=VOICE_EVIDENCE_PRE_ROLL_SECONDS,
#         spool_memory_limit_bytes=VOICE_EVIDENCE_SPOOL_MEMORY_BYTES,
#     ):
#         self.pre_roll_seconds = max(
#             0.0,
#             float(pre_roll_seconds),
#         )

#         self.spool_memory_limit_bytes = max(
#             1024 * 1024,
#             int(spool_memory_limit_bytes),
#         )

#         self._lock = threading.RLock()

#         self._pre_roll = deque()
#         self._pre_roll_duration = 0.0

#         self._active = False
#         self._sample_rate = None
#         self._sample_width = 2
#         self._channels = 1
#         self._spool = None
#         self._bytes_written = 0
#         self._sample_rate_change_detected = False

#     def _frame_duration(
#         self,
#         pcm_bytes,
#         sample_rate,
#     ):
#         try:
#             sample_rate = int(sample_rate)

#         except (
#             TypeError,
#             ValueError,
#         ):
#             return 0.0

#         if sample_rate <= 0:
#             return 0.0

#         bytes_per_frame = self._sample_width * self._channels

#         if bytes_per_frame <= 0:
#             return 0.0

#         frame_count = len(pcm_bytes) // bytes_per_frame

#         return frame_count / float(sample_rate)

#     def _trim_pre_roll(
#         self,
#     ):
#         while self._pre_roll and self._pre_roll_duration > self.pre_roll_seconds:
#             old = self._pre_roll.popleft()

#             self._pre_roll_duration = max(
#                 0.0,
#                 self._pre_roll_duration
#                 - float(
#                     old.get(
#                         "duration",
#                         0.0,
#                     )
#                     or 0.0
#                 ),
#             )

#     def feed_pcm(
#         self,
#         pcm_bytes,
#         sample_rate,
#     ):
#         if not pcm_bytes:
#             return

#         pcm_bytes = bytes(pcm_bytes)

#         try:
#             sample_rate = int(sample_rate)

#         except (
#             TypeError,
#             ValueError,
#         ):
#             return

#         if sample_rate <= 0:
#             return

#         duration = self._frame_duration(
#             pcm_bytes,
#             sample_rate,
#         )

#         if duration <= 0.0:
#             return

#         with self._lock:
#             frame = {
#                 "pcm": pcm_bytes,
#                 "sample_rate": sample_rate,
#                 "duration": duration,
#             }

#             self._pre_roll.append(frame)

#             self._pre_roll_duration += duration

#             self._trim_pre_roll()

#             if not self._active:
#                 return

#             if self._sample_rate is None:
#                 self._sample_rate = sample_rate

#             if sample_rate != self._sample_rate:
#                 self._sample_rate_change_detected = True
#                 return

#             if self._spool is None:
#                 return

#             self._spool.write(pcm_bytes)

#             self._bytes_written += len(pcm_bytes)

#     def start(
#         self,
#     ):
#         with self._lock:
#             if self._active:
#                 return True

#             selected_rate = None

#             for frame in reversed(self._pre_roll):
#                 frame_rate = frame.get("sample_rate")

#                 if frame_rate:
#                     selected_rate = int(frame_rate)
#                     break

#             if not selected_rate:
#                 return False

#             self._spool = tempfile.SpooledTemporaryFile(
#                 max_size=self.spool_memory_limit_bytes,
#                 mode="w+b",
#             )

#             self._sample_rate = selected_rate
#             self._bytes_written = 0
#             self._sample_rate_change_detected = False

#             for frame in self._pre_roll:
#                 if (
#                     int(
#                         frame.get(
#                             "sample_rate",
#                             0,
#                         )
#                         or 0
#                     )
#                     != self._sample_rate
#                 ):
#                     continue

#                 pcm = frame.get("pcm")

#                 if not pcm:
#                     continue

#                 self._spool.write(pcm)

#                 self._bytes_written += len(pcm)

#             self._active = True

#             print(
#                 "[AUDIO][EVIDENCE RECORDING STARTED] "
#                 f"sample_rate={self._sample_rate} "
#                 f"| pre_roll={self.pre_roll_seconds:.2f}s"
#             )

#             return True

#     def stop(
#         self,
#     ):
#         with self._lock:
#             if not self._active:
#                 return None

#             spool = self._spool
#             sample_rate = self._sample_rate
#             bytes_written = self._bytes_written
#             sample_rate_change_detected = self._sample_rate_change_detected

#             self._active = False
#             self._spool = None
#             self._sample_rate = None
#             self._bytes_written = 0
#             self._sample_rate_change_detected = False

#         if spool is None:
#             return None

#         try:
#             spool.seek(0)

#             pcm = spool.read()

#         finally:
#             try:
#                 spool.close()

#             except Exception:
#                 pass

#         if not pcm:
#             return None

#         bytes_per_frame = self._channels * self._sample_width

#         frame_count = len(pcm) // bytes_per_frame

#         duration_seconds = frame_count / float(sample_rate) if sample_rate else 0.0

#         return {
#             "pcm": pcm,
#             "sample_rate": sample_rate,
#             "channels": self._channels,
#             "sample_width": self._sample_width,
#             "duration_seconds": round(
#                 duration_seconds,
#                 3,
#             ),
#             "bytes_written": bytes_written,
#             "sample_rate_change_detected": (sample_rate_change_detected),
#         }

#     def discard(
#         self,
#     ):
#         with self._lock:
#             spool = self._spool

#             self._active = False
#             self._spool = None
#             self._sample_rate = None
#             self._bytes_written = 0
#             self._sample_rate_change_detected = False

#         if spool is not None:
#             try:
#                 spool.close()

#             except Exception:
#                 pass

#     def close(
#         self,
#     ):
#         self.discard()


# class IncidentRecordingAudioMonitor(AudioMonitor):
#     """
#     Backward-compatible AudioMonitor subclass used by production main.py.

#     AudioMonitor keeps all existing microphone discovery, device switching,
#     VAD processing, high-quality evidence buffering and event emission.
#     This subclass only mirrors the original PCM stream into the full-incident
#     recorder. VAD/resampling changes inside AudioMonitor do not alter the PCM
#     that is retained here for evidence.
#     """

#     def __init__(
#         self,
#         *args,
#         voice_incident_recorder=None,
#         **kwargs,
#     ):
#         self.voice_incident_recorder = voice_incident_recorder

#         super().__init__(
#             *args,
#             **kwargs,
#         )

#     def _append_audio_buffer(
#         self,
#         pcm_bytes,
#         sample_rate,
#     ):
#         super()._append_audio_buffer(
#             pcm_bytes,
#             sample_rate,
#         )

#         recorder = self.voice_incident_recorder

#         if recorder is not None:
#             recorder.feed_pcm(
#                 pcm_bytes,
#                 sample_rate,
#             )


# def extract_token_from_url(
#     launch_url,
# ):
#     try:
#         parsed = urlparse(launch_url)

#     except Exception:
#         raise ValueError("Invalid proctor launch URL.")

#     if parsed.scheme != PROTOCOL_SCHEME:
#         raise ValueError("Invalid proctor protocol.")

#     if parsed.netloc != LAUNCH_ACTION:
#         raise ValueError("Invalid proctor launch action.")

#     query = parse_qs(parsed.query)

#     tokens = query.get("token")

#     if not tokens:
#         raise ValueError("Launch token is missing.")

#     token = tokens[0].strip()

#     if not token:
#         raise ValueError("Launch token is empty.")

#     return token


# def get_launch_token():
#     parser = argparse.ArgumentParser(prog="Skolariq Proctor")

#     parser.add_argument(
#         "launch_url",
#         nargs="?",
#     )

#     parser.add_argument(
#         "--token",
#         required=False,
#     )

#     args = parser.parse_args()

#     if args.token:
#         return args.token.strip()

#     if args.launch_url:
#         try:
#             return extract_token_from_url(args.launch_url)

#         except ValueError as error:
#             print(f"Launch rejected: {error}")

#             sys.exit(1)

#     print("Launch rejected: " "No launch token provided.")

#     sys.exit(1)


# def get_assessment_web_base_url():
#     configured_url = getattr(
#         settings,
#         "ASSESSMENT_WEB_BASE_URL",
#         None,
#     )

#     if configured_url:
#         return str(configured_url).strip().rstrip("/")

#     return DEFAULT_ASSESSMENT_WEB_BASE_URL


# def get_assessment_frontend_base_url():
#     configured_url = getattr(
#         settings,
#         "ASSESSMENT_FRONTEND_BASE_URL",
#         None,
#     )

#     if configured_url:
#         return str(configured_url).strip().rstrip("/")

#     environment_url = os.getenv(
#         "ASSESSMENT_FRONTEND_BASE_URL",
#         "",
#     )

#     if environment_url:
#         return str(environment_url).strip().rstrip("/")

#     return get_assessment_web_base_url()


# def build_assessments_center_url():
#     return f"{get_assessment_frontend_base_url()}" "/student/assessments-center"


# def open_assessments_center():
#     target_url = build_assessments_center_url()

#     print()

#     print(
#         "[PROCTOR] Opening assessments center:",
#         target_url,
#     )

#     try:
#         opened = webbrowser.open(
#             target_url,
#             new=1,
#             autoraise=True,
#         )

#         if not opened:
#             print(
#                 "[PROCTOR] Browser open request was issued, "
#                 "but the operating system did not confirm it."
#             )

#         return bool(opened)

#     except Exception as error:
#         print(
#             "[PROCTOR] Unable to open assessments center:",
#             error,
#         )

#         return False


# def get_socket_server_url():
#     configured_url = getattr(
#         settings,
#         "SOCKET_SERVER_URL",
#         None,
#     )

#     if configured_url:
#         return str(configured_url).strip().rstrip("/")

#     return get_assessment_web_base_url()


# def build_bootstrap_url(
#     token,
# ):
#     base_url = get_assessment_web_base_url()

#     encoded_token = quote(
#         token,
#         safe="",
#     )

#     return f"{base_url}" "/student/proctor/bootstrap" f"?token={encoded_token}"


# def open_camera():
#     if os.name == "nt":
#         camera = cv2.VideoCapture(
#             CAMERA_INDEX,
#             cv2.CAP_DSHOW,
#         )

#     else:
#         camera = cv2.VideoCapture(CAMERA_INDEX)

#     if not camera.isOpened():
#         raise RuntimeError(f"Unable to open camera index " f"{CAMERA_INDEX}.")

#     camera.set(
#         cv2.CAP_PROP_FRAME_WIDTH,
#         CAMERA_WIDTH,
#     )

#     camera.set(
#         cv2.CAP_PROP_FRAME_HEIGHT,
#         CAMERA_HEIGHT,
#     )

#     success, frame = camera.read()

#     if not success or frame is None:
#         camera.release()

#         raise RuntimeError("Camera opened but failed to " "provide a valid frame.")

#     return camera


# def start_microphone():
#     try:
#         device_info = sd.query_devices(kind="input")

#         if not device_info:
#             raise RuntimeError("No microphone input device " "was found.")

#         samplerate = float(
#             device_info.get(
#                 "default_samplerate",
#                 44100,
#             )
#         )

#         if samplerate <= 0:
#             samplerate = 44100.0

#         stream = sd.InputStream(
#             device=None,
#             channels=MIC_CHANNELS,
#             samplerate=samplerate,
#             dtype="float32",
#             blocksize=1024,
#         )

#         stream.start()

#         return stream

#     except Exception as error:
#         raise RuntimeError(f"Unable to start microphone: " f"{error}") from error


# def stop_microphone(
#     microphone,
# ):
#     if microphone is None:
#         return

#     try:
#         microphone.stop()

#     except Exception:
#         pass

#     try:
#         microphone.close()

#     except Exception:
#         pass


# def start_kiosk(
#     token,
#     proctor_socket=None,
#     before_security_termination_callback=None,
# ):
#     bootstrap_url = build_bootstrap_url(token)

#     print()

#     print("[PROCTOR] Starting secure kiosk...")

#     print("[PROCTOR] Bootstrap URL prepared.")

#     kiosk = KioskManager(
#         proctor_socket=proctor_socket,
#         before_security_termination_callback=before_security_termination_callback,
#     )

#     if proctor_socket is not None:
#         print("[PROCTOR] Proctor socket attached " "to kiosk manager.")

#     else:
#         print("[PROCTOR] Kiosk manager started " "without proctor socket.")

#     try:
#         process = kiosk.start(bootstrap_url)

#     except Exception as error:
#         print("[PROCTOR] Kiosk launch failed.")

#         print(f"[PROCTOR] Reason: {error}")

#         sys.exit(1)

#     print("[PROCTOR] Kiosk started successfully.")

#     return (
#         kiosk,
#         process,
#     )


# def start_keyboard_lockdown():
#     app_environment = str(
#         getattr(
#             settings,
#             "APP_ENV",
#             "development",
#         )
#     ).lower()

#     allow_development_escape = app_environment != "production"

#     lockdown = KeyboardLockdownManager(
#         allow_development_escape=allow_development_escape
#     )

#     lockdown.start()

#     return lockdown


# def get_process_pid(
#     process,
# ):
#     if process is None:
#         return None

#     if isinstance(
#         process,
#         int,
#     ):
#         return process if process > 0 else None

#     try:
#         pid = int(
#             getattr(
#                 process,
#                 "pid",
#             )
#         )

#     except (
#         AttributeError,
#         TypeError,
#         ValueError,
#     ):
#         return None

#     return pid if pid > 0 else None


# def _normalize_process_path(value):
#     if not value:
#         return ""

#     try:
#         return os.path.normcase(os.path.abspath(os.path.expanduser(str(value))))
#     except Exception:
#         return os.path.normcase(str(value))


# def _windows_process_snapshot():
#     """
#     Return a lightweight Windows process snapshot without using
#     psutil.Process.parent()/ppid().

#     The ProcessMonitor's strict cleanup can create a lot of process churn.
#     Repeated psutil parent lookups on Windows rebuild a global PPID map and can
#     become very slow. Toolhelp gives us the PID/PPID/name data in one native
#     snapshot and avoids that startup bottleneck.
#     """
#     if os.name != "nt":
#         return {}

#     try:
#         import ctypes
#         from ctypes import wintypes

#         TH32CS_SNAPPROCESS = 0x00000002
#         MAX_PATH = 260
#         INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

#         class PROCESSENTRY32W(ctypes.Structure):
#             _fields_ = [
#                 ("dwSize", wintypes.DWORD),
#                 ("cntUsage", wintypes.DWORD),
#                 ("th32ProcessID", wintypes.DWORD),
#                 ("th32DefaultHeapID", ctypes.c_size_t),
#                 ("th32ModuleID", wintypes.DWORD),
#                 ("cntThreads", wintypes.DWORD),
#                 ("th32ParentProcessID", wintypes.DWORD),
#                 ("pcPriClassBase", wintypes.LONG),
#                 ("dwFlags", wintypes.DWORD),
#                 ("szExeFile", wintypes.WCHAR * MAX_PATH),
#             ]

#         kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

#         create_snapshot = kernel32.CreateToolhelp32Snapshot
#         create_snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
#         create_snapshot.restype = wintypes.HANDLE

#         process_first = kernel32.Process32FirstW
#         process_first.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
#         process_first.restype = wintypes.BOOL

#         process_next = kernel32.Process32NextW
#         process_next.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
#         process_next.restype = wintypes.BOOL

#         close_handle = kernel32.CloseHandle
#         close_handle.argtypes = [wintypes.HANDLE]
#         close_handle.restype = wintypes.BOOL

#         snapshot_handle = create_snapshot(TH32CS_SNAPPROCESS, 0)

#         if snapshot_handle in (None, 0, INVALID_HANDLE_VALUE):
#             return {}

#         entry = PROCESSENTRY32W()
#         entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
#         processes = {}

#         try:
#             success = bool(
#                 process_first(
#                     snapshot_handle,
#                     ctypes.byref(entry),
#                 )
#             )

#             while success:
#                 pid = int(entry.th32ProcessID)

#                 if pid >= 0:
#                     processes[pid] = {
#                         "pid": pid,
#                         "ppid": int(entry.th32ParentProcessID),
#                         "name": str(entry.szExeFile or "").strip(),
#                     }

#                 success = bool(
#                     process_next(
#                         snapshot_handle,
#                         ctypes.byref(entry),
#                     )
#                 )

#         finally:
#             close_handle(snapshot_handle)

#         return processes

#     except Exception as error:
#         print(
#             "[PROCESS MONITOR] Windows process snapshot warning:",
#             error,
#         )
#         return {}


# def _current_proctor_ancestor_pids(process_snapshot):
#     current_pid = int(os.getpid())
#     protected_pids = {current_pid}

#     try:
#         direct_parent_pid = int(os.getppid())
#     except Exception:
#         direct_parent_pid = 0

#     if direct_parent_pid > 0:
#         protected_pids.add(direct_parent_pid)

#     if not isinstance(process_snapshot, dict) or not process_snapshot:
#         return protected_pids

#     cursor = current_pid
#     visited = set()

#     for _ in range(32):
#         if cursor in visited:
#             break

#         visited.add(cursor)

#         record = process_snapshot.get(cursor)

#         if not isinstance(record, dict):
#             break

#         try:
#             parent_pid = int(record.get("ppid") or 0)
#         except (TypeError, ValueError):
#             break

#         if parent_pid <= 0 or parent_pid == cursor:
#             break

#         protected_pids.add(parent_pid)
#         cursor = parent_pid

#     return protected_pids


# def _install_fast_pre_exam_process_guards(process_monitor):
#     """
#     Temporarily replace only the ProcessMonitor helpers that repeatedly call
#     psutil parent()/ppid() during the pre-exam cleanup.

#     Returns a callback that restores the original helpers. If anything needed
#     for the safe replacement is unavailable, no patch is installed.
#     """
#     if process_monitor is None or psutil is None or os.name != "nt":
#         return lambda: None

#     process_snapshot = _windows_process_snapshot()

#     if not process_snapshot:
#         return lambda: None

#     protected_proctor_pids = _current_proctor_ancestor_pids(process_snapshot)

#     original_contains_proctor = getattr(
#         process_monitor,
#         "_process_tree_contains_proctor",
#         None,
#     )
#     original_get_browser_root = getattr(
#         process_monitor,
#         "_get_browser_root",
#         None,
#     )
#     original_collect_strict_roots = getattr(
#         process_monitor,
#         "_collect_strict_user_process_roots",
#         None,
#     )

#     def fast_process_tree_contains_proctor(process):
#         if process is None:
#             return True

#         try:
#             target_pid = int(process.pid)
#         except (TypeError, ValueError, AttributeError):
#             return True

#         return target_pid in protected_proctor_pids

#     def fast_get_browser_root(process):
#         if process is None:
#             return None

#         try:
#             current_pid = int(process.pid)
#         except (TypeError, ValueError, AttributeError):
#             return process

#         root = process
#         visited = set()

#         while current_pid > 0 and current_pid not in visited:
#             visited.add(current_pid)

#             current_record = process_snapshot.get(current_pid)

#             if not isinstance(current_record, dict):
#                 break

#             current_name = str(current_record.get("name") or "").strip()

#             try:
#                 if not process_monitor._is_browser(current_name):
#                     break
#             except Exception:
#                 break

#             try:
#                 root = psutil.Process(current_pid)
#             except Exception:
#                 break

#             try:
#                 parent_pid = int(current_record.get("ppid") or 0)
#             except (TypeError, ValueError):
#                 break

#             if parent_pid <= 0 or parent_pid == current_pid:
#                 break

#             parent_record = process_snapshot.get(parent_pid)

#             if not isinstance(parent_record, dict):
#                 break

#             parent_name = str(parent_record.get("name") or "").strip()

#             try:
#                 if not process_monitor._is_browser(parent_name):
#                     break
#             except Exception:
#                 break

#             current_pid = parent_pid

#         return root

#     def fast_collect_strict_user_process_roots():
#         candidates = {}

#         for process in psutil.process_iter(
#             attrs=[
#                 "pid",
#                 "name",
#                 "exe",
#             ]
#         ):
#             try:
#                 if int(process.pid) == int(process_monitor.current_pid):
#                     continue

#                 if not process_monitor._is_current_user_process(process):
#                     continue

#                 if process_monitor._is_strict_lockdown_exempt(process):
#                     continue

#                 candidates[int(process.pid)] = process

#             except (
#                 psutil.NoSuchProcess,
#                 psutil.AccessDenied,
#                 psutil.ZombieProcess,
#             ):
#                 continue
#             except Exception:
#                 continue

#         if not candidates:
#             return []

#         candidate_pids = set(candidates.keys())
#         roots = []

#         for pid, process in candidates.items():
#             record = process_snapshot.get(pid)

#             try:
#                 parent_pid = int(record.get("ppid") if isinstance(record, dict) else 0)
#             except (TypeError, ValueError):
#                 parent_pid = 0

#             if parent_pid in candidate_pids:
#                 continue

#             roots.append(process)

#         return roots

#     if callable(original_contains_proctor):
#         process_monitor._process_tree_contains_proctor = (
#             fast_process_tree_contains_proctor
#         )

#     if callable(original_get_browser_root):
#         process_monitor._get_browser_root = fast_get_browser_root

#     if callable(original_collect_strict_roots):
#         process_monitor._collect_strict_user_process_roots = (
#             fast_collect_strict_user_process_roots
#         )

#     print(
#         "[PROCESS MONITOR] Fast Windows startup process guards enabled "
#         f"| protected_proctor_pids={sorted(protected_proctor_pids)}"
#     )

#     def restore():
#         try:
#             if callable(original_contains_proctor):
#                 process_monitor._process_tree_contains_proctor = (
#                     original_contains_proctor
#                 )

#             if callable(original_get_browser_root):
#                 process_monitor._get_browser_root = original_get_browser_root

#             if callable(original_collect_strict_roots):
#                 process_monitor._collect_strict_user_process_roots = (
#                     original_collect_strict_roots
#                 )

#         except Exception:
#             pass

#     return restore


# def _is_same_proctor_process(process):
#     """
#     Identify another instance of this exact proctor without treating every
#     python.exe process as a duplicate.
#     """
#     if psutil is None or process is None:
#         return False

#     try:
#         pid = int(process.pid)
#     except (TypeError, ValueError, AttributeError):
#         return False

#     if pid <= 0 or pid == os.getpid():
#         return False

#     # Never classify the launcher/parent chain of the currently running proctor
#     # as a stale duplicate. This is especially important for custom-protocol,
#     # batch-file, development Python, and packaged-launcher flows.
#     if pid in _get_current_process_ancestor_pids():
#         return False

#     try:
#         current_username = str(psutil.Process(os.getpid()).username() or "").lower()
#     except Exception:
#         current_username = ""

#     try:
#         candidate_username = str(process.username() or "").lower()
#     except Exception:
#         candidate_username = ""

#     if (
#         current_username
#         and candidate_username
#         and current_username != candidate_username
#     ):
#         return False

#     current_main_path = _normalize_process_path(__file__)
#     current_project_root = _normalize_process_path(
#         os.path.dirname(os.path.dirname(current_main_path))
#     )
#     current_executable = _normalize_process_path(sys.executable)

#     try:
#         candidate_executable = _normalize_process_path(process.exe())
#     except Exception:
#         candidate_executable = ""

#     if bool(getattr(sys, "frozen", False)):
#         if candidate_executable and candidate_executable == current_executable:
#             return True

#     try:
#         cmdline = [
#             str(item or "").strip()
#             for item in (process.cmdline() or [])
#             if str(item or "").strip()
#         ]
#     except Exception:
#         cmdline = []

#     has_module_launch = False

#     for index, argument in enumerate(cmdline[:-1]):
#         if argument == "-m" and cmdline[index + 1].lower() == "src.main":
#             has_module_launch = True
#             break

#     has_exact_main_path = False
#     has_src_main_argument = False

#     for argument in cmdline:
#         cleaned = argument.strip().strip('"').strip("'")

#         if not cleaned:
#             continue

#         if _normalize_process_path(cleaned) == current_main_path:
#             has_exact_main_path = True
#             break

#         slash_argument = cleaned.replace("\\", "/").lower()

#         if slash_argument.endswith("/src/main.py") or slash_argument == "src/main.py":
#             has_src_main_argument = True

#     try:
#         candidate_cwd = _normalize_process_path(process.cwd())
#     except Exception:
#         candidate_cwd = ""

#     same_project = bool(
#         candidate_cwd and current_project_root and candidate_cwd == current_project_root
#     )

#     if has_exact_main_path:
#         return True

#     if same_project and (has_module_launch or has_src_main_argument):
#         return True

#     return False


# def _get_current_process_ancestor_pids():
#     """
#     Return the PID chain that launched this proctor process.

#     These processes are protected from duplicate-instance cleanup because a
#     protocol launcher, development wrapper, Python bootstrapper, or packaged
#     executable may legitimately be an ancestor of the active proctor process.
#     """
#     protected_pids = {os.getpid()}

#     if psutil is None:
#         return protected_pids

#     try:
#         current_process = psutil.Process(os.getpid())

#         for parent in current_process.parents():
#             try:
#                 parent_pid = int(parent.pid)
#             except (TypeError, ValueError, AttributeError):
#                 continue

#             if parent_pid > 0:
#                 protected_pids.add(parent_pid)

#     except Exception:
#         pass

#     return protected_pids


# def _is_current_process_or_ancestor(process):
#     if process is None:
#         return False

#     try:
#         pid = int(process.pid)
#     except (TypeError, ValueError, AttributeError):
#         return False

#     return pid in _get_current_process_ancestor_pids()


# def _force_terminate_previous_proctor(process):
#     if psutil is None or process is None:
#         return False

#     try:
#         pid = int(process.pid)
#     except (TypeError, ValueError, AttributeError):
#         return False

#     if pid <= 0 or _is_current_process_or_ancestor(process):
#         print(
#             "[PROCTOR][DUPLICATE CLEANUP] Protected current/launcher process "
#             f"will not be terminated | pid={pid}"
#         )
#         return False

#     if os.name == "nt":
#         try:
#             creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

#             # Deliberately do NOT use taskkill /T here. A previous proctor may
#             # have launched or share a wrapper tree with the new instance.
#             # Killing only the exact stale PID prevents Windows from taking the
#             # newly launched proctor down with an ancestor/process tree.
#             subprocess.run(
#                 [
#                     "taskkill",
#                     "/PID",
#                     str(pid),
#                     "/F",
#                 ],
#                 stdout=subprocess.PIPE,
#                 stderr=subprocess.PIPE,
#                 text=True,
#                 timeout=PREVIOUS_PROCTOR_INSTANCE_SHUTDOWN_TIMEOUT_SECONDS,
#                 creationflags=creationflags,
#                 check=False,
#             )

#         except Exception as error:
#             print(
#                 "[PROCTOR][DUPLICATE CLEANUP] taskkill warning "
#                 f"| pid={pid} | error={error}"
#             )

#         deadline = time.monotonic() + PREVIOUS_PROCTOR_INSTANCE_SHUTDOWN_TIMEOUT_SECONDS

#         while time.monotonic() < deadline:
#             if not psutil.pid_exists(pid):
#                 return True

#             time.sleep(0.05)

#     # Re-check immediately before the psutil fallback in case process ancestry
#     # changed while Windows cleanup was attempted.
#     if _is_current_process_or_ancestor(process):
#         print(
#             "[PROCTOR][DUPLICATE CLEANUP] Cleanup aborted because PID became "
#             f"part of the active launch chain | pid={pid}"
#         )
#         return False

#     try:
#         process.terminate()
#     except (
#         psutil.NoSuchProcess,
#         psutil.ZombieProcess,
#     ):
#         return True
#     except Exception:
#         pass

#     try:
#         process.wait(timeout=1.0)
#     except Exception:
#         if _is_current_process_or_ancestor(process):
#             return False

#         try:
#             process.kill()
#         except Exception:
#             pass

#     deadline = time.monotonic() + 1.5

#     while time.monotonic() < deadline:
#         if not psutil.pid_exists(pid):
#             return True

#         time.sleep(0.05)

#     return not psutil.pid_exists(pid)


# def terminate_previous_proctor_instances():
#     """
#     A valid new launch supersedes any stale instance of this same application.

#     Unrelated Python/backend processes are deliberately ignored.
#     """
#     if psutil is None:
#         print(
#             "[PROCTOR][DUPLICATE CLEANUP] psutil unavailable; "
#             "skipping stale-instance cleanup."
#         )
#         return []

#     print()
#     print("[PROCTOR][DUPLICATE CLEANUP] Checking for stale proctor instances...")

#     candidates = []

#     for process in psutil.process_iter(attrs=["pid", "name"]):
#         try:
#             if _is_same_proctor_process(process):
#                 candidates.append(process)
#         except (
#             psutil.NoSuchProcess,
#             psutil.AccessDenied,
#             psutil.ZombieProcess,
#         ):
#             continue
#         except Exception:
#             continue

#     if not candidates:
#         print("[PROCTOR][DUPLICATE CLEANUP] No previous proctor instance found.")
#         return []

#     terminated_pids = []

#     for process in candidates:
#         try:
#             pid = int(process.pid)
#         except Exception:
#             continue

#         try:
#             process_name = process.name()
#         except Exception:
#             process_name = "unknown"

#         print(
#             "[PROCTOR][DUPLICATE CLEANUP] Previous instance detected "
#             f"| process={process_name} | pid={pid}"
#         )

#         if _force_terminate_previous_proctor(process):
#             terminated_pids.append(pid)
#             print(
#                 "[PROCTOR][DUPLICATE CLEANUP] Previous instance terminated "
#                 f"| pid={pid}"
#             )
#         else:
#             print(
#                 "[PROCTOR][DUPLICATE CLEANUP] Warning: previous instance could "
#                 f"not be fully terminated | pid={pid}. Startup will continue."
#             )

#     return terminated_pids


# def prepare_process_monitor(
#     frontend_event_callback=None,
# ):
#     if ProcessMonitor is None:
#         print()

#         print("[PROCESS MONITOR] Process monitoring is unavailable.")

#         if PROCESS_MONITOR_IMPORT_ERROR is not None:
#             print(
#                 "[PROCESS MONITOR] Reason:",
#                 PROCESS_MONITOR_IMPORT_ERROR,
#             )

#         return None

#     try:
#         print()

#         print("[PROCESS MONITOR] Initializing process monitor...")

#         try:
#             process_monitor = ProcessMonitor(
#                 check_interval=2.0,
#                 block_external_browsers=True,
#                 terminate_remote_access=True,
#                 terminate_screen_sharing=True,
#                 frontend_event_callback=frontend_event_callback,
#             )

#         except TypeError:
#             # Backward compatibility with an older ProcessMonitor build.
#             process_monitor = ProcessMonitor(
#                 check_interval=2.0,
#                 block_external_browsers=True,
#                 terminate_remote_access=True,
#                 terminate_screen_sharing=True,
#             )

#             if hasattr(process_monitor, "frontend_event_callback"):
#                 process_monitor.frontend_event_callback = frontend_event_callback

#         process_monitor.capture_pre_kiosk_browser_processes()

#         print("[PROCESS MONITOR] Pre-kiosk browser snapshot completed.")

#         return process_monitor

#     except Exception as error:
#         print(
#             "[PROCESS MONITOR] Initialization failed:",
#             error,
#         )

#         return None


# def perform_pre_exam_process_cleanup(
#     process_monitor,
# ):
#     """
#     Best-effort targeted process cleanup before camera/microphone startup.

#     The production ProcessMonitor still performs the same cleanup. On Windows,
#     only its repeated parent/PPID lookups are temporarily replaced with a native
#     process snapshot so process churn cannot stall startup inside psutil.ppid().
#     """
#     if process_monitor is None:
#         print(
#             "[PROCESS MONITOR] Pre-exam process cleanup is unavailable. "
#             "Continuing with normal startup."
#         )

#         return {
#             "supported": False,
#             "detected": [],
#             "terminated": [],
#             "failed": [],
#         }

#     cleanup_method = getattr(
#         process_monitor,
#         "terminate_pre_exam_media_processes",
#         None,
#     )

#     if not callable(cleanup_method):
#         print(
#             "[PROCESS MONITOR] Installed ProcessMonitor does not expose "
#             "terminate_pre_exam_media_processes(). "
#             "Continuing with normal startup."
#         )

#         return {
#             "supported": False,
#             "detected": [],
#             "terminated": [],
#             "failed": [],
#         }

#     print()
#     print(
#         "[PROCESS MONITOR] Performing targeted pre-exam cleanup "
#         "before camera/microphone startup..."
#     )

#     restore_guards = _install_fast_pre_exam_process_guards(process_monitor)

#     try:
#         result = cleanup_method()

#     except Exception as error:
#         print(
#             "[PROCESS MONITOR] Pre-exam cleanup error:",
#             error,
#         )
#         print(
#             "[PROCESS MONITOR] Cleanup failure is non-blocking. "
#             "Continuing with camera/microphone and secure kiosk startup."
#         )

#         return {
#             "supported": True,
#             "detected": [],
#             "terminated": [],
#             "failed": [],
#             "cleanup_error": str(error),
#         }

#     finally:
#         try:
#             restore_guards()
#         except Exception:
#             pass

#     if not isinstance(result, dict):
#         result = {
#             "detected": [],
#             "terminated": [],
#             "failed": [],
#         }

#     detected = result.get("detected", [])
#     terminated = result.get("terminated", [])
#     failed = result.get("failed", [])

#     if not isinstance(detected, list):
#         detected = []

#     if not isinstance(terminated, list):
#         terminated = []

#     if not isinstance(failed, list):
#         failed = []

#     result["supported"] = True
#     result["detected"] = detected
#     result["terminated"] = terminated
#     result["failed"] = failed

#     print(
#         "[PROCESS MONITOR] Targeted pre-exam cleanup completed "
#         f"| detected={len(detected)} "
#         f"| terminated={len(terminated)} "
#         f"| remaining={len(failed)}"
#     )

#     if failed:
#         remaining_processes = []

#         for item in failed:
#             if not isinstance(item, dict):
#                 continue

#             process_name = str(item.get("process_name", "") or "unknown").strip()
#             pid = item.get("pid")

#             remaining_processes.append(
#                 f"{process_name}" + (f" (PID {pid})" if pid is not None else "")
#             )

#         remaining_text = (
#             ", ".join(remaining_processes)
#             if remaining_processes
#             else f"{len(failed)} process(es)"
#         )

#         print(
#             "[PROCESS MONITOR] Warning: some restricted processes "
#             f"could not be terminated yet: {remaining_text}"
#         )
#         print(
#             "[PROCESS MONITOR] This is non-blocking. The assessment will "
#             "continue starting, and continuous process monitoring will retry "
#             "restricted applications."
#         )

#     print(
#         "[PROCESS MONITOR] Pre-exam cleanup finished. "
#         "Camera/microphone initialization may proceed."
#     )

#     return result


# def _get_process_monitor_frontend_message(
#     payload,
# ):
#     if isinstance(
#         payload,
#         dict,
#     ):
#         message = payload.get("message")

#     else:
#         message = payload

#     message = str(message or "").strip()

#     return message or None


# def emit_process_monitor_frontend_event(
#     socket_client,
#     payload,
# ):
#     """
#     Emit a process-monitor notification to Node using a dedicated event.

#     Privacy contract:
#     the outbound payload contains exactly ONE field:
#         {"message": "..."}

#     No PID, process name, executable path, user/session/test/schedule ID,
#     timestamp, category, action, or diagnostic metadata is emitted.
#     """

#     message = _get_process_monitor_frontend_message(payload)

#     if not message or socket_client is None:
#         return False

#     sio_client = getattr(
#         socket_client,
#         "sio",
#         None,
#     )

#     if sio_client is None or not getattr(
#         sio_client,
#         "connected",
#         False,
#     ):
#         return False

#     if not bool(
#         getattr(
#             socket_client,
#             "joined_room",
#             False,
#         )
#     ):
#         return False

#     try:
#         sio_client.emit(
#             "proctor-process-monitor-event",
#             {
#                 "message": message,
#             },
#         )

#         print("[PROCESS MONITOR][SOCKET] Frontend message emitted: " f"{message}")

#         return True

#     except Exception as error:
#         print(
#             "[PROCESS MONITOR][SOCKET] Frontend message emit failed:",
#             error,
#         )

#         return False


# def start_process_monitor_frontend_forwarder(
#     pipeline,
#     socket_client,
# ):
#     """
#     Forward sanitized ProcessMonitor messages to the already joined proctor
#     socket room. Events detected during pre-exam cleanup are buffered until the
#     socket has connected and joined the room, so they are not lost.
#     """

#     if not isinstance(
#         pipeline,
#         dict,
#     ):
#         return False

#     event_queue = pipeline.get("process_monitor_frontend_queue")

#     if event_queue is None or socket_client is None:
#         return False

#     existing_thread = pipeline.get("process_monitor_frontend_thread")

#     if existing_thread is not None and existing_thread.is_alive():
#         return True

#     stop_event = threading.Event()
#     pipeline["process_monitor_frontend_stop_event"] = stop_event

#     def worker():
#         pending_payload = None

#         while not stop_event.is_set():
#             if pending_payload is None:
#                 try:
#                     pending_payload = event_queue.get(
#                         timeout=0.20,
#                     )

#                 except queue.Empty:
#                     continue

#                 except Exception:
#                     pending_payload = None
#                     continue

#             if emit_process_monitor_frontend_event(
#                 socket_client=socket_client,
#                 payload=pending_payload,
#             ):
#                 pending_payload = None
#                 continue

#             stop_event.wait(0.20)

#     thread = threading.Thread(
#         target=worker,
#         name="SkolariqProcessMonitorFrontendForwarder",
#         daemon=True,
#     )

#     pipeline["process_monitor_frontend_thread"] = thread

#     thread.start()

#     print(
#         "[PROCESS MONITOR] Frontend notification forwarder started. "
#         "Only human-readable message text will be emitted."
#     )

#     return True


# def stop_process_monitor_frontend_forwarder(
#     pipeline,
# ):
#     if not isinstance(
#         pipeline,
#         dict,
#     ):
#         return

#     stop_event = pipeline.get("process_monitor_frontend_stop_event")

#     if stop_event is not None:
#         try:
#             stop_event.set()
#         except Exception:
#             pass

#     thread = pipeline.get("process_monitor_frontend_thread")

#     if (
#         thread is not None
#         and thread.is_alive()
#         and thread is not threading.current_thread()
#     ):
#         try:
#             thread.join(timeout=1.0)
#         except Exception:
#             pass

#     pipeline["process_monitor_frontend_stop_event"] = None
#     pipeline["process_monitor_frontend_thread"] = None


# def activate_process_monitor(
#     process_monitor,
#     kiosk_process,
# ):
#     """
#     Protect the kiosk process tree and start continuous targeted monitoring.

#     Deliberately avoids the legacy blanket/strict cleanup loop. The updated
#     ProcessMonitor's normal scan already blocks the restricted categories
#     (external browsers, remote access, screen sharing, user media/camera/audio
#     apps, and duplicate proctor instances) without repeatedly sweeping every
#     current-user process.
#     """
#     if process_monitor is None:
#         return False

#     kiosk_pid = get_process_pid(kiosk_process)

#     if kiosk_pid is None:
#         print(
#             "[PROCESS MONITOR] Kiosk PID is unavailable. "
#             "External-browser termination will remain disabled until a "
#             "kiosk PID is available, but other targeted monitoring can start."
#         )

#     else:
#         try:
#             process_monitor.set_kiosk_root_pid(kiosk_pid)

#             print("[PROCESS MONITOR] Secure kiosk process tree protected.")

#             enable_strict_lockdown = getattr(
#                 process_monitor,
#                 "enable_strict_user_process_lockdown",
#                 None,
#             )

#             if callable(enable_strict_lockdown):
#                 enable_strict_lockdown(False)

#                 print(
#                     "[PROCESS MONITOR] Legacy blanket strict-lockdown loop "
#                     "disabled. Targeted continuous monitoring will be used."
#                 )

#         except Exception as error:
#             print(
#                 "[PROCESS MONITOR] Failed to register kiosk PID:",
#                 error,
#             )

#             kiosk_pid = None

#     if kiosk_pid is not None:
#         try:
#             terminated_browser_pids = (
#                 process_monitor.terminate_pre_kiosk_browser_processes()
#             )

#             if terminated_browser_pids:
#                 print(
#                     "[PROCESS MONITOR] Pre-existing browser sessions terminated. "
#                     f"Root PIDs={terminated_browser_pids}"
#                 )

#             else:
#                 print(
#                     "[PROCESS MONITOR] No pre-existing browser session "
#                     "required termination."
#                 )

#         except Exception as error:
#             print(
#                 "[PROCESS MONITOR] Failed to terminate "
#                 "pre-existing browser sessions:",
#                 error,
#             )

#     try:
#         started = process_monitor.start()

#         if started:
#             print("[PROCESS MONITOR] Continuous targeted process monitoring started.")

#         else:
#             print(
#                 "[PROCESS MONITOR] Continuous monitor was already active "
#                 "or could not be started."
#             )

#         return bool(started)

#     except Exception as error:
#         print(
#             "[PROCESS MONITOR] Failed to start continuous monitoring:",
#             error,
#         )

#         return False


# def stop_process_monitor(
#     process_monitor,
# ):
#     if process_monitor is None:
#         return

#     try:
#         process_monitor.stop()

#         print("[PROCESS MONITOR] Process monitoring stopped.")

#     except Exception as error:
#         print(
#             "[PROCESS MONITOR] Cleanup error:",
#             error,
#         )


# def start_proctor_socket(
#     session,
#     tracking_start_event=None,
#     audio_monitor=None,
#     before_exam_complete_callback=None,
#     before_tracking_start_callback=None,
# ):
#     """
#     Start the native Socket.IO client.

#     Backward compatibility:
#     - tracking_start_event is optional.
#     - audio_monitor is optional.
#     - before_exam_complete_callback is optional.
#     - before_tracking_start_callback is optional.
#     - Existing calls that pass only session continue to work.

#     Secure kiosk behavior:
#     - When tracking_start_event is supplied, Python listens for
#       "proctor-tracking-start".
#     - Camera/microphone may already be active before this event.
#     - Violation detection remains paused until the validated
#       frontend signal reaches Python through Node.
#     """

#     try:
#         socket_client = ProctorSocketClient(
#             server_url=get_socket_server_url(),
#             token=session.get("raw_token"),
#             proctor_session_id=session["proctor_session_id"],
#             test_id=session["test_id"],
#             schedule_id=session["schedule_id"],
#         )

#         def exam_completed(
#             data,
#         ):
#             global exam_completed_flag

#             print()

#             print("[PROCTOR] Exam completion " "received.")

#             print(
#                 "[PROCTOR]",
#                 data,
#             )

#             exam_completed_flag = True

#             if callable(before_exam_complete_callback):
#                 try:
#                     before_exam_complete_callback()

#                 except Exception as error:
#                     print(
#                         "[PROCTOR] Exam-complete final evidence callback error:",
#                         error,
#                     )

#         socket_client.exam_completed_callback = exam_completed

#         if audio_monitor is not None:

#             def microphone_devices_request(
#                 data,
#             ):
#                 status = audio_monitor.get_status()

#                 return {
#                     "devices": audio_monitor.get_available_microphones(),
#                     "current_device": status.get("active_microphone"),
#                     "reason": None,
#                 }

#             def microphone_change_request(
#                 data,
#             ):
#                 payload = (
#                     data
#                     if isinstance(
#                         data,
#                         dict,
#                     )
#                     else {}
#                 )

#                 device_key = str(
#                     payload.get(
#                         "device_key",
#                         "",
#                     )
#                 ).strip()

#                 if not device_key:
#                     return {
#                         "success": False,
#                         "reason": "MICROPHONE_DEVICE_KEY_REQUIRED",
#                     }

#                 return audio_monitor.switch_microphone(
#                     device_key=device_key,
#                     timeout=8.0,
#                 )

#             socket_client.microphone_devices_request_callback = (
#                 microphone_devices_request
#             )

#             socket_client.microphone_change_request_callback = microphone_change_request

#             print("[PROCTOR] Microphone device-control callbacks registered.")

#         if tracking_start_event is not None:

#             expected_session_id = str(
#                 session.get(
#                     "proctor_session_id",
#                     "",
#                 )
#             )

#             expected_test_id = str(
#                 session.get(
#                     "test_id",
#                     "",
#                 )
#             )

#             expected_schedule_id = str(
#                 session.get(
#                     "schedule_id",
#                     "",
#                 )
#             )

#             def proctor_tracking_start(
#                 data,
#             ):
#                 payload = (
#                     data
#                     if isinstance(
#                         data,
#                         dict,
#                     )
#                     else {}
#                 )

#                 received_session_id = str(
#                     payload.get(
#                         "proctor_session_id",
#                         "",
#                     )
#                 )

#                 received_test_id = str(
#                     payload.get(
#                         "test_id",
#                         "",
#                     )
#                 )

#                 received_schedule_id = str(
#                     payload.get(
#                         "schedule_id",
#                         "",
#                     )
#                 )

#                 if (
#                     not received_session_id
#                     or not received_test_id
#                     or not received_schedule_id
#                 ):
#                     print(
#                         "[SOCKET][TRACKING START IGNORED] "
#                         "Missing session/exam/schedule information."
#                     )

#                     return

#                 if (
#                     received_session_id != expected_session_id
#                     or received_test_id != expected_test_id
#                     or received_schedule_id != expected_schedule_id
#                 ):
#                     print(
#                         "[SOCKET][TRACKING START IGNORED] "
#                         "Received event does not match the active proctor session."
#                     )

#                     return

#                 if tracking_start_event.is_set():
#                     print(
#                         "[SOCKET][TRACKING START] "
#                         "Duplicate start signal received; tracking is already active."
#                     )

#                     return

#                 if callable(before_tracking_start_callback):
#                     try:
#                         before_tracking_start_callback()

#                     except Exception as error:
#                         print(
#                             "[SOCKET][TRACKING START ERROR] "
#                             "Unable to prepare audio tracking state:",
#                             error,
#                         )

#                         return

#                 tracking_start_event.set()

#                 print()

#                 print(
#                     "[SOCKET][TRACKING START] "
#                     "Validated frontend start signal received."
#                 )

#                 print("[PROCTOR] Violation tracking is now ACTIVE.")

#             sio_client = getattr(
#                 socket_client,
#                 "sio",
#                 None,
#             )

#             if sio_client is None or not hasattr(
#                 sio_client,
#                 "on",
#             ):
#                 raise RuntimeError(
#                     "Socket client does not expose a Socket.IO event interface."
#                 )

#             sio_client.on(
#                 "proctor-tracking-start",
#                 proctor_tracking_start,
#             )

#             print(
#                 "[PROCTOR] Tracking start listener registered. "
#                 "Violation tracking will remain paused until the secure exam page signals readiness."
#             )

#         socket_client.start_background()

#         print("[PROCTOR] Proctor socket " "startup requested.")

#         return socket_client

#     except Exception as error:
#         print(
#             "[PROCTOR] Socket startup failed:",
#             error,
#         )

#         return None


# def get_face_coordinates(
#     face,
# ):
#     x = None
#     y = None
#     width = None
#     height = None

#     if isinstance(
#         face,
#         dict,
#     ):

#         if "x" in face and "y" in face and "x2" in face and "y2" in face:
#             x = int(face["x"])

#             y = int(face["y"])

#             width = int(face["x2"] - face["x"])

#             height = int(face["y2"] - face["y"])

#         elif "x" in face and "y" in face and "w" in face and "h" in face:
#             x = int(face["x"])

#             y = int(face["y"])

#             width = int(face["w"])

#             height = int(face["h"])

#         elif "x" in face and "y" in face and "width" in face and "height" in face:
#             x = int(face["x"])

#             y = int(face["y"])

#             width = int(face["width"])

#             height = int(face["height"])

#         elif "bbox" in face and len(face["bbox"]) >= 4:
#             x = int(face["bbox"][0])

#             y = int(face["bbox"][1])

#             width = int(face["bbox"][2])

#             height = int(face["bbox"][3])

#     elif isinstance(
#         face,
#         (
#             list,
#             tuple,
#         ),
#     ):
#         if len(face) >= 4:
#             x = int(face[0])

#             y = int(face[1])

#             width = int(face[2])

#             height = int(face[3])

#     if x is None or y is None or width is None or height is None:
#         return None

#     return {
#         "x": x,
#         "y": y,
#         "width": width,
#         "height": height,
#     }


# def get_landmark_xy(
#     landmark,
# ):
#     if landmark is None:
#         return None

#     try:
#         if isinstance(landmark, dict):
#             x = float(landmark.get("x"))
#             y = float(landmark.get("y"))
#         else:
#             x = float(getattr(landmark, "x"))
#             y = float(getattr(landmark, "y"))
#     except (TypeError, ValueError, AttributeError):
#         return None

#     if not (math.isfinite(x) and math.isfinite(y)):
#         return None

#     return (x, y)


# def get_valid_landmark_points(
#     landmarks,
# ):
#     if landmarks is None:
#         return []

#     try:
#         iterable = list(landmarks)
#     except TypeError:
#         return []

#     points = []

#     for landmark in iterable:
#         point = get_landmark_xy(landmark)

#         if point is not None:
#             points.append(point)

#     return points


# def is_yunet_face_clipped_by_frame(
#     face,
#     frame_shape,
# ):
#     coordinates = get_face_coordinates(face)

#     if coordinates is None:
#         return False

#     frame_height = int(frame_shape[0])
#     frame_width = int(frame_shape[1])

#     x1 = int(coordinates["x"])
#     y1 = int(coordinates["y"])
#     x2 = int(coordinates["x"] + coordinates["width"])
#     y2 = int(coordinates["y"] + coordinates["height"])

#     tolerance = max(
#         1,
#         int(min(frame_width, frame_height) * 0.003),
#     )

#     return bool(
#         x1 <= tolerance
#         or y1 <= tolerance
#         or x2 >= (frame_width - 1 - tolerance)
#         or y2 >= (frame_height - 1 - tolerance)
#     )


# def are_face_landmarks_out_of_frame(
#     landmarks,
#     frame_shape,
# ):
#     points = get_valid_landmark_points(landmarks)

#     if len(points) < 20:
#         return False

#     frame_height = int(frame_shape[0])
#     frame_width = int(frame_shape[1])

#     normalized_count = sum(
#         1 for x, y in points if (-2.0 <= x <= 2.0 and -2.0 <= y <= 2.0)
#     )

#     coordinates_are_normalized = normalized_count >= int(len(points) * 0.90)

#     if coordinates_are_normalized:
#         outside_count = sum(
#             1 for x, y in points if (x < 0.0 or x > 1.0 or y < 0.0 or y > 1.0)
#         )

#         near_edge_count = sum(
#             1
#             for x, y in points
#             if (x <= 0.002 or x >= 0.998 or y <= 0.002 or y >= 0.998)
#         )
#     else:
#         outside_count = sum(
#             1
#             for x, y in points
#             if (x < 0.0 or x > (frame_width - 1) or y < 0.0 or y > (frame_height - 1))
#         )

#         pixel_edge_tolerance = max(
#             1,
#             int(min(frame_width, frame_height) * 0.003),
#         )

#         near_edge_count = sum(
#             1
#             for x, y in points
#             if (
#                 x <= pixel_edge_tolerance
#                 or x >= (frame_width - 1 - pixel_edge_tolerance)
#                 or y <= pixel_edge_tolerance
#                 or y >= (frame_height - 1 - pixel_edge_tolerance)
#             )
#         )

#     outside_threshold = max(
#         3,
#         int(math.ceil(len(points) * 0.01)),
#     )

#     near_edge_threshold = max(
#         12,
#         int(math.ceil(len(points) * 0.08)),
#     )

#     return bool(
#         outside_count >= outside_threshold or near_edge_count >= near_edge_threshold
#     )


# def evaluate_face_presence(
#     faces,
#     landmark_result,
#     frame_shape,
# ):
#     if faces is None:
#         faces = []

#     face_count = len(faces)

#     if not isinstance(landmark_result, dict):
#         landmark_result = {}

#     landmark_valid = bool(landmark_result.get("valid", False))

#     try:
#         landmark_face_count = int(landmark_result.get("face_count", 0) or 0)
#     except (TypeError, ValueError):
#         landmark_face_count = 0

#     landmarks = landmark_result.get("landmarks")

#     yunet_face_present = face_count > 0
#     landmarker_face_present = bool(landmark_valid or landmark_face_count > 0)

#     yunet_face_clipped = False

#     if face_count == 1:
#         yunet_face_clipped = is_yunet_face_clipped_by_frame(
#             faces[0],
#             frame_shape,
#         )

#     landmark_face_out_of_frame = False

#     if landmarker_face_present:
#         landmark_face_out_of_frame = are_face_landmarks_out_of_frame(
#             landmarks,
#             frame_shape,
#         )

#     partial_face_out_of_frame = False

#     if face_count <= 1:
#         if landmarker_face_present:
#             partial_face_out_of_frame = landmark_face_out_of_frame
#         elif yunet_face_present:
#             partial_face_out_of_frame = yunet_face_clipped

#     any_face_present = bool(yunet_face_present or landmarker_face_present)

#     no_face = bool((not any_face_present) or partial_face_out_of_frame)

#     if no_face:
#         if partial_face_out_of_frame:
#             decision = "FACE_PARTIALLY_OUT"
#         else:
#             decision = "NO_FACE"
#     elif face_count > 1:
#         decision = "MULTIPLE_FACES"
#     elif yunet_face_present and landmarker_face_present:
#         decision = "FACE_PRESENT_BOTH"
#     elif yunet_face_present:
#         decision = "FACE_PRESENT_YUNET"
#     elif landmarker_face_present:
#         decision = "FACE_PRESENT_LANDMARKER"
#     else:
#         decision = "NO_FACE"

#     return {
#         "no_face": no_face,
#         "decision": decision,
#         "face_count": face_count,
#         "landmark_valid": landmark_valid,
#         "landmark_face_count": landmark_face_count,
#         "yunet_face_present": yunet_face_present,
#         "landmarker_face_present": landmarker_face_present,
#         "yunet_face_clipped": yunet_face_clipped,
#         "landmark_face_out_of_frame": landmark_face_out_of_frame,
#         "partial_face_out_of_frame": partial_face_out_of_frame,
#     }


# def get_object_anomalies(
#     object_detections,
# ):
#     phone_detected = False

#     book_detected = False

#     extra_person_detected = False

#     phone_detections = []

#     book_detections = []

#     person_detections = []

#     for detection in object_detections:

#         if not isinstance(
#             detection,
#             dict,
#         ):
#             continue

#         label = str(
#             detection.get(
#                 "label",
#                 "",
#             )
#         ).upper()

#         if label == "CELL_PHONE":

#             phone_detected = True

#             phone_detections.append(detection)

#         elif label == "BOOK":

#             book_detected = True

#             book_detections.append(detection)

#         elif label == "PERSON":

#             person_detections.append(detection)

#     if len(person_detections) > 1:
#         extra_person_detected = True

#     return {
#         "phone_detected": phone_detected,
#         "book_detected": book_detected,
#         "extra_person_detected": extra_person_detected,
#         "phone_detections": phone_detections,
#         "book_detections": book_detections,
#         "person_detections": person_detections,
#     }


# def initialize_proctoring_pipeline(
#     session,
# ):
#     camera = None

#     microphone = None

#     audio_device_manager = None

#     voice_activity_detector = None

#     audio_monitor = None

#     voice_incident_recorder = None

#     audio_event_queue = None

#     face_detector = None

#     face_landmarker = None

#     gaze_tracker = None

#     head_tracker = None

#     pose_landmarker = None

#     posture_monitor = None

#     object_detector = None

#     evidence_store = None

#     anomaly_manager = None

#     proctoring_api = None

#     try:
#         print()

#         print("[PROCTOR] Initializing native proctoring hardware...")

#         print("[CAMERA] Starting camera...")

#         camera = open_camera()

#         print("[CAMERA] Camera opened successfully.")

#         print("[MICROPHONE] Discovering microphone devices...")

#         audio_device_manager = AudioDeviceManager()

#         microphone_selection = audio_device_manager.select_default_microphone()

#         if not microphone_selection.get(
#             "success",
#             False,
#         ):
#             raise RuntimeError(
#                 "No valid physical microphone could be selected. "
#                 f"Reason: "
#                 f"{microphone_selection.get('reason', 'UNKNOWN')}"
#             )

#         selected_microphone = microphone_selection["device"]

#         print(
#             "[MICROPHONE] Selected and validated: "
#             f"{selected_microphone.get('name')} "
#             f"| index="
#             f"{selected_microphone.get('index')} "
#             f"| sample_rate="
#             f"{selected_microphone.get('sample_rate')}"
#         )

#         print("[VOICE] Initializing voice activity detector...")

#         voice_activity_detector = VoiceActivityDetector(
#             frame_duration_ms=30,
#             required_voice_duration=VOICE_TRIGGER_SECONDS,
#             aggressiveness=1,
#             calibration_seconds=1.0,
#             smoothing_window_seconds=VOICE_SMOOTHING_WINDOW_SECONDS,
#             minimum_voice_ratio=0.40,
#             silence_reset_seconds=VOICE_DETECTOR_SILENCE_RESET_SECONDS,
#             whisper_noise_margin_db=6.0,
#             whisper_absolute_floor_db=-58.0,
#         )

#         print("[VOICE] Voice activity detector initialized.")

#         audio_event_queue = queue.Queue()

#         print("[MEDIAPIPE FACE DETECTOR] Loading face detector...")

#         face_detector = MediaPipeFaceDetector()

#         print("[MEDIAPIPE FACE DETECTOR] Face detector loaded successfully.")

#         print("[FACE LANDMARKER] Loading MediaPipe Face Landmarker...")

#         face_landmarker = FaceLandmarker()

#         print("[FACE LANDMARKER] MediaPipe model loaded successfully.")

#         print("[GAZE] Initializing gaze tracker...")

#         gaze_tracker = GazeTracker()

#         print("[GAZE] Gaze tracker initialized.")

#         print("[HEAD] Initializing head tracker...")

#         head_tracker = HeadTracker()

#         print("[HEAD] Head tracker initialized.")

#         print("[POSE] Loading MediaPipe Pose Landmarker...")

#         pose_landmarker = PoseLandmarker()

#         print("[POSE] Pose Landmarker loaded successfully.")

#         print("[POSTURE] Initializing posture monitor...")

#         posture_monitor = PostureMonitor()

#         print("[POSTURE] Posture monitor initialized.")

#         print("[YOLO26] Loading object detector...")

#         object_detector = YOLO26ObjectDetector()

#         print("[YOLO26] Object detector loaded successfully.")

#         print("[EVIDENCE] Initializing evidence store...")

#         real_evidence_store = EvidenceStore(
#             student_id=session.get(
#                 "student_id",
#                 session.get(
#                     "user_id",
#                     "local_test",
#                 ),
#             ),
#             exam_id=session.get(
#                 "test_id",
#                 "local_test",
#             ),
#             schedule_id=session.get(
#                 "schedule_id",
#                 "local_test",
#             ),
#             session_id=session.get(
#                 "proctor_session_id",
#                 "local_test",
#             ),
#         )

#         evidence_store = DeferredAudioEvidenceStore(real_evidence_store)

#         print(
#             "[EVIDENCE] Evidence store initialized. "
#             "Image evidence saves immediately; VOICE_DETECTED uses an "
#             "immediate socket marker and saves the complete WAV when the "
#             "voice incident ends."
#         )

#         print("[ANOMALY] Initializing anomaly manager...")

#         anomaly_manager = AnomalyManager(evidence_store=evidence_store)

#         configure_voice_anomaly_for_production(anomaly_manager)

#         print("[ANOMALY] Anomaly manager initialized.")

#         voice_incident_recorder = VoiceIncidentEvidenceRecorder(
#             pre_roll_seconds=VOICE_EVIDENCE_PRE_ROLL_SECONDS,
#             spool_memory_limit_bytes=VOICE_EVIDENCE_SPOOL_MEMORY_BYTES,
#         )

#         # Start the audio monitor only after the heavy vision models and
#         # AnomalyManager are ready. The monitor preserves the original PCM
#         # stream for evidence while the VAD can independently use its
#         # detector-compatible processing path.
#         print("[AUDIO] Starting audio monitor...")

#         audio_monitor = IncidentRecordingAudioMonitor(
#             device_manager=audio_device_manager,
#             voice_detector=voice_activity_detector,
#             event_callback=audio_event_queue.put,
#             device_poll_interval=2.0,
#             evidence_buffer_seconds=8.0,
#             reconnect_interval=2.0,
#             voice_incident_recorder=voice_incident_recorder,
#         )

#         if not audio_monitor.start():
#             raise RuntimeError("Unable to start audio monitor.")

#         microphone = audio_monitor

#         print("[AUDIO] Audio monitor started successfully.")

#         print("[API] Initializing proctoring API...")

#         proctoring_api = ProctoringAPI(token=session.get("raw_token"))

#         print("[API] Proctoring API initialized.")

#         print()

#         print("[PROCTOR] Native proctoring pipeline " "initialized successfully.")

#         return {
#             "camera": camera,
#             "microphone": microphone,
#             "audio_device_manager": audio_device_manager,
#             "voice_activity_detector": voice_activity_detector,
#             "audio_monitor": audio_monitor,
#             "voice_incident_recorder": voice_incident_recorder,
#             "audio_event_queue": audio_event_queue,
#             "audio_anomaly_result": None,
#             "audio_tracking_prepared": False,
#             "audio_worker_thread": None,
#             "audio_worker_stop_event": threading.Event(),
#             "anomaly_manager_lock": threading.RLock(),
#             "face_detector": face_detector,
#             "face_landmarker": face_landmarker,
#             "gaze_tracker": gaze_tracker,
#             "head_tracker": head_tracker,
#             "pose_landmarker": pose_landmarker,
#             "posture_monitor": posture_monitor,
#             "object_detector": object_detector,
#             "evidence_store": evidence_store,
#             "anomaly_manager": anomaly_manager,
#             "proctoring_api": proctoring_api,
#             "proctor_socket": None,
#             "process_monitor": None,
#             "pending_violations": [],
#             "pending_violations_lock": threading.RLock(),
#             "final_evidence_flush_lock": threading.RLock(),
#             "shutdown_requested_event": threading.Event(),
#             "final_evidence_flush_completed_event": threading.Event(),
#             "shutdown_reason": None,
#         }

#     except Exception:
#         cleanup_proctoring_pipeline(
#             camera=camera,
#             microphone=microphone,
#             face_detector=face_detector,
#             face_landmarker=face_landmarker,
#             gaze_tracker=gaze_tracker,
#             head_tracker=head_tracker,
#             pose_landmarker=pose_landmarker,
#             posture_monitor=posture_monitor,
#             object_detector=object_detector,
#             evidence_store=evidence_store,
#             anomaly_manager=anomaly_manager,
#             proctoring_api=proctoring_api,
#             audio_monitor=audio_monitor,
#             voice_incident_recorder=voice_incident_recorder,
#         )

#         raise


# def cleanup_proctoring_pipeline(
#     camera=None,
#     microphone=None,
#     face_detector=None,
#     face_landmarker=None,
#     gaze_tracker=None,
#     head_tracker=None,
#     pose_landmarker=None,
#     posture_monitor=None,
#     object_detector=None,
#     evidence_store=None,
#     anomaly_manager=None,
#     proctoring_api=None,
#     audio_monitor=None,
#     voice_incident_recorder=None,
# ):
#     if audio_monitor is not None:
#         try:
#             audio_monitor.close()

#         except Exception as error:
#             print(
#                 "[AUDIO] Cleanup error:",
#                 error,
#             )

#     if voice_incident_recorder is not None:
#         try:
#             voice_incident_recorder.close()

#         except Exception as error:
#             print(
#                 "[AUDIO] Voice incident recorder cleanup error:",
#                 error,
#             )

#     if anomaly_manager is not None:
#         try:
#             anomaly_manager.close()

#         except Exception as error:
#             print(
#                 "[ANOMALY] Cleanup error:",
#                 error,
#             )

#     if evidence_store is not None:
#         try:
#             evidence_store.close()

#         except Exception as error:
#             print(
#                 "[EVIDENCE] Cleanup error:",
#                 error,
#             )

#     if posture_monitor is not None:
#         try:
#             posture_monitor.reset()

#         except Exception as error:
#             print(
#                 "[POSTURE] Cleanup error:",
#                 error,
#             )

#     if microphone is not None and microphone is not audio_monitor:
#         try:
#             stop_microphone(microphone)

#         except Exception as error:
#             print(
#                 "[MICROPHONE] Cleanup error:",
#                 error,
#             )

#     if camera is not None:
#         try:
#             camera.release()

#         except Exception as error:
#             print(
#                 "[CAMERA] Cleanup error:",
#                 error,
#             )

#     if object_detector is not None:
#         try:
#             object_detector.close()

#         except Exception as error:
#             print(
#                 "[YOLO26] Cleanup error:",
#                 error,
#             )

#     if pose_landmarker is not None:
#         try:
#             pose_landmarker.close()

#         except Exception as error:
#             print(
#                 "[POSE] Cleanup error:",
#                 error,
#             )

#     if gaze_tracker is not None:
#         try:
#             gaze_tracker.close()

#         except Exception as error:
#             print(
#                 "[GAZE] Cleanup error:",
#                 error,
#             )

#     if head_tracker is not None:
#         try:
#             head_tracker.close()

#         except Exception as error:
#             print(
#                 "[HEAD] Cleanup error:",
#                 error,
#             )

#     if face_landmarker is not None:
#         try:
#             face_landmarker.close()

#         except Exception as error:
#             print(
#                 "[FACE LANDMARKER] Cleanup error:",
#                 error,
#             )

#     if face_detector is not None:
#         try:
#             face_detector.close()

#         except Exception as error:
#             print(
#                 "[MEDIAPIPE FACE DETECTOR] Cleanup error:",
#                 error,
#             )


# def queue_api_violations(
#     anomaly_results,
#     pending_violations,
# ):
#     if pending_violations is None:
#         pending_violations = []

#     for (
#         event_type,
#         result,
#     ) in anomaly_results.items():

#         if not isinstance(
#             result,
#             dict,
#         ):
#             continue

#         api_violation = result.get("api_violation")

#         if not api_violation:
#             continue

#         if not isinstance(
#             api_violation,
#             dict,
#         ):
#             continue

#         pending_violations.append(dict(api_violation))

#     return pending_violations


# def send_pending_violations(
#     proctoring_api,
#     pending_violations,
#     proctor_socket=None,
#     require_all_evidence_files=False,
# ):
#     """
#     Send queued proctoring violations while preserving
#     the exact relationship between each violation and
#     its evidence file.

#     The violation's local file_path is intentionally
#     removed from the JSON payload. Instead, evidence_files
#     contains an explicit violation_index -> file path mapping.

#     This prevents evidence paths from being attached to the
#     wrong violation when some violations have no evidence.

#     Backward compatibility:
#     - proctor_socket remains an optional argument so existing
#       callers do not need to change.
#     - Existing two-argument and three-argument calls continue
#       to work unchanged.
#     - require_all_evidence_files defaults to False so normal periodic
#       submission behavior remains unchanged.

#     Real-time behavior:
#     - Socket.IO notification is NOT emitted from this function.
#     - AnomalyManager emits the real-time event immediately after
#       local image/audio evidence capture.
#     - REST persistence remains independently retryable here.
#     """

#     if proctoring_api is None or not pending_violations:
#         return pending_violations

#     violations = []

#     evidence_files = []

#     missing_evidence_files = []

#     for violation in pending_violations:

#         if not isinstance(
#             violation,
#             dict,
#         ):
#             continue

#         violation_copy = dict(violation)

#         file_path = violation_copy.pop(
#             "file_path",
#             None,
#         )

#         violation_index = len(violations)

#         violations.append(violation_copy)

#         if not file_path:
#             continue

#         file_path_string = str(file_path).strip()

#         if not file_path_string:
#             continue

#         if not os.path.isfile(file_path_string):
#             print(
#                 "[API] Evidence file is missing " "for pending violation:",
#                 file_path_string,
#             )

#             missing_evidence_files.append(file_path_string)

#             continue

#         evidence_files.append(
#             {
#                 "violation_index": violation_index,
#                 "path": file_path_string,
#             }
#         )

#         print(
#             "[API] Evidence mapping prepared "
#             f"| violation_index={violation_index} "
#             f"| path={file_path_string}"
#         )

#     if require_all_evidence_files and missing_evidence_files:
#         print(
#             "[API] Strict evidence submission blocked. "
#             f"Missing evidence files={len(missing_evidence_files)}"
#         )

#         return pending_violations

#     if not violations:
#         return []

#     try:
#         print(
#             "[API] Preparing violation batch "
#             f"| violations={len(violations)} "
#             f"| evidence_files={len(evidence_files)}"
#         )

#         result = proctoring_api.send_violations(
#             violations=violations,
#             evidence_files=evidence_files,
#         )

#     except Exception as error:
#         print("[API] Violation submission " f"error: {error}")

#         return pending_violations

#     if result.get(
#         "success",
#         False,
#     ):
#         print("[API] Violation batch sent " "successfully. " f"Count={len(violations)}")

#         return []

#     reason = result.get("reason")

#     if reason == "API_COOLDOWN":
#         return pending_violations

#     print("[API] Violation batch was not " "sent.")

#     if reason:
#         print(f"[API] Reason: {reason}")

#     return pending_violations


# def request_final_evidence_flush(
#     pipeline,
#     reason,
# ):
#     if not isinstance(
#         pipeline,
#         dict,
#     ):
#         return False

#     reason_text = str(reason or "SESSION_FINALIZATION").strip()

#     if not reason_text:
#         reason_text = "SESSION_FINALIZATION"

#     pipeline["shutdown_reason"] = reason_text

#     shutdown_event = pipeline.get("shutdown_requested_event")

#     if shutdown_event is not None and hasattr(
#         shutdown_event,
#         "set",
#     ):
#         shutdown_event.set()

#     print("[PROCTOR] Final evidence flush requested " f"| reason={reason_text}")

#     return True


# def wait_for_final_evidence_flush(
#     pipeline,
#     reason,
# ):
#     if not request_final_evidence_flush(
#         pipeline=pipeline,
#         reason=reason,
#     ):
#         return False

#     completed_event = pipeline.get("final_evidence_flush_completed_event")

#     if completed_event is None or not hasattr(
#         completed_event,
#         "wait",
#     ):
#         return False

#     print(
#         "[PROCTOR] Waiting for every captured evidence item "
#         "to be persisted before termination..."
#     )

#     while not completed_event.wait(timeout=0.25):
#         pass

#     print(
#         "[PROCTOR] Final evidence persistence confirmed "
#         f"| reason={pipeline.get('shutdown_reason')}"
#     )

#     return True


# def flush_all_pending_evidence_until_empty(
#     pipeline,
#     reason=None,
# ):
#     if not isinstance(
#         pipeline,
#         dict,
#     ):
#         return True

#     flush_lock = pipeline.get("final_evidence_flush_lock")

#     if flush_lock is None:
#         flush_lock = threading.RLock()

#         pipeline["final_evidence_flush_lock"] = flush_lock

#     pending_lock = pipeline.get("pending_violations_lock")

#     if pending_lock is None:
#         pending_lock = threading.RLock()

#         pipeline["pending_violations_lock"] = pending_lock

#     completed_event = pipeline.get("final_evidence_flush_completed_event")

#     if completed_event is None:
#         completed_event = threading.Event()

#         pipeline["final_evidence_flush_completed_event"] = completed_event

#     reason_text = str(
#         reason or pipeline.get("shutdown_reason") or "SESSION_FINALIZATION"
#     ).strip()

#     if not reason_text:
#         reason_text = "SESSION_FINALIZATION"

#     pipeline["shutdown_reason"] = reason_text

#     attempt = 0

#     with flush_lock:
#         while True:
#             with pending_lock:
#                 pending_violations = pipeline.get(
#                     "pending_violations",
#                     [],
#                 )

#                 if pending_violations is None:
#                     pending_violations = []

#                     pipeline["pending_violations"] = pending_violations

#                 if not pending_violations:
#                     completed_event.set()

#                     print(
#                         "[API] Final evidence flush complete "
#                         f"| reason={reason_text} "
#                         "| pending=0"
#                     )

#                     return True

#                 proctoring_api = pipeline.get("proctoring_api")

#                 proctor_socket = pipeline.get("proctor_socket")

#                 if proctoring_api is not None:
#                     attempt += 1

#                     print(
#                         "[API] Final evidence flush attempt "
#                         f"{attempt} "
#                         f"| reason={reason_text} "
#                         f"| pending={len(pending_violations)}"
#                     )

#                     try:
#                         remaining_violations = send_pending_violations(
#                             proctoring_api=proctoring_api,
#                             pending_violations=pending_violations,
#                             proctor_socket=proctor_socket,
#                             require_all_evidence_files=True,
#                         )

#                     except Exception as error:
#                         print(
#                             "[API] Final evidence flush attempt failed:",
#                             error,
#                         )

#                         remaining_violations = pending_violations

#                     pipeline["pending_violations"] = remaining_violations

#                     if not remaining_violations:
#                         completed_event.set()

#                         print(
#                             "[API] Every queued violation and evidence file "
#                             "was persisted successfully "
#                             f"| reason={reason_text}"
#                         )

#                         return True

#                 else:
#                     print(
#                         "[API] Proctoring API unavailable during final "
#                         "evidence flush. Retrying before kiosk shutdown."
#                     )

#             time.sleep(FINAL_EVIDENCE_RETRY_DELAY_SECONDS)


# def empty_voice_anomaly_result():
#     return {
#         "event_type": "VOICE_DETECTED",
#         # `active` means anomaly-active. Human speech before the cumulative
#         # threshold is TRACKING only and deliberately remains inactive.
#         "active": False,
#         "confirmed": False,
#         "captured": False,
#         "duration": 0.0,
#         "required_duration": VOICE_TRIGGER_SECONDS,
#         "cooldown": 0.0,
#         "cooldown_remaining": 0.0,
#         "evidence": None,
#         "api_violation": None,
#         "incident_duration_seconds": 0.0,
#         "cumulative_voice_duration_seconds": 0.0,
#         "silence_duration_seconds": 0.0,
#         "short_gap_grace_seconds": VOICE_SHORT_GAP_GRACE_SECONDS,
#         "incident_end_silence_seconds": VOICE_INCIDENT_END_SILENCE_SECONDS,
#         "completed_audio_evidence": None,
#         "_voice_incident_active": False,
#         "_voice_incident_started_at": None,
#         "_voice_last_activity_at": None,
#         "_voice_silence_started_at": None,
#         "_voice_speech_active": False,
#         "_voice_incident_captured": False,
#         "_voice_incident_number": 0,
#         "_voice_core_incident_events_seen": False,
#         "_voice_incident_client_captured_at": None,
#         "_voice_incident_initial_metadata": {},
#     }


# def configure_voice_anomaly_for_production(
#     anomaly_manager,
# ):
#     """
#     Match the validated test_v2 VOICE_DETECTED confirmation behavior.

#     VoiceActivityDetector owns:
#     - human-speech classification,
#     - cumulative speech accumulation,
#     - the 1.5-second confirmation threshold,
#     - the 5-second continuous-silence incident boundary.

#     Therefore AnomalyManager must accept the already-confirmed VOICE_DETECTED
#     event immediately instead of applying another multi-second confirmation.
#     """
#     rules = getattr(
#         anomaly_manager,
#         "rules",
#         None,
#     )

#     if not isinstance(
#         rules,
#         dict,
#     ):
#         print(
#             "[AUDIO] Warning: AnomalyManager rules are not exposed; "
#             "core-confirmed voice events will use the manager defaults."
#         )
#         return False

#     voice_rule = rules.get("VOICE_DETECTED")

#     if not isinstance(
#         voice_rule,
#         dict,
#     ):
#         print(
#             "[AUDIO] Warning: VOICE_DETECTED anomaly rule is unavailable; "
#             "core-confirmed voice events will use the manager defaults."
#         )
#         return False

#     # The cumulative speech threshold is already enforced by
#     # VoiceActivityDetector. Do not apply a second duration gate here.
#     voice_rule["duration"] = 0.0
#     voice_rule["minimum_audio_duration"] = 0.0
#     voice_rule["recovery_grace"] = 0.0
#     voice_rule["capture_once_per_incident"] = True

#     print(
#         "[AUDIO] VOICE_DETECTED uses cumulative human-speech confirmation "
#         f"| speech_threshold={VOICE_TRIGGER_SECONDS:.1f}s "
#         f"| incident_end_silence={VOICE_INCIDENT_END_SILENCE_SECONDS:.1f}s "
#         "| pause_time_excluded=True"
#     )

#     return True


# def _voice_incident_elapsed(
#     result,
#     now,
# ):
#     started_at = result.get("_voice_incident_started_at")

#     if started_at is None:
#         return 0.0

#     try:
#         return max(
#             0.0,
#             float(now) - float(started_at),
#         )

#     except (
#         TypeError,
#         ValueError,
#     ):
#         return 0.0


# def _voice_silence_elapsed(
#     result,
#     now,
# ):
#     silence_started_at = result.get("_voice_silence_started_at")

#     if silence_started_at is None:
#         return 0.0

#     try:
#         return max(
#             0.0,
#             float(now) - float(silence_started_at),
#         )

#     except (
#         TypeError,
#         ValueError,
#     ):
#         return 0.0


# def _start_voice_tracking_incident(
#     result,
#     now,
#     voice_incident_recorder=None,
#     incident_number=None,
#     core_event=False,
# ):
#     """
#     Start a logical voice incident without declaring a violation.

#     This mirrors test_v2: speech can be tracked before the cumulative
#     confirmation threshold is reached.
#     """
#     if result.get(
#         "_voice_incident_active",
#         False,
#     ):
#         if core_event:
#             result["_voice_core_incident_events_seen"] = True

#         return result

#     previous_number = int(
#         result.get(
#             "_voice_incident_number",
#             0,
#         )
#         or 0
#     )

#     if incident_number is None:
#         incident_number = previous_number + 1

#     else:
#         try:
#             incident_number = int(incident_number)

#         except (
#             TypeError,
#             ValueError,
#         ):
#             incident_number = previous_number + 1

#     result.update(
#         {
#             "active": False,
#             "confirmed": False,
#             "captured": False,
#             "duration": 0.0,
#             "required_duration": VOICE_TRIGGER_SECONDS,
#             "incident_duration_seconds": 0.0,
#             "cumulative_voice_duration_seconds": 0.0,
#             "silence_duration_seconds": 0.0,
#             "completed_audio_evidence": None,
#             "_voice_incident_active": True,
#             "_voice_incident_started_at": now,
#             "_voice_last_activity_at": now,
#             "_voice_silence_started_at": None,
#             "_voice_speech_active": True,
#             "_voice_incident_captured": False,
#             "_voice_incident_number": incident_number,
#             "_voice_incident_client_captured_at": None,
#             "_voice_incident_initial_metadata": {},
#         }
#     )

#     if core_event:
#         result["_voice_core_incident_events_seen"] = True

#     if voice_incident_recorder is not None:
#         try:
#             recorder_started = voice_incident_recorder.start()

#             if not recorder_started:
#                 print(
#                     "[AUDIO][VOICE EVIDENCE WARNING] "
#                     "Incident recorder could not start from pre-roll. "
#                     "Tracking will continue."
#                 )

#         except Exception as error:
#             print(
#                 "[AUDIO][VOICE EVIDENCE WARNING] " "Unable to start incident recorder:",
#                 error,
#             )

#     print(
#         "[AUDIO][VOICE TRACKING STARTED] "
#         f"incident={incident_number} "
#         f"| threshold={VOICE_TRIGGER_SECONDS:.1f}s cumulative speech"
#     )

#     return result


# def _refresh_voice_tracking_state(
#     result,
#     now,
# ):
#     if not result.get(
#         "_voice_incident_active",
#         False,
#     ):
#         result["silence_duration_seconds"] = 0.0
#         return result

#     silence_started_at = result.get("_voice_silence_started_at")

#     if silence_started_at is None:
#         result["silence_duration_seconds"] = 0.0

#     else:
#         try:
#             result["silence_duration_seconds"] = max(
#                 0.0,
#                 float(now) - float(silence_started_at),
#             )

#         except (
#             TypeError,
#             ValueError,
#         ):
#             result["silence_duration_seconds"] = 0.0

#     result["required_duration"] = VOICE_TRIGGER_SECONDS
#     result["short_gap_grace_seconds"] = VOICE_SHORT_GAP_GRACE_SECONDS
#     result["incident_end_silence_seconds"] = VOICE_INCIDENT_END_SILENCE_SECONDS

#     if not result.get(
#         "confirmed",
#         False,
#     ):
#         # Human speech is being tracked, but it has not yet accumulated enough
#         # actual speech time to be a violation.
#         result["active"] = False

#     else:
#         # After confirmation, natural pauses remain part of the same incident.
#         result["active"] = True

#     return result


# def _get_evidence_capture_timestamp(
#     evidence,
# ):
#     if not isinstance(
#         evidence,
#         dict,
#     ):
#         return None

#     event_payload = evidence.get("event")

#     if isinstance(
#         event_payload,
#         dict,
#     ):
#         captured_at = event_payload.get("captured_at")

#         if captured_at:
#             return captured_at

#     captured_at = evidence.get("client_captured_at")

#     if captured_at:
#         return captured_at

#     return None


# def _build_completed_voice_api_violation(
#     completed_evidence,
#     result,
#     incident_number,
#     incident_duration,
#     silence_elapsed,
#     recorded_audio,
#     forced_finalize=False,
#     finalize_reason=None,
# ):
#     if not isinstance(
#         completed_evidence,
#         dict,
#     ):
#         return None

#     file_path = completed_evidence.get("file_path") or completed_evidence.get(
#         "audio_path"
#     )

#     if not file_path:
#         return None

#     initial_metadata = result.get(
#         "_voice_incident_initial_metadata",
#         {},
#     )

#     if not isinstance(
#         initial_metadata,
#         dict,
#     ):
#         initial_metadata = {}

#     metadata = dict(initial_metadata)

#     cumulative_voice_duration = float(
#         result.get(
#             "cumulative_voice_duration_seconds",
#             result.get(
#                 "duration",
#                 0.0,
#             ),
#         )
#         or 0.0
#     )

#     metadata.update(
#         {
#             "incident_number": incident_number,
#             "incident_duration_seconds": round(
#                 incident_duration,
#                 3,
#             ),
#             "cumulative_voice_duration_seconds": round(
#                 cumulative_voice_duration,
#                 3,
#             ),
#             "confirmation_threshold_seconds": VOICE_TRIGGER_SECONDS,
#             "pause_time_excluded": True,
#             "continuous_silence_seconds": round(
#                 silence_elapsed,
#                 3,
#             ),
#             "recorded_audio_duration_seconds": (
#                 recorded_audio.get("duration_seconds")
#                 if isinstance(
#                     recorded_audio,
#                     dict,
#                 )
#                 else None
#             ),
#             "recording_started_on_incident_start": True,
#             "continuous_audio_evidence": True,
#             "evidence_write_deferred_until_incident_end": True,
#             "voice_incident_end_silence_seconds": (VOICE_INCIDENT_END_SILENCE_SECONDS),
#             "voice_evidence_pre_roll_seconds": (VOICE_EVIDENCE_PRE_ROLL_SECONDS),
#             "evidence_type": "audio",
#             "audio_sample_rate": completed_evidence.get("sample_rate"),
#             "audio_channels": completed_evidence.get(
#                 "channels",
#                 1,
#             ),
#             "audio_sample_width": completed_evidence.get(
#                 "sample_width",
#                 2,
#             ),
#             "sample_rate_change_detected": bool(
#                 recorded_audio.get(
#                     "sample_rate_change_detected",
#                     False,
#                 )
#                 if isinstance(
#                     recorded_audio,
#                     dict,
#                 )
#                 else False
#             ),
#             "forced_incident_finalize": bool(forced_finalize),
#         }
#     )

#     if finalize_reason:
#         metadata["voice_incident_finalize_reason"] = str(finalize_reason)

#     client_captured_at = result.get("_voice_incident_client_captured_at")

#     if not client_captured_at:
#         client_captured_at = _get_evidence_capture_timestamp(completed_evidence)

#     if not client_captured_at:
#         client_captured_at = datetime.now(timezone.utc).isoformat()

#     return {
#         "violation_type": "VOICE_DETECTED",
#         "client_captured_at": client_captured_at,
#         "metadata": metadata,
#         "file_path": str(file_path),
#     }


# def _update_audio_anomaly_with_lock(
#     anomaly_manager,
#     anomaly_manager_lock=None,
#     **kwargs,
# ):
#     if anomaly_manager_lock is None:
#         return anomaly_manager.update_audio(**kwargs)

#     with anomaly_manager_lock:
#         return anomaly_manager.update_audio(**kwargs)


# def _finalize_voice_incident(
#     result,
#     anomaly_manager,
#     now,
#     voice_incident_recorder=None,
#     evidence_store=None,
#     anomaly_manager_lock=None,
#     cumulative_voice_duration=None,
#     continuous_silence=None,
#     confirmed=None,
#     force=False,
#     finalize_reason=None,
#     ended_by_core=False,
# ):
#     """
#     Close one logical voice incident.

#     Unconfirmed tracking incidents are discarded without evidence/API/socket
#     violation creation. Confirmed incidents persist the held WAV and create the
#     final file-backed REST violation while the real-time socket notification has
#     already been emitted at confirmation time.
#     """
#     if not result.get(
#         "_voice_incident_active",
#         False,
#     ):
#         return (
#             result,
#             None,
#         )

#     incident_number = int(
#         result.get(
#             "_voice_incident_number",
#             0,
#         )
#         or 0
#     )

#     was_confirmed = bool(
#         result.get(
#             "confirmed",
#             False,
#         )
#         if confirmed is None
#         else confirmed
#     )

#     if cumulative_voice_duration is None:
#         cumulative_voice_duration = float(
#             result.get(
#                 "cumulative_voice_duration_seconds",
#                 result.get(
#                     "duration",
#                     0.0,
#                 ),
#             )
#             or 0.0
#         )

#     else:
#         cumulative_voice_duration = float(cumulative_voice_duration or 0.0)

#     if continuous_silence is None:
#         continuous_silence = _voice_silence_elapsed(
#             result,
#             now,
#         )

#     else:
#         continuous_silence = float(continuous_silence or 0.0)

#     result["cumulative_voice_duration_seconds"] = cumulative_voice_duration
#     result["duration"] = cumulative_voice_duration

#     incident_duration = _voice_incident_elapsed(
#         result,
#         now,
#     )

#     completed_evidence = None
#     completed_api_violation = None
#     recorded_audio = None

#     if was_confirmed:
#         if voice_incident_recorder is not None:
#             try:
#                 recorded_audio = voice_incident_recorder.stop()

#             except Exception as error:
#                 print(
#                     "[AUDIO][VOICE EVIDENCE STOP ERROR] "
#                     f"incident={incident_number} "
#                     f"| error={error}"
#                 )

#         should_persist_audio = bool(
#             result.get(
#                 "_voice_incident_captured",
#                 False,
#             )
#         )

#         if (
#             should_persist_audio
#             and isinstance(
#                 recorded_audio,
#                 dict,
#             )
#             and recorded_audio.get("pcm")
#             and evidence_store is not None
#         ):
#             persist_audio = getattr(
#                 evidence_store,
#                 "persist_audio",
#                 None,
#             )

#             if callable(persist_audio):
#                 evidence_metadata = {
#                     "incident_number": incident_number,
#                     "incident_duration_seconds": round(
#                         incident_duration,
#                         3,
#                     ),
#                     "cumulative_voice_duration_seconds": round(
#                         cumulative_voice_duration,
#                         3,
#                     ),
#                     "confirmation_threshold_seconds": VOICE_TRIGGER_SECONDS,
#                     "pause_time_excluded": True,
#                     "continuous_silence_seconds": round(
#                         continuous_silence,
#                         3,
#                     ),
#                     "recorded_audio_duration_seconds": recorded_audio.get(
#                         "duration_seconds"
#                     ),
#                     "recording_started_on_incident_start": True,
#                     "continuous_audio_evidence": True,
#                     "evidence_write_deferred_until_incident_end": True,
#                     "voice_incident_end_silence_seconds": (
#                         VOICE_INCIDENT_END_SILENCE_SECONDS
#                     ),
#                     "voice_evidence_pre_roll_seconds": (
#                         VOICE_EVIDENCE_PRE_ROLL_SECONDS
#                     ),
#                     "sample_rate_change_detected": bool(
#                         recorded_audio.get(
#                             "sample_rate_change_detected",
#                             False,
#                         )
#                     ),
#                     "forced_incident_finalize": bool(force),
#                     "ended_by_core_incident_event": bool(ended_by_core),
#                 }

#                 if finalize_reason:
#                     evidence_metadata["voice_incident_finalize_reason"] = str(
#                         finalize_reason
#                     )

#                 try:
#                     completed_evidence = persist_audio(
#                         pcm=recorded_audio["pcm"],
#                         sample_rate=recorded_audio["sample_rate"],
#                         channels=recorded_audio.get(
#                             "channels",
#                             1,
#                         ),
#                         sample_width=recorded_audio.get(
#                             "sample_width",
#                             2,
#                         ),
#                         event_type="VOICE_DETECTED",
#                         metadata=evidence_metadata,
#                     )

#                     if completed_evidence:
#                         completed_api_violation = _build_completed_voice_api_violation(
#                             completed_evidence=completed_evidence,
#                             result=result,
#                             incident_number=incident_number,
#                             incident_duration=incident_duration,
#                             silence_elapsed=continuous_silence,
#                             recorded_audio=recorded_audio,
#                             forced_finalize=force,
#                             finalize_reason=finalize_reason,
#                         )

#                         print(
#                             "[AUDIO][VOICE EVIDENCE SAVED] "
#                             f"incident={incident_number} "
#                             f"| cumulative_speech="
#                             f"{cumulative_voice_duration:.2f}s "
#                             f"| recorded_duration="
#                             f"{float(recorded_audio.get('duration_seconds', 0.0)):.2f}s "
#                             f"| path="
#                             f"{completed_evidence.get('audio_path')}"
#                         )

#                 except Exception as error:
#                     print(
#                         "[AUDIO][VOICE EVIDENCE SAVE ERROR] "
#                         f"incident={incident_number} "
#                         f"| error={error}"
#                     )

#         elif isinstance(
#             recorded_audio,
#             dict,
#         ) and recorded_audio.get("pcm"):
#             print(
#                 "[AUDIO][VOICE EVIDENCE NOT PERSISTED] "
#                 f"incident={incident_number} "
#                 "| anomaly evidence cooldown/capture-once did not arm "
#                 "a new evidence capture."
#             )

#         ended_result = _update_audio_anomaly_with_lock(
#             anomaly_manager=anomaly_manager,
#             anomaly_manager_lock=anomaly_manager_lock,
#             event_type="VOICE_DETECTED",
#             active=False,
#             audio_evidence=None,
#             metadata={
#                 "incident_number": incident_number,
#                 "cumulative_voice_duration_seconds": round(
#                     cumulative_voice_duration,
#                     3,
#                 ),
#                 "confirmation_threshold_seconds": VOICE_TRIGGER_SECONDS,
#                 "pause_time_excluded": True,
#                 "continuous_silence_seconds": round(
#                     continuous_silence,
#                     3,
#                 ),
#                 "ended_by_core_incident_event": bool(ended_by_core),
#                 "forced_incident_finalize": bool(force),
#                 "voice_incident_finalize_reason": (
#                     str(finalize_reason) if finalize_reason else None
#                 ),
#             },
#         )

#     else:
#         # Tracking never reached the cumulative speech threshold, therefore it
#         # must not become an anomaly and must not persist evidence.
#         if voice_incident_recorder is not None:
#             try:
#                 voice_incident_recorder.discard()

#             except Exception:
#                 pass

#         ended_result = None

#     fresh = empty_voice_anomaly_result()
#     fresh["_voice_incident_number"] = incident_number
#     fresh["_voice_core_incident_events_seen"] = bool(
#         result.get(
#             "_voice_core_incident_events_seen",
#             False,
#         )
#         or ended_by_core
#     )

#     if isinstance(
#         ended_result,
#         dict,
#     ):
#         fresh["cooldown"] = float(
#             ended_result.get(
#                 "cooldown",
#                 0.0,
#             )
#             or 0.0
#         )

#         fresh["cooldown_remaining"] = float(
#             ended_result.get(
#                 "cooldown_remaining",
#                 0.0,
#             )
#             or 0.0
#         )

#     fresh["completed_audio_evidence"] = completed_evidence

#     print(
#         "[AUDIO][VOICE INCIDENT ENDED] "
#         f"incident={incident_number} "
#         f"| cumulative_speech={cumulative_voice_duration:.2f}s "
#         f"| continuous_silence={continuous_silence:.2f}s "
#         f"| anomaly={was_confirmed} "
#         f"| forced={bool(force)}"
#     )

#     return (
#         fresh,
#         completed_api_violation,
#     )


# def _legacy_finish_voice_incident_if_needed(
#     result,
#     anomaly_manager,
#     now,
#     voice_incident_recorder=None,
#     evidence_store=None,
#     anomaly_manager_lock=None,
# ):
#     """
#     Local 5-second silence safeguard for the validated test_v2 incident model.

#     AudioMonitor may emit VOICE_INCIDENT_STARTED/ENDED, but production must not
#     depend exclusively on the final INCIDENT_ENDED event. Once speech pauses,
#     the local state machine tracks continuous silence itself and closes the
#     incident after VOICE_INCIDENT_END_SILENCE_SECONDS.

#     This preserves test_v2 behavior even if a core incident-end event is delayed
#     or missed:
#     - speech resumes before 5 seconds -> same incident continues;
#     - cumulative human-speech duration is preserved;
#     - silence is never added to the speech total;
#     - 5 continuous seconds without speech -> incident closes.
#     """
#     result = _refresh_voice_tracking_state(
#         result,
#         now,
#     )

#     if not result.get(
#         "_voice_incident_active",
#         False,
#     ):
#         return (
#             result,
#             None,
#         )

#     silence_elapsed = float(
#         result.get(
#             "silence_duration_seconds",
#             0.0,
#         )
#         or 0.0
#     )

#     if silence_elapsed < VOICE_INCIDENT_END_SILENCE_SECONDS:
#         return (
#             result,
#             None,
#         )

#     return _finalize_voice_incident(
#         result=result,
#         anomaly_manager=anomaly_manager,
#         now=now,
#         voice_incident_recorder=voice_incident_recorder,
#         evidence_store=evidence_store,
#         anomaly_manager_lock=anomaly_manager_lock,
#         continuous_silence=silence_elapsed,
#         force=False,
#         ended_by_core=False,
#     )


# def _finish_voice_incident_if_silent(
#     result,
#     anomaly_manager,
#     now,
#     voice_incident_recorder=None,
#     evidence_store=None,
#     anomaly_manager_lock=None,
#     force=False,
#     finalize_reason=None,
# ):
#     """
#     Backward-compatible wrapper retained for existing callers.

#     Normal operation delegates to the legacy silence fallback only when the
#     installed AudioMonitor does not provide logical incident boundary events.
#     Shutdown force-finalization always closes the currently tracked incident.
#     """
#     if force:
#         return _finalize_voice_incident(
#             result=result,
#             anomaly_manager=anomaly_manager,
#             now=now,
#             voice_incident_recorder=voice_incident_recorder,
#             evidence_store=evidence_store,
#             anomaly_manager_lock=anomaly_manager_lock,
#             force=True,
#             finalize_reason=finalize_reason,
#             ended_by_core=False,
#         )

#     return _legacy_finish_voice_incident_if_needed(
#         result=result,
#         anomaly_manager=anomaly_manager,
#         now=now,
#         voice_incident_recorder=voice_incident_recorder,
#         evidence_store=evidence_store,
#         anomaly_manager_lock=anomaly_manager_lock,
#     )


# def process_audio_events(
#     audio_event_queue,
#     anomaly_manager,
#     current_result=None,
#     tracking_enabled=True,
#     anomaly_manager_lock=None,
#     voice_incident_recorder=None,
#     evidence_store=None,
#     force_finalize=False,
#     finalize_reason=None,
# ):
#     """
#     Production version of the validated test_v2 voice state machine.

#     Backward compatibility:
#     - Existing positional arguments remain valid.
#     - Recorder/evidence/finalization arguments remain optional.
#     - Return value remains (result, new_api_violations).

#     Detection behavior:
#     - Proper human speech starts TRACKING, not a violation.
#     - Only actual human-speech time contributes to the cumulative threshold.
#     - Pause/silence time contributes zero seconds.
#     - Speech returning before 5 continuous seconds of silence stays in the same
#       logical incident and keeps the previous cumulative speech total.
#     - VOICE_DETECTED is confirmed only after 1.5 seconds cumulative speech.
#     - Once confirmed, short pauses do not deactivate the violation.
#     - The logical incident closes after 5 continuous seconds without speech.

#     Production evidence behavior:
#     - Original PCM starts recording when the logical incident starts.
#     - At confirmation, AnomalyManager gets the lightweight deferred-audio marker
#       so the Socket.IO violation can be emitted immediately.
#     - The placeholder marker is NOT queued to REST.
#     - When the incident ends, the complete WAV is persisted and the final
#       file-backed violation is queued for REST.
#     """
#     result = dict(current_result or empty_voice_anomaly_result())

#     new_api_violations = []

#     if audio_event_queue is None or anomaly_manager is None:
#         return (
#             result,
#             new_api_violations,
#         )

#     if not tracking_enabled:
#         return (
#             result,
#             new_api_violations,
#         )

#     now = time.monotonic()

#     (
#         result,
#         completed_api_violation,
#     ) = _finish_voice_incident_if_silent(
#         result=result,
#         anomaly_manager=anomaly_manager,
#         now=now,
#         voice_incident_recorder=voice_incident_recorder,
#         evidence_store=evidence_store,
#         anomaly_manager_lock=anomaly_manager_lock,
#         force=False,
#     )

#     if isinstance(
#         completed_api_violation,
#         dict,
#     ):
#         new_api_violations.append(dict(completed_api_violation))

#     while True:
#         try:
#             payload = audio_event_queue.get_nowait()

#         except queue.Empty:
#             break

#         if not isinstance(
#             payload,
#             dict,
#         ):
#             continue

#         event_type = (
#             str(
#                 payload.get(
#                     "event_type",
#                     "",
#                 )
#             )
#             .upper()
#             .strip()
#         )

#         now = time.monotonic()

#         if event_type == "VOICE_INCIDENT_STARTED":
#             result = _start_voice_tracking_incident(
#                 result=result,
#                 now=now,
#                 voice_incident_recorder=voice_incident_recorder,
#                 incident_number=payload.get("incident_number"),
#                 core_event=True,
#             )

#             continue

#         if event_type == "VOICE_ACTIVITY_STARTED":
#             if not result.get(
#                 "_voice_incident_active",
#                 False,
#             ):
#                 result = _start_voice_tracking_incident(
#                     result=result,
#                     now=now,
#                     voice_incident_recorder=voice_incident_recorder,
#                     incident_number=payload.get("incident_number"),
#                     core_event=False,
#                 )

#             result["_voice_speech_active"] = True
#             result["_voice_last_activity_at"] = now
#             result["_voice_silence_started_at"] = None
#             result["silence_duration_seconds"] = 0.0

#             continue

#         if event_type == "VOICE_ACTIVITY_ENDED":
#             if result.get(
#                 "_voice_incident_active",
#                 False,
#             ):
#                 result["_voice_speech_active"] = False

#                 if result.get("_voice_silence_started_at") is None:
#                     result["_voice_silence_started_at"] = now

#                     print(
#                         "[AUDIO][VOICE PAUSE] "
#                         "Speech stopped; cumulative speech is preserved. "
#                         f"Waiting {VOICE_INCIDENT_END_SILENCE_SECONDS:.1f}s "
#                         "of continuous silence before ending the incident."
#                     )

#                 result = _refresh_voice_tracking_state(
#                     result,
#                     now,
#                 )

#             continue

#         if event_type == "VOICE_DETECTED":
#             if not result.get(
#                 "_voice_incident_active",
#                 False,
#             ):
#                 result = _start_voice_tracking_incident(
#                     result=result,
#                     now=now,
#                     voice_incident_recorder=voice_incident_recorder,
#                     incident_number=payload.get("incident_number"),
#                     core_event=False,
#                 )

#             cumulative_voice_duration = float(
#                 payload.get(
#                     "cumulative_voice_duration_seconds",
#                     payload.get(
#                         "voice_duration_seconds",
#                         VOICE_TRIGGER_SECONDS,
#                     ),
#                 )
#                 or 0.0
#             )

#             result["cumulative_voice_duration_seconds"] = cumulative_voice_duration

#             result["incident_duration_seconds"] = cumulative_voice_duration

#             result["duration"] = cumulative_voice_duration
#             result["_voice_last_activity_at"] = now
#             result["_voice_silence_started_at"] = None
#             result["_voice_speech_active"] = True
#             result["silence_duration_seconds"] = 0.0

#             audio_evidence = payload.get("evidence_audio")

#             metadata = {
#                 key: value
#                 for (
#                     key,
#                     value,
#                 ) in payload.items()
#                 if key
#                 not in {
#                     "event_type",
#                     "evidence_audio",
#                 }
#             }

#             metadata.update(
#                 {
#                     "incident_number": result.get(
#                         "_voice_incident_number",
#                         0,
#                     ),
#                     "cumulative_voice_duration_seconds": round(
#                         cumulative_voice_duration,
#                         3,
#                     ),
#                     "confirmation_threshold_seconds": VOICE_TRIGGER_SECONDS,
#                     "incident_end_silence_seconds": (
#                         VOICE_INCIDENT_END_SILENCE_SECONDS
#                     ),
#                     "pause_time_excluded": True,
#                     "continuous_audio_evidence": True,
#                     "evidence_write_deferred_until_incident_end": True,
#                 }
#             )

#             manager_result = _update_audio_anomaly_with_lock(
#                 anomaly_manager=anomaly_manager,
#                 anomaly_manager_lock=anomaly_manager_lock,
#                 event_type="VOICE_DETECTED",
#                 active=True,
#                 audio_evidence=audio_evidence,
#                 metadata=metadata,
#             )

#             if not isinstance(
#                 manager_result,
#                 dict,
#             ):
#                 manager_result = {}

#             previous_incident_captured = bool(
#                 result.get(
#                     "_voice_incident_captured",
#                     False,
#                 )
#             )

#             previous_client_captured_at = result.get(
#                 "_voice_incident_client_captured_at"
#             )

#             previous_initial_metadata = result.get(
#                 "_voice_incident_initial_metadata",
#                 {},
#             )

#             if not isinstance(
#                 previous_initial_metadata,
#                 dict,
#             ):
#                 previous_initial_metadata = {}

#             immediate_api_violation = manager_result.get("api_violation")

#             if not previous_client_captured_at and isinstance(
#                 immediate_api_violation,
#                 dict,
#             ):
#                 previous_client_captured_at = immediate_api_violation.get(
#                     "client_captured_at"
#                 )

#             if not previous_client_captured_at:
#                 previous_client_captured_at = (
#                     payload.get("timestamp")
#                     or payload.get("captured_at")
#                     or datetime.now(timezone.utc).isoformat()
#                 )

#             if not previous_initial_metadata:
#                 previous_initial_metadata = dict(metadata)

#             # Keep the production-only tracking fields that are not returned by
#             # AnomalyManager.
#             manager_result["_voice_incident_active"] = True
#             manager_result["_voice_incident_started_at"] = result.get(
#                 "_voice_incident_started_at"
#             )
#             manager_result["_voice_last_activity_at"] = now
#             manager_result["_voice_silence_started_at"] = None
#             manager_result["_voice_speech_active"] = True
#             manager_result["_voice_incident_number"] = result.get(
#                 "_voice_incident_number",
#                 0,
#             )
#             manager_result["_voice_core_incident_events_seen"] = bool(
#                 result.get(
#                     "_voice_core_incident_events_seen",
#                     False,
#                 )
#             )
#             manager_result["_voice_incident_client_captured_at"] = (
#                 previous_client_captured_at
#             )
#             manager_result["_voice_incident_initial_metadata"] = (
#                 previous_initial_metadata
#             )
#             manager_result["_voice_incident_captured"] = bool(
#                 previous_incident_captured
#                 or manager_result.get(
#                     "captured",
#                     False,
#                 )
#             )

#             manager_result["active"] = True
#             manager_result["confirmed"] = True
#             manager_result["captured"] = bool(
#                 manager_result["_voice_incident_captured"]
#             )
#             manager_result["duration"] = cumulative_voice_duration
#             manager_result["required_duration"] = VOICE_TRIGGER_SECONDS
#             manager_result["incident_duration_seconds"] = cumulative_voice_duration
#             manager_result["cumulative_voice_duration_seconds"] = (
#                 cumulative_voice_duration
#             )
#             manager_result["silence_duration_seconds"] = 0.0
#             manager_result["short_gap_grace_seconds"] = VOICE_SHORT_GAP_GRACE_SECONDS
#             manager_result["incident_end_silence_seconds"] = (
#                 VOICE_INCIDENT_END_SILENCE_SECONDS
#             )

#             # Important: this immediate api_violation belongs to the real-time
#             # socket marker and intentionally has no final WAV path. It is NOT
#             # appended to REST. REST receives the file-backed violation when the
#             # incident is finalized.
#             result = manager_result

#             if result.get(
#                 "captured",
#                 False,
#             ):
#                 print(
#                     "[AUDIO][VOICE VIOLATION CONFIRMED] "
#                     f"incident={result.get('_voice_incident_number', 0)} "
#                     f"| cumulative_speech={cumulative_voice_duration:.2f}s "
#                     f"| threshold={VOICE_TRIGGER_SECONDS:.1f}s "
#                     "| socket event emitted immediately; "
#                     "continuous WAV recording remains active."
#                 )

#             else:
#                 print(
#                     "[AUDIO][VOICE VIOLATION CONFIRMED] "
#                     f"incident={result.get('_voice_incident_number', 0)} "
#                     f"| cumulative_speech={cumulative_voice_duration:.2f}s "
#                     f"| threshold={VOICE_TRIGGER_SECONDS:.1f}s "
#                     "| no new evidence/socket marker due to "
#                     "existing incident/cooldown."
#                 )

#             continue

#         if event_type == "VOICE_INCIDENT_ENDED":
#             result["_voice_core_incident_events_seen"] = True

#             cumulative_voice_duration = float(
#                 payload.get(
#                     "cumulative_voice_duration_seconds",
#                     result.get(
#                         "cumulative_voice_duration_seconds",
#                         0.0,
#                     ),
#                 )
#                 or 0.0
#             )

#             continuous_silence = float(
#                 payload.get(
#                     "continuous_silence_seconds",
#                     result.get(
#                         "silence_duration_seconds",
#                         0.0,
#                     ),
#                 )
#                 or 0.0
#             )

#             # Keep production behavior strictly aligned with test_v2's contract:
#             # an incident may end only after a full 5-second stretch with no
#             # further detected speech. If an early/stale core event arrives,
#             # remain in HOLD and let either resumed speech continue the same
#             # incident or the local silence safeguard close it at 5 seconds.
#             if continuous_silence < VOICE_INCIDENT_END_SILENCE_SECONDS:
#                 if result.get(
#                     "_voice_incident_active",
#                     False,
#                 ):
#                     result["_voice_speech_active"] = False

#                     if result.get("_voice_silence_started_at") is None:
#                         result["_voice_silence_started_at"] = now - max(
#                             0.0, continuous_silence
#                         )

#                     result = _refresh_voice_tracking_state(
#                         result,
#                         now,
#                     )

#                 continue

#             (
#                 result,
#                 completed_api_violation,
#             ) = _finalize_voice_incident(
#                 result=result,
#                 anomaly_manager=anomaly_manager,
#                 now=now,
#                 voice_incident_recorder=voice_incident_recorder,
#                 evidence_store=evidence_store,
#                 anomaly_manager_lock=anomaly_manager_lock,
#                 cumulative_voice_duration=cumulative_voice_duration,
#                 continuous_silence=continuous_silence,
#                 confirmed=bool(
#                     payload.get(
#                         "confirmed",
#                         result.get(
#                             "confirmed",
#                             False,
#                         ),
#                     )
#                 ),
#                 force=False,
#                 ended_by_core=True,
#             )

#             if isinstance(
#                 completed_api_violation,
#                 dict,
#             ):
#                 new_api_violations.append(dict(completed_api_violation))

#             continue

#         if event_type in {
#             "MIC_UNAVAILABLE",
#             "MIC_CHANGE_REQUIRED",
#             "MIC_STREAM_ERROR",
#             "MIC_DEVICE_LIST_CHANGED",
#             "DEFAULT_MIC_CHANGED",
#             "MIC_RECOVERED",
#             "MIC_DEVICE_CHANGED",
#             "MIC_CHANGE_FAILED",
#             "MIC_INPUT_OVERFLOW",
#             "AUDIO_MONITOR_ERROR",
#             "VOICE_DETECTION_ERROR",
#         }:
#             safe_payload = {
#                 key: value
#                 for (
#                     key,
#                     value,
#                 ) in payload.items()
#                 if key != "evidence_audio"
#             }

#             print(
#                 f"[AUDIO][{event_type}]",
#                 safe_payload,
#             )

#     now = time.monotonic()

#     (
#         result,
#         completed_api_violation,
#     ) = _finish_voice_incident_if_silent(
#         result=result,
#         anomaly_manager=anomaly_manager,
#         now=now,
#         voice_incident_recorder=voice_incident_recorder,
#         evidence_store=evidence_store,
#         anomaly_manager_lock=anomaly_manager_lock,
#         force=bool(force_finalize),
#         finalize_reason=finalize_reason,
#     )

#     if isinstance(
#         completed_api_violation,
#         dict,
#     ):
#         new_api_violations.append(dict(completed_api_violation))

#     result = _refresh_voice_tracking_state(
#         result,
#         time.monotonic(),
#     )

#     return (
#         result,
#         new_api_violations,
#     )


# def discard_pretracking_audio_events(
#     audio_event_queue,
# ):
#     """
#     Remove audio events produced before frontend tracking starts.

#     Important:
#     - Does NOT reset VoiceActivityDetector.
#     - Does NOT call AnomalyManager.
#     - Prevents pre-exam speech from becoming a violation.
#     - Keeps the live AudioMonitor/microphone running for device checks.
#     """
#     if audio_event_queue is None:
#         return 0

#     discarded = 0

#     while True:
#         try:
#             audio_event_queue.get_nowait()
#             discarded += 1

#         except queue.Empty:
#             break

#     return discarded


# def reset_audio_tracking_state(
#     pipeline,
# ):
#     """
#     Start production audio tracking from the same clean detector state used by
#     the working test_v2 flow.

#     Camera/microphone are intentionally opened before the secure exam page is
#     ready. Any voice activity produced during that bootstrap period must not
#     leak into the real assessment incident state.
#     """

#     audio_event_queue = pipeline.get("audio_event_queue")

#     # Remove everything emitted before the validated frontend tracking-start.
#     discard_pretracking_audio_events(audio_event_queue)

#     voice_incident_recorder = pipeline.get("voice_incident_recorder")

#     if voice_incident_recorder is not None:
#         try:
#             voice_incident_recorder.discard()
#         except Exception:
#             pass

#     audio_monitor = pipeline.get("audio_monitor")

#     if audio_monitor is not None:
#         clear_audio_buffer = getattr(
#             audio_monitor,
#             "clear_audio_buffer",
#             None,
#         )

#         if callable(clear_audio_buffer):
#             try:
#                 clear_audio_buffer()
#             except Exception:
#                 pass

#         voice_detector = getattr(
#             audio_monitor,
#             "voice_detector",
#             None,
#         )

#         reset_detector = getattr(
#             voice_detector,
#             "reset",
#             None,
#         )

#         if callable(reset_detector):
#             try:
#                 reset_detector(recalibrate=True)

#             except TypeError:
#                 reset_detector()

#         # AudioMonitor uses these edge-state flags to decide when to emit
#         # VOICE_ACTIVITY_STARTED / VOICE_DETECTED. Reset them alongside VAD so
#         # the first real assessment speech always begins a fresh incident.
#         try:
#             audio_monitor._last_voice_active = False
#         except Exception:
#             pass

#         try:
#             audio_monitor._last_confirmed = False
#         except Exception:
#             pass

#         set_status = getattr(
#             audio_monitor,
#             "_set_status",
#             None,
#         )

#         if callable(set_status):
#             try:
#                 set_status(
#                     calibrating=True,
#                     voice_active=False,
#                     voice_confirmed=False,
#                     voice_duration_seconds=0.0,
#                     cumulative_voice_duration_seconds=0.0,
#                     silence_duration_seconds=0.0,
#                     incident_active=False,
#                     vad_speech=False,
#                     whisper_candidate=False,
#                     detection_source=None,
#                 )
#             except Exception:
#                 pass

#     # Reset once more after detector reset so no stale callback event created
#     # during bootstrap can survive into the tracked assessment.
#     discard_pretracking_audio_events(audio_event_queue)

#     pipeline["audio_anomaly_result"] = empty_voice_anomaly_result()
#     pipeline["audio_tracking_prepared"] = True

#     print(
#         "[AUDIO] Tracking-start reset complete. "
#         "Voice detection begins from a clean incident state."
#     )


# def _append_audio_api_violations(
#     pipeline,
#     violations,
# ):
#     if not violations:
#         return

#     pending_violations_lock = pipeline.get("pending_violations_lock")

#     if pending_violations_lock is None:
#         pending_violations_lock = threading.RLock()
#         pipeline["pending_violations_lock"] = pending_violations_lock

#     with pending_violations_lock:
#         pending_violations = pipeline.get(
#             "pending_violations",
#             [],
#         )

#         if pending_violations is None:
#             pending_violations = []

#         pending_violations.extend(
#             dict(item)
#             for item in violations
#             if isinstance(
#                 item,
#                 dict,
#             )
#         )

#         pipeline["pending_violations"] = pending_violations


# def run_audio_tracking_worker(
#     pipeline,
# ):
#     """
#     Dedicated low-cost audio consumer.

#     The preview/test processes audio immediately from AudioMonitor's queue.
#     In production, doing that work inside the heavy camera/vision loop can
#     delay VOICE_DETECTED handling whenever vision inference or REST I/O takes
#     longer than expected. This worker preserves the same direct
#     AudioMonitor -> queue -> AnomalyManager path while running independently
#     from the vision loop.

#     The worker also owns full voice-incident finalization. On normal operation
#     it waits for the configured silence hold; on shutdown it force-finalizes
#     any active recording before the final REST evidence flush.

#     Tracking remains gated by tracking_start_event. Pre-tracking queue
#     cleanup is performed synchronously by before_tracking_start immediately
#     before the event is set.
#     """
#     audio_event_queue = pipeline.get("audio_event_queue")
#     anomaly_manager = pipeline.get("anomaly_manager")
#     tracking_start_event = pipeline.get("tracking_start_event")
#     anomaly_manager_lock = pipeline.get("anomaly_manager_lock")
#     voice_incident_recorder = pipeline.get("voice_incident_recorder")
#     evidence_store = pipeline.get("evidence_store")

#     if anomaly_manager_lock is None:
#         anomaly_manager_lock = threading.RLock()
#         pipeline["anomaly_manager_lock"] = anomaly_manager_lock

#     stop_event = pipeline.get("audio_worker_stop_event")

#     if stop_event is None:
#         stop_event = threading.Event()
#         pipeline["audio_worker_stop_event"] = stop_event

#     audio_anomaly_result = pipeline.get("audio_anomaly_result")

#     if not isinstance(
#         audio_anomaly_result,
#         dict,
#     ):
#         audio_anomaly_result = empty_voice_anomaly_result()
#         pipeline["audio_anomaly_result"] = audio_anomaly_result

#     print("[AUDIO] Dedicated real-time tracking worker started.")

#     try:
#         while not stop_event.is_set():
#             tracking_enabled = (
#                 True if tracking_start_event is None else tracking_start_event.is_set()
#             )

#             if not tracking_enabled:
#                 stop_event.wait(0.02)
#                 continue

#             (
#                 audio_anomaly_result,
#                 new_audio_violations,
#             ) = process_audio_events(
#                 audio_event_queue=audio_event_queue,
#                 anomaly_manager=anomaly_manager,
#                 current_result=audio_anomaly_result,
#                 tracking_enabled=True,
#                 anomaly_manager_lock=anomaly_manager_lock,
#                 voice_incident_recorder=voice_incident_recorder,
#                 evidence_store=evidence_store,
#             )

#             pipeline["audio_anomaly_result"] = audio_anomaly_result

#             _append_audio_api_violations(
#                 pipeline=pipeline,
#                 violations=new_audio_violations,
#             )

#             stop_event.wait(0.01)

#     finally:
#         tracking_enabled = (
#             True if tracking_start_event is None else tracking_start_event.is_set()
#         )

#         if tracking_enabled:
#             (
#                 audio_anomaly_result,
#                 final_audio_violations,
#             ) = process_audio_events(
#                 audio_event_queue=audio_event_queue,
#                 anomaly_manager=anomaly_manager,
#                 current_result=audio_anomaly_result,
#                 tracking_enabled=True,
#                 anomaly_manager_lock=anomaly_manager_lock,
#                 voice_incident_recorder=voice_incident_recorder,
#                 evidence_store=evidence_store,
#                 force_finalize=True,
#                 finalize_reason=(
#                     pipeline.get("shutdown_reason") or "AUDIO_WORKER_STOP"
#                 ),
#             )

#             pipeline["audio_anomaly_result"] = audio_anomaly_result

#             _append_audio_api_violations(
#                 pipeline=pipeline,
#                 violations=final_audio_violations,
#             )

#         print("[AUDIO] Dedicated real-time tracking worker stopped.")


# def start_audio_tracking_worker(
#     pipeline,
# ):
#     if not isinstance(
#         pipeline,
#         dict,
#     ):
#         return False

#     existing_thread = pipeline.get("audio_worker_thread")

#     if existing_thread is not None and existing_thread.is_alive():
#         return True

#     stop_event = pipeline.get("audio_worker_stop_event")

#     if stop_event is None:
#         stop_event = threading.Event()
#         pipeline["audio_worker_stop_event"] = stop_event

#     stop_event.clear()

#     thread = threading.Thread(
#         target=run_audio_tracking_worker,
#         args=(pipeline,),
#         name="SkolariqAudioTrackingWorker",
#         daemon=True,
#     )

#     pipeline["audio_worker_thread"] = thread

#     thread.start()

#     return True


# def stop_audio_tracking_worker(
#     pipeline,
#     timeout=3.0,
# ):
#     if not isinstance(
#         pipeline,
#         dict,
#     ):
#         return

#     stop_event = pipeline.get("audio_worker_stop_event")

#     if stop_event is not None:
#         stop_event.set()

#     thread = pipeline.get("audio_worker_thread")

#     if (
#         thread is not None
#         and thread.is_alive()
#         and thread is not threading.current_thread()
#     ):
#         thread.join(
#             timeout=max(
#                 0.0,
#                 float(timeout),
#             )
#         )

#         if thread.is_alive():
#             print(
#                 "[AUDIO] Waiting for active voice evidence "
#                 "to finish finalizing before shutdown..."
#             )

#             thread.join()

#     pipeline["audio_worker_thread"] = None


# def run_proctoring_detection_loop(
#     pipeline,
# ):
#     global exam_completed_flag

#     camera = pipeline["camera"]

#     face_detector = pipeline["face_detector"]

#     face_landmarker = pipeline["face_landmarker"]

#     gaze_tracker = pipeline["gaze_tracker"]

#     head_tracker = pipeline["head_tracker"]

#     pose_landmarker = pipeline["pose_landmarker"]

#     posture_monitor = pipeline["posture_monitor"]

#     object_detector = pipeline["object_detector"]

#     anomaly_manager = pipeline["anomaly_manager"]

#     anomaly_manager_lock = pipeline.get("anomaly_manager_lock")

#     if anomaly_manager_lock is None:
#         anomaly_manager_lock = threading.RLock()
#         pipeline["anomaly_manager_lock"] = anomaly_manager_lock

#     proctoring_api = pipeline.get("proctoring_api")

#     proctor_socket = pipeline.get("proctor_socket")

#     audio_monitor = pipeline.get("audio_monitor")

#     pending_violations = pipeline.get("pending_violations")

#     if pending_violations is None:
#         pending_violations = []

#         pipeline["pending_violations"] = pending_violations

#     pending_violations_lock = pipeline.get("pending_violations_lock")

#     if pending_violations_lock is None:
#         pending_violations_lock = threading.RLock()

#         pipeline["pending_violations_lock"] = pending_violations_lock

#     shutdown_requested_event = pipeline.get("shutdown_requested_event")

#     if shutdown_requested_event is None:
#         shutdown_requested_event = threading.Event()

#         pipeline["shutdown_requested_event"] = shutdown_requested_event

#     tracking_start_event = pipeline.get("tracking_start_event")

#     if tracking_start_event is None:
#         tracking_start_event = threading.Event()

#         tracking_start_event.set()

#         pipeline["tracking_start_event"] = tracking_start_event

#     frame_count = 0

#     last_log_time = 0.0

#     last_waiting_log_time = 0.0

#     tracking_started_logged = False

#     print()

#     if tracking_start_event.is_set():
#         print("[PROCTOR] Detection pipeline started.")

#     else:
#         print("[PROCTOR] Camera and microphone are active.")

#         print(
#             "[PROCTOR] Violation tracking is PAUSED until "
#             "the secure exam page signals readiness."
#         )

#     while True:
#         if exam_completed_flag or shutdown_requested_event.is_set():
#             print()

#             shutdown_reason = pipeline.get("shutdown_reason") or (
#                 "EXAM_COMPLETE" if exam_completed_flag else "SESSION_FINALIZATION"
#             )

#             print(
#                 "[PROCTOR] Finalization requested. "
#                 f"Stopping detection | reason={shutdown_reason}"
#             )

#             # The dedicated audio worker owns audio queue consumption and
#             # drains any final queued audio before final REST persistence.
#             break

#         success, frame = camera.read()

#         if not success or frame is None:
#             print("[CAMERA] Failed to read frame.")

#             time.sleep(0.05)

#             continue

#         if not tracking_start_event.is_set():
#             # AudioMonitor remains live for microphone status/device switching,
#             # but the dedicated audio worker does not consume or evaluate voice
#             # events until the validated tracking-start event is set. The
#             # before_tracking_start callback clears pre-tracking audio exactly
#             # once immediately before tracking becomes active.
#             current_time = time.time()

#             if current_time - last_waiting_log_time >= 2.0:
#                 print(
#                     "[PROCTOR] Waiting for secure exam page. "
#                     "Violation tracking remains paused."
#                 )

#                 if audio_monitor is not None:
#                     audio_status = audio_monitor.get_status()

#                     print(
#                         "[AUDIO] "
#                         f"mic_available="
#                         f"{audio_status.get('microphone_available', False)} "
#                         "| calibrating="
#                         f"{audio_status.get('calibrating', False)} "
#                         "| tracking=PAUSED"
#                     )

#                 last_waiting_log_time = current_time

#             time.sleep(0.02)

#             continue

#         if not tracking_started_logged:
#             tracking_started_logged = True

#             print()

#             print(
#                 "[PROCTOR] Frontend readiness confirmed. "
#                 "Starting violation tracking."
#             )

#             print("[PROCTOR] Detection pipeline started.")

#         frame_count += 1

#         try:
#             faces = face_detector.detect(frame)

#             if faces is None:
#                 faces = []

#         except Exception as error:
#             print(
#                 "[MEDIAPIPE FACE DETECTOR] Detection error:",
#                 error,
#             )

#             faces = []

#         face_count = len(faces)

#         try:
#             landmark_result = face_landmarker.process(frame)

#         except Exception as error:
#             print(
#                 "[FACE LANDMARKER] Processing error:",
#                 error,
#             )

#             landmark_result = {
#                 "valid": False,
#                 "landmarks": None,
#                 "face_count": 0,
#             }

#         landmark_valid = bool(
#             landmark_result.get(
#                 "valid",
#                 False,
#             )
#         )

#         landmarks = landmark_result.get("landmarks") if landmark_result else None

#         # Keep production face-count behavior aligned with test_v2.
#         # NO_FACE and MULTIPLE_FACES come from the MediaPipe face detector only.
#         # Face Landmarker remains responsible for landmarks/gaze/head tracking.
#         face_presence = {
#             "decision": (
#                 "NO_FACE"
#                 if face_count == 0
#                 else ("MULTIPLE_FACES" if face_count > 1 else "SINGLE_FACE")
#             ),
#             "no_face": (face_count == 0),
#             "face_count": face_count,
#             "landmark_valid": landmark_valid,
#             "landmark_face_count": (
#                 landmark_result.get("face_count", 0)
#                 if isinstance(
#                     landmark_result,
#                     dict,
#                 )
#                 else 0
#             ),
#             "mediapipe_face_present": (face_count > 0),
#         }

#         no_face_detected = face_count == 0

#         if landmarks is not None and landmark_valid:
#             try:
#                 gaze_result = gaze_tracker.process(
#                     landmarks,
#                     frame.shape,
#                 )

#             except Exception as error:
#                 print(
#                     "[GAZE] Processing error:",
#                     error,
#                 )

#                 gaze_result = {
#                     "direction": "UNKNOWN",
#                     "valid": False,
#                     "calibrated": False,
#                     "away": False,
#                     "away_duration": 0.0,
#                 }

#         else:
#             gaze_result = {
#                 "direction": "UNKNOWN",
#                 "valid": False,
#                 "calibrated": getattr(
#                     gaze_tracker,
#                     "calibrated",
#                     False,
#                 ),
#                 "away": False,
#                 "away_duration": 0.0,
#             }

#         if landmarks is not None and landmark_valid:
#             try:
#                 head_result = head_tracker.process(
#                     landmarks,
#                     frame.shape,
#                 )

#             except Exception as error:
#                 print(
#                     "[HEAD] Processing error:",
#                     error,
#                 )

#                 head_result = {
#                     "direction": "UNKNOWN",
#                     "valid": False,
#                     "yaw": None,
#                     "pitch": None,
#                     "roll": None,
#                     "away": False,
#                     "away_duration": 0.0,
#                 }

#         else:
#             head_result = {
#                 "direction": "UNKNOWN",
#                 "valid": False,
#                 "yaw": None,
#                 "pitch": None,
#                 "roll": None,
#                 "away": False,
#                 "away_duration": 0.0,
#             }

#         try:
#             pose_result = pose_landmarker.process(frame)

#         except Exception as error:
#             print(
#                 "[POSE] Processing error:",
#                 error,
#             )

#             pose_result = {
#                 "valid": False,
#                 "pose_count": 0,
#                 "landmarks": None,
#                 "world_landmarks": None,
#             }

#         try:
#             posture_result = posture_monitor.process(
#                 pose_result,
#                 frame.shape,
#             )

#         except Exception as error:
#             print(
#                 "[POSTURE] Processing error:",
#                 error,
#             )

#             posture_result = {
#                 "valid": False,
#                 "upper_body_visible": False,
#                 "leaning_left": False,
#                 "leaning_right": False,
#                 "left_arm_raised": False,
#                 "right_arm_raised": False,
#                 "unusual_arm_movement": False,
#                 "left_arm_movement": 0.0,
#                 "right_arm_movement": 0.0,
#             }

#         try:
#             object_detections = object_detector.detect(frame)

#             if object_detections is None:
#                 object_detections = []

#         except Exception as error:
#             print(
#                 "[YOLO26] Detection error:",
#                 error,
#             )

#             object_detections = []

#         object_anomalies = get_object_anomalies(object_detections)

#         anomaly_metadata = {
#             "frame_number": frame_count,
#             "face_count": face_count,
#             "landmark_valid": landmark_valid,
#             "face_presence": {
#                 "decision": face_presence.get(
#                     "decision",
#                     "UNKNOWN",
#                 ),
#                 "no_face": no_face_detected,
#                 "face_count": face_count,
#                 "mediapipe_face_present": (face_count > 0),
#                 "landmark_valid": landmark_valid,
#                 "landmark_face_count": face_presence.get(
#                     "landmark_face_count",
#                     0,
#                 ),
#             },
#             "gaze": {
#                 "direction": gaze_result.get(
#                     "direction",
#                     "UNKNOWN",
#                 ),
#                 "valid": gaze_result.get(
#                     "valid",
#                     False,
#                 ),
#                 "calibrated": gaze_result.get(
#                     "calibrated",
#                     False,
#                 ),
#                 "away": gaze_result.get(
#                     "away",
#                     False,
#                 ),
#                 "away_duration": gaze_result.get(
#                     "away_duration",
#                     0.0,
#                 ),
#             },
#             "head": {
#                 "direction": head_result.get(
#                     "direction",
#                     "UNKNOWN",
#                 ),
#                 "valid": head_result.get(
#                     "valid",
#                     False,
#                 ),
#                 "yaw": head_result.get("yaw"),
#                 "pitch": head_result.get("pitch"),
#                 "roll": head_result.get("roll"),
#                 "away": head_result.get(
#                     "away",
#                     False,
#                 ),
#                 "away_duration": head_result.get(
#                     "away_duration",
#                     0.0,
#                 ),
#             },
#             "pose": {
#                 "valid": posture_result.get(
#                     "valid",
#                     False,
#                 ),
#                 "pose_count": pose_result.get(
#                     "pose_count",
#                     0,
#                 ),
#                 "upper_body_visible": posture_result.get(
#                     "upper_body_visible",
#                     False,
#                 ),
#                 "leaning_left": posture_result.get(
#                     "leaning_left",
#                     False,
#                 ),
#                 "leaning_right": posture_result.get(
#                     "leaning_right",
#                     False,
#                 ),
#                 "left_arm_raised": posture_result.get(
#                     "left_arm_raised",
#                     False,
#                 ),
#                 "right_arm_raised": posture_result.get(
#                     "right_arm_raised",
#                     False,
#                 ),
#                 "unusual_arm_movement": posture_result.get(
#                     "unusual_arm_movement",
#                     False,
#                 ),
#                 "left_arm_movement": posture_result.get(
#                     "left_arm_movement",
#                     0.0,
#                 ),
#                 "right_arm_movement": posture_result.get(
#                     "right_arm_movement",
#                     0.0,
#                 ),
#                 "shoulder_center_x": posture_result.get("shoulder_center_x"),
#                 "shoulder_width": posture_result.get("shoulder_width"),
#             },
#             "objects": object_detections,
#         }

#         with anomaly_manager_lock:
#             visual_anomaly_results = anomaly_manager.update_many(
#                 anomalies={
#                     "NO_FACE": no_face_detected,
#                     "MULTIPLE_FACES": (face_count > 1),
#                     "GAZE_AWAY": bool(
#                         gaze_result.get(
#                             "away",
#                             False,
#                         )
#                     ),
#                     "HEAD_AWAY": bool(
#                         head_result.get(
#                             "away",
#                             False,
#                         )
#                     ),
#                     "PHONE_DETECTED": object_anomalies["phone_detected"],
#                     "BOOK_DETECTED": object_anomalies["book_detected"],
#                     "EXTRA_PERSON": object_anomalies["extra_person_detected"],
#                     "BODY_LEAN_LEFT": bool(
#                         posture_result.get(
#                             "leaning_left",
#                             False,
#                         )
#                     ),
#                     "BODY_LEAN_RIGHT": bool(
#                         posture_result.get(
#                             "leaning_right",
#                             False,
#                         )
#                     ),
#                     "LEFT_ARM_RAISED": bool(
#                         posture_result.get(
#                             "left_arm_raised",
#                             False,
#                         )
#                     ),
#                     "RIGHT_ARM_RAISED": bool(
#                         posture_result.get(
#                             "right_arm_raised",
#                             False,
#                         )
#                     ),
#                     "UNUSUAL_ARM_MOVEMENT": bool(
#                         posture_result.get(
#                             "unusual_arm_movement",
#                             False,
#                         )
#                     ),
#                     "UPPER_BODY_NOT_VISIBLE": (
#                         posture_result.get(
#                             "valid",
#                             False,
#                         )
#                         and not posture_result.get(
#                             "upper_body_visible",
#                             False,
#                         )
#                     ),
#                 },
#                 frame=frame,
#                 metadata=anomaly_metadata,
#             )

#         with pending_violations_lock:
#             pending_violations = pipeline.get(
#                 "pending_violations",
#                 [],
#             )

#             if pending_violations is None:
#                 pending_violations = []

#             pending_violations = queue_api_violations(
#                 visual_anomaly_results,
#                 pending_violations,
#             )

#             pipeline["pending_violations"] = pending_violations

#             if pending_violations:
#                 pending_violations = send_pending_violations(
#                     proctoring_api=proctoring_api,
#                     pending_violations=pending_violations,
#                     proctor_socket=proctor_socket,
#                 )

#                 pipeline["pending_violations"] = pending_violations

#         anomaly_results = dict(visual_anomaly_results)

#         audio_anomaly_result = pipeline.get("audio_anomaly_result")

#         if not isinstance(
#             audio_anomaly_result,
#             dict,
#         ):
#             audio_anomaly_result = empty_voice_anomaly_result()

#         anomaly_results["VOICE_DETECTED"] = dict(audio_anomaly_result)

#         current_time = time.time()

#         if current_time - last_log_time >= 1.0:
#             if face_count == 0:
#                 print("[DETECTION] NO FACE")

#             elif face_count == 1:
#                 print("[DETECTION] SINGLE FACE")

#             else:
#                 print("[DETECTION] " f"MULTIPLE FACES: {face_count}")

#             print(
#                 "[FACE PRESENCE] "
#                 f"mediapipe_count={face_count} "
#                 "| landmarker_valid="
#                 f"{landmark_valid} "
#                 "| landmarker_count="
#                 f"{face_presence.get('landmark_face_count', 0)} "
#                 "| no_face="
#                 f"{no_face_detected}"
#             )

#             if landmark_valid:
#                 print("[FACE LANDMARKER] VALID")

#             else:
#                 print("[FACE LANDMARKER] NOT AVAILABLE")

#             print(
#                 "[GAZE] "
#                 f"{gaze_result.get('direction', 'UNKNOWN')} "
#                 "| valid="
#                 f"{gaze_result.get('valid', False)} "
#                 "| calibrated="
#                 f"{gaze_result.get('calibrated', False)} "
#                 "| away="
#                 f"{gaze_result.get('away', False)}"
#             )

#             print(
#                 "[HEAD] "
#                 f"{head_result.get('direction', 'UNKNOWN')} "
#                 "| yaw="
#                 f"{head_result.get('yaw')} "
#                 "| pitch="
#                 f"{head_result.get('pitch')} "
#                 "| roll="
#                 f"{head_result.get('roll')} "
#                 "| away="
#                 f"{head_result.get('away', False)}"
#             )

#             print(
#                 "[POSE] "
#                 f"valid="
#                 f"{posture_result.get('valid', False)} "
#                 "| upper_body="
#                 f"{posture_result.get('upper_body_visible', False)} "
#                 "| lean_left="
#                 f"{posture_result.get('leaning_left', False)} "
#                 "| lean_right="
#                 f"{posture_result.get('leaning_right', False)} "
#                 "| left_arm="
#                 f"{posture_result.get('left_arm_raised', False)} "
#                 "| right_arm="
#                 f"{posture_result.get('right_arm_raised', False)} "
#                 "| unusual_movement="
#                 f"{posture_result.get('unusual_arm_movement', False)}"
#             )

#             if object_detections:
#                 for detection in object_detections:
#                     print(
#                         "[OBJECT] "
#                         f"{detection.get('label', 'OBJECT')} "
#                         "| confidence="
#                         f"{float(detection.get('confidence', 0.0)):.3f} "
#                         "| box=("
#                         f"{detection.get('x')},"
#                         f"{detection.get('y')},"
#                         f"{detection.get('x2')},"
#                         f"{detection.get('y2')}"
#                         ")"
#                     )

#             else:
#                 print("[OBJECT] " "No monitored objects detected.")

#             if audio_monitor is not None:
#                 audio_status = audio_monitor.get_status()

#                 active_microphone = audio_status.get("active_microphone") or {}

#                 print(
#                     "[AUDIO] "
#                     f"mic="
#                     f"{active_microphone.get('name', 'Unavailable')} "
#                     "| available="
#                     f"{audio_status.get('microphone_available', False)} "
#                     "| calibrating="
#                     f"{audio_status.get('calibrating', False)} "
#                     "| voice_active="
#                     f"{audio_status.get('voice_active', False)} "
#                     "| voice_confirmed="
#                     f"{audio_status.get('voice_confirmed', False)} "
#                     "| cumulative="
#                     f"{float(audio_status.get('cumulative_voice_duration_seconds', audio_status.get('voice_duration_seconds', 0.0)) or 0.0):.2f}s "
#                     "| silence="
#                     f"{float(audio_status.get('silence_duration_seconds', 0.0) or 0.0):.2f}s "
#                     "| whisper="
#                     f"{audio_status.get('whisper_candidate', False)} "
#                     "| source="
#                     f"{audio_status.get('detection_source')} "
#                     "| dbfs="
#                     f"{float(audio_status.get('dbfs', -100.0)):.1f}"
#                 )

#             for (
#                 event_type,
#                 result,
#             ) in anomaly_results.items():
#                 if result.get(
#                     "confirmed",
#                     False,
#                 ):
#                     cooldown_remaining = float(
#                         result.get(
#                             "cooldown_remaining",
#                             0.0,
#                         )
#                     )

#                     print(
#                         "[ANOMALY] "
#                         f"{event_type} "
#                         "| confirmed=True "
#                         "| captured="
#                         f"{result.get('captured', False)} "
#                         "| cooldown_remaining="
#                         f"{cooldown_remaining:.1f}s"
#                     )

#             if pending_violations:
#                 print("[API] Pending violations: " f"{len(pending_violations)}")

#             last_log_time = current_time


# def run_proctor_session(
#     kiosk,
#     keyboard_lockdown,
#     pipeline,
# ):
#     print()

#     print("[PROCTOR] Proctoring session active.")

#     try:

#         run_proctoring_detection_loop(pipeline)

#     except KeyboardInterrupt:

#         print()

#         print("[PROCTOR] Development stop requested.")

#         request_final_evidence_flush(
#             pipeline=pipeline,
#             reason="DEVELOPMENT_STOP",
#         )

#     finally:

#         final_reason = pipeline.get("shutdown_reason") or (
#             "EXAM_COMPLETE" if exam_completed_flag else "SESSION_FINALIZATION"
#         )

#         stop_audio_tracking_worker(pipeline)

#         request_final_evidence_flush(
#             pipeline=pipeline,
#             reason=final_reason,
#         )

#         flush_all_pending_evidence_until_empty(
#             pipeline=pipeline,
#             reason=final_reason,
#         )

#         stop_process_monitor_frontend_forwarder(pipeline)

#         stop_process_monitor_frontend_forwarder(pipeline)

#         process_monitor = pipeline.get("process_monitor")

#         if process_monitor is not None:
#             stop_process_monitor(process_monitor)

#             pipeline["process_monitor"] = None

#         try:

#             keyboard_lockdown.stop()

#         except Exception as error:

#             print(
#                 "[PROCTOR] Keyboard unlock error:",
#                 error,
#             )

#         try:

#             cleanup_proctoring_pipeline(
#                 camera=pipeline.get("camera"),
#                 microphone=pipeline.get("microphone"),
#                 face_detector=pipeline.get("face_detector"),
#                 face_landmarker=pipeline.get("face_landmarker"),
#                 gaze_tracker=pipeline.get("gaze_tracker"),
#                 head_tracker=pipeline.get("head_tracker"),
#                 pose_landmarker=pipeline.get("pose_landmarker"),
#                 posture_monitor=pipeline.get("posture_monitor"),
#                 object_detector=pipeline.get("object_detector"),
#                 evidence_store=pipeline.get("evidence_store"),
#                 anomaly_manager=pipeline.get("anomaly_manager"),
#                 proctoring_api=pipeline.get("proctoring_api"),
#                 audio_monitor=pipeline.get("audio_monitor"),
#                 voice_incident_recorder=pipeline.get("voice_incident_recorder"),
#             )

#         except Exception as error:

#             print(
#                 "[PROCTOR] Pipeline cleanup error:",
#                 error,
#             )

#         try:

#             kiosk.stop()

#         except Exception as error:

#             print(
#                 "[PROCTOR] Kiosk stop error:",
#                 error,
#             )

#         if exam_completed_flag:
#             open_assessments_center()


# def terminate_startup_failure(
#     kiosk,
#     keyboard_lockdown,
#     socket_client,
#     pipeline,
#     error,
# ):
#     print()

#     print("[PROCTOR] " "========================================")

#     print("[PROCTOR] " "CAMERA/MICROPHONE STARTUP FAILED")

#     print("[PROCTOR] " "Exam session got terminated.")

#     print(f"[PROCTOR] Reason: {error}")

#     print("[PROCTOR] " "========================================")

#     if pipeline is not None:
#         try:
#             stop_audio_tracking_worker(pipeline)

#             request_final_evidence_flush(
#                 pipeline=pipeline,
#                 reason="STARTUP_FAILURE",
#             )

#             flush_all_pending_evidence_until_empty(
#                 pipeline=pipeline,
#                 reason="STARTUP_FAILURE",
#             )

#         except Exception as flush_error:
#             print(
#                 "[API] Startup-failure evidence flush error:",
#                 flush_error,
#             )

#     if pipeline is not None:

#         process_monitor = pipeline.get("process_monitor")

#         if process_monitor is not None:
#             try:
#                 stop_process_monitor(process_monitor)

#                 pipeline["process_monitor"] = None

#             except Exception:
#                 pass

#     if keyboard_lockdown is not None:

#         try:
#             keyboard_lockdown.stop()

#         except Exception:
#             pass

#     if socket_client is not None:

#         try:
#             socket_client.disconnect()

#         except Exception:
#             pass

#     if pipeline is not None:

#         try:

#             cleanup_proctoring_pipeline(
#                 camera=pipeline.get("camera"),
#                 microphone=pipeline.get("microphone"),
#                 face_detector=pipeline.get("face_detector"),
#                 face_landmarker=pipeline.get("face_landmarker"),
#                 gaze_tracker=pipeline.get("gaze_tracker"),
#                 head_tracker=pipeline.get("head_tracker"),
#                 pose_landmarker=pipeline.get("pose_landmarker"),
#                 posture_monitor=pipeline.get("posture_monitor"),
#                 object_detector=pipeline.get("object_detector"),
#                 evidence_store=pipeline.get("evidence_store"),
#                 anomaly_manager=pipeline.get("anomaly_manager"),
#                 proctoring_api=pipeline.get("proctoring_api"),
#                 audio_monitor=pipeline.get("audio_monitor"),
#                 voice_incident_recorder=pipeline.get("voice_incident_recorder"),
#             )

#         except Exception:
#             pass

#     if kiosk is not None:

#         try:
#             kiosk.stop()

#         except Exception:
#             pass


# def main():
#     global exam_completed_flag

#     exam_completed_flag = False

#     # This event gates every detector/anomaly operation.
#     #
#     # Camera and microphone are initialized before the kiosk opens,
#     # but this event remains unset until AssessmentsNewPage has
#     # rendered, joined the secure socket room, and Node forwards
#     # "proctor-tracking-start" to this Python client.
#     tracking_start_event = threading.Event()

#     token = get_launch_token()

#     try:

#         session = validate_launch_token(token)

#     except LaunchTokenError as error:

#         print(f"Launch rejected: {error}")

#         sys.exit(1)

#     session = session.model_dump()

#     session["raw_token"] = token

#     print()

#     print("[PROCTOR] Launch token validated.")

#     safe_session_log = {
#         key: value for key, value in session.items() if key != "raw_token"
#     }

#     print(
#         "[PROCTOR] Session:",
#         safe_session_log,
#     )

#     # A valid new launch may supersede an independently running stale proctor.
#     # This cleanup is deliberately best-effort and MUST NEVER prevent the new
#     # assessment from starting. The cleanup implementation also protects this
#     # process and every launcher/ancestor in its active process chain.
#     try:
#         terminate_previous_proctor_instances()
#     except Exception as error:
#         print(
#             "[PROCTOR][DUPLICATE CLEANUP] Unexpected cleanup error; "
#             "continuing startup safely. "
#             f"Reason: {error}"
#         )

#     kiosk = None

#     keyboard_lockdown = None

#     socket_client = None

#     process_monitor = None

#     pipeline = None

#     # ProcessMonitor may detect and close restricted applications before the
#     # Socket.IO connection exists. Keep only frontend-safe message payloads in
#     # this queue until the proctor socket has joined its room.
#     process_monitor_frontend_queue = queue.Queue()

#     try:

#         print()

#         print("[PROCTOR] Securing desktop before camera and microphone startup...")

#         process_monitor = prepare_process_monitor(
#             frontend_event_callback=process_monitor_frontend_queue.put,
#         )

#         perform_pre_exam_process_cleanup(process_monitor)

#         print()

#         print("[PROCTOR] Performing mandatory " "camera and microphone check...")

#         pipeline = initialize_proctoring_pipeline(session)

#         pipeline["process_monitor"] = process_monitor
#         pipeline["process_monitor_frontend_queue"] = process_monitor_frontend_queue

#         print()

#         print("[PROCTOR] Camera check: PASSED")

#         print("[PROCTOR] Microphone check: PASSED")

#         print()

#         print("[PROCTOR] Starting secure exam " "environment...")

#         # Attach the new tracking gate before starting the socket.
#         # The detection loop will keep the camera/microphone alive,
#         # but all detector/anomaly/evidence work remains paused until
#         # this event is set by the validated socket start signal.
#         pipeline["tracking_start_event"] = tracking_start_event

#         def before_tracking_start():
#             # Match the working test_v2 behavior: discard bootstrap audio and
#             # begin the real assessment from a fresh VAD/incident state.
#             reset_audio_tracking_state(pipeline)

#         def before_exam_complete():
#             return wait_for_final_evidence_flush(
#                 pipeline=pipeline,
#                 reason="EXAM_COMPLETE",
#             )

#         socket_client = start_proctor_socket(
#             session,
#             tracking_start_event=tracking_start_event,
#             audio_monitor=pipeline.get("audio_monitor"),
#             before_exam_complete_callback=before_exam_complete,
#             before_tracking_start_callback=before_tracking_start,
#         )

#         # Attach the same live socket client to the running pipeline.
#         pipeline["proctor_socket"] = socket_client

#         if socket_client is not None:

#             start_process_monitor_frontend_forwarder(
#                 pipeline=pipeline,
#                 socket_client=socket_client,
#             )

#             print("[PROCTOR] Socket client created " "successfully.")

#             # Real-time violation notifications must not wait for REST
#             # persistence. Image anomalies emit after their normal local
#             # evidence capture. VOICE_DETECTED emits immediately using the
#             # lightweight deferred-audio marker, while its complete WAV
#             # continues recording and is queued to REST only after the held
#             # voice incident ends.
#             anomaly_manager = pipeline.get("anomaly_manager")

#             if anomaly_manager is not None:

#                 anomaly_manager.set_socket_client(socket_client)

#                 print(
#                     "[PROCTOR] Live socket attached to anomaly manager. "
#                     "Image violations emit after local evidence capture; "
#                     "voice violations emit immediately while complete WAV "
#                     "evidence continues recording."
#                 )

#                 if not start_audio_tracking_worker(pipeline):
#                     raise RuntimeError(
#                         "Unable to start the dedicated real-time audio "
#                         "tracking worker."
#                     )

#                 print(
#                     "[PROCTOR] Dedicated audio tracking worker ready. "
#                     "Voice violations will be processed independently "
#                     "from vision inference and REST submission."
#                 )

#             else:

#                 raise RuntimeError(
#                     "Anomaly manager is unavailable. "
#                     "Real-time proctor violation events cannot be enabled."
#                 )

#         else:

#             raise RuntimeError(
#                 "Secure proctor socket could not be started. "
#                 "The exam cannot begin without the tracking-start channel."
#             )

#         def before_security_termination():
#             return wait_for_final_evidence_flush(
#                 pipeline=pipeline,
#                 reason="SECURE_DESKTOP",
#             )

#         kiosk, kiosk_process = start_kiosk(
#             token,
#             proctor_socket=socket_client,
#             before_security_termination_callback=before_security_termination,
#         )

#         activate_process_monitor(
#             process_monitor=process_monitor,
#             kiosk_process=kiosk_process,
#         )

#         keyboard_lockdown = start_keyboard_lockdown()

#         run_proctor_session(
#             kiosk,
#             keyboard_lockdown,
#             pipeline,
#         )

#         pipeline = None

#     except Exception as error:

#         print()

#         print("[PROCTOR] Startup/session failure.")

#         print(f"[PROCTOR] Reason: {error}")

#         terminate_startup_failure(
#             kiosk=kiosk,
#             keyboard_lockdown=keyboard_lockdown,
#             socket_client=socket_client,
#             pipeline=pipeline,
#             error=error,
#         )

#         kiosk = None

#         keyboard_lockdown = None

#         socket_client = None

#         pipeline = None

#     finally:

#         if pipeline is not None:
#             try:
#                 stop_audio_tracking_worker(pipeline)

#                 request_final_evidence_flush(
#                     pipeline=pipeline,
#                     reason=(pipeline.get("shutdown_reason") or "MAIN_FINALIZATION"),
#                 )

#                 flush_all_pending_evidence_until_empty(
#                     pipeline=pipeline,
#                     reason=(pipeline.get("shutdown_reason") or "MAIN_FINALIZATION"),
#                 )

#             except Exception as flush_error:
#                 print(
#                     "[API] Main final evidence flush error:",
#                     flush_error,
#                 )

#         if process_monitor is not None:
#             stop_process_monitor(process_monitor)

#             process_monitor = None

#         if socket_client:

#             try:
#                 socket_client.disconnect()

#             except Exception:
#                 pass

#         if pipeline is not None:

#             try:

#                 cleanup_proctoring_pipeline(
#                     camera=pipeline.get("camera"),
#                     microphone=pipeline.get("microphone"),
#                     face_detector=pipeline.get("face_detector"),
#                     face_landmarker=pipeline.get("face_landmarker"),
#                     gaze_tracker=pipeline.get("gaze_tracker"),
#                     head_tracker=pipeline.get("head_tracker"),
#                     pose_landmarker=pipeline.get("pose_landmarker"),
#                     posture_monitor=pipeline.get("posture_monitor"),
#                     object_detector=pipeline.get("object_detector"),
#                     evidence_store=pipeline.get("evidence_store"),
#                     anomaly_manager=pipeline.get("anomaly_manager"),
#                     proctoring_api=pipeline.get("proctoring_api"),
#                     audio_monitor=pipeline.get("audio_monitor"),
#                     voice_incident_recorder=pipeline.get("voice_incident_recorder"),
#                 )

#             except Exception:
#                 pass


# if __name__ == "__main__":
#     main()


import argparse
import os
import sys
import time
import math
import queue
import tempfile
import threading
import webbrowser
import subprocess

try:
    import psutil
except Exception:
    psutil = None

from collections import deque
from datetime import datetime, timezone

from urllib.parse import (
    parse_qs,
    quote,
    urlparse,
)

import cv2
import sounddevice as sd

from src.auth import (
    LaunchTokenError,
    validate_launch_token,
)

from src.config import settings

from src.core.kiosk_manager import (
    KioskManager,
)

from src.core.keyboard_lockdown import (
    KeyboardLockdownManager,
)

try:
    from src.core.process_monitor import (
        ProcessMonitor,
    )

    PROCESS_MONITOR_IMPORT_ERROR = None

except Exception as error:
    ProcessMonitor = None

    PROCESS_MONITOR_IMPORT_ERROR = error

from src.socket.proctor_socket import (
    ProctorSocketClient,
)

from src.vision.face_detector_mediapipe import (
    MediaPipeFaceDetector,
)

from src.vision.face_landmarker import (
    FaceLandmarker,
)

from src.vision.gaze_tracker import (
    GazeTracker,
)

from src.vision.head_tracker import (
    HeadTracker,
)

from src.vision.pose_landmarker import (
    PoseLandmarker,
)

from src.vision.object_detector_yolo26 import (
    YOLO26ObjectDetector,
)

from src.core.posture_monitor import (
    PostureMonitor,
)

from src.evidence.evidence_store import (
    EvidenceStore,
)

from src.core.anomaly_manager import (
    AnomalyManager,
)

from src.core.audio_device_manager import (
    AudioDeviceManager,
)

from src.core.voice_activity_detector import (
    VoiceActivityDetector,
)

from src.core.audio_monitor import (
    AudioMonitor,
)

from src.api.proctoring_api import (
    ProctoringAPI,
)

PROTOCOL_SCHEME = "skolariq-proctor"

LAUNCH_ACTION = "launch"

DEFAULT_ASSESSMENT_WEB_BASE_URL = "http://localhost:5173"

CAMERA_INDEX = 0

CAMERA_WIDTH = 640

CAMERA_HEIGHT = 480

MIC_CHANNELS = 1

exam_completed_flag = False

FINAL_EVIDENCE_RETRY_DELAY_SECONDS = 2.0

PREVIOUS_PROCTOR_INSTANCE_SHUTDOWN_TIMEOUT_SECONDS = 4.0

# Voice detection/incident behavior.
# Keep production behavior aligned with the validated test_v2 flow:
# - human speech starts a logical incident, but is not immediately a violation;
# - only cumulative HUMAN-SPEECH time counts toward confirmation;
# - silence/pause time contributes zero toward the threshold;
# - speech resuming before 5 seconds of continuous silence continues the same
#   logical incident and keeps the previous cumulative speech total;
# - VOICE_DETECTED is confirmed only after 1.5 seconds cumulative speech;
# - the logical incident ends only after 5 seconds continuous silence.
VOICE_TRIGGER_SECONDS = 1.5
VOICE_SMOOTHING_WINDOW_SECONDS = 0.06
VOICE_DETECTOR_SILENCE_RESET_SECONDS = 5.0
# Kept for backward compatibility with existing status/metadata consumers.
VOICE_SHORT_GAP_GRACE_SECONDS = 5.0
VOICE_INCIDENT_END_SILENCE_SECONDS = 5.0
VOICE_EVIDENCE_PRE_ROLL_SECONDS = 0.75

# Keep short incidents in RAM, then automatically spill longer evidence to a
# temporary file. This protects low-memory laptops while preserving the full
# high-quality PCM stream for the final WAV.
VOICE_EVIDENCE_SPOOL_MEMORY_BYTES = 4 * 1024 * 1024


class DeferredAudioEvidenceStore:
    """
    Backward-compatible EvidenceStore adapter for production voice incidents.

    Image evidence is saved immediately through the existing EvidenceStore.

    For VOICE_DETECTED, AnomalyManager receives an immediate lightweight
    evidence marker. That marker lets the existing AnomalyManager/socket path
    confirm and broadcast the violation immediately without waiting for the
    complete voice incident to finish.

    The actual WAV is written only when the held voice incident closes.
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
    Preserve the complete original PCM stream for one voice incident.

    A short pre-roll is continuously retained so the beginning of the first
    utterance is not clipped while the VOICE_DETECTED event travels through
    the queue. Once an incident starts, every original PCM frame is appended,
    including natural silence between speech segments.

    SpooledTemporaryFile keeps short evidence in memory and automatically
    spills longer evidence to disk after the configured memory threshold.
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
    Backward-compatible AudioMonitor subclass used by production main.py.

    AudioMonitor keeps all existing microphone discovery, device switching,
    VAD processing, high-quality evidence buffering and event emission.
    This subclass only mirrors the original PCM stream into the full-incident
    recorder. VAD/resampling changes inside AudioMonitor do not alter the PCM
    that is retained here for evidence.
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


def extract_token_from_url(
    launch_url,
):
    try:
        parsed = urlparse(launch_url)

    except Exception:
        raise ValueError("Invalid proctor launch URL.")

    if parsed.scheme != PROTOCOL_SCHEME:
        raise ValueError("Invalid proctor protocol.")

    if parsed.netloc != LAUNCH_ACTION:
        raise ValueError("Invalid proctor launch action.")

    query = parse_qs(parsed.query)

    tokens = query.get("token")

    if not tokens:
        raise ValueError("Launch token is missing.")

    token = tokens[0].strip()

    if not token:
        raise ValueError("Launch token is empty.")

    return token


def get_launch_token():
    parser = argparse.ArgumentParser(prog="Skolariq Proctor")

    parser.add_argument(
        "launch_url",
        nargs="?",
    )

    parser.add_argument(
        "--token",
        required=False,
    )

    args = parser.parse_args()

    if args.token:
        return args.token.strip()

    if args.launch_url:
        try:
            return extract_token_from_url(args.launch_url)

        except ValueError as error:
            print(f"Launch rejected: {error}")

            sys.exit(1)

    print("Launch rejected: " "No launch token provided.")

    sys.exit(1)


def get_assessment_web_base_url():
    configured_url = getattr(
        settings,
        "ASSESSMENT_WEB_BASE_URL",
        None,
    )

    if configured_url:
        return str(configured_url).strip().rstrip("/")

    return DEFAULT_ASSESSMENT_WEB_BASE_URL


def get_assessment_frontend_base_url():
    configured_url = getattr(
        settings,
        "ASSESSMENT_FRONTEND_BASE_URL",
        None,
    )

    if configured_url:
        return str(configured_url).strip().rstrip("/")

    environment_url = os.getenv(
        "ASSESSMENT_FRONTEND_BASE_URL",
        "",
    )

    if environment_url:
        return str(environment_url).strip().rstrip("/")

    return get_assessment_web_base_url()


def build_assessments_center_url():
    return f"{get_assessment_frontend_base_url()}" "/student/assessments-center"


def open_assessments_center():
    target_url = build_assessments_center_url()

    print()

    print(
        "[PROCTOR] Opening assessments center:",
        target_url,
    )

    try:
        opened = webbrowser.open(
            target_url,
            new=1,
            autoraise=True,
        )

        if not opened:
            print(
                "[PROCTOR] Browser open request was issued, "
                "but the operating system did not confirm it."
            )

        return bool(opened)

    except Exception as error:
        print(
            "[PROCTOR] Unable to open assessments center:",
            error,
        )

        return False


def get_socket_server_url():
    configured_url = getattr(
        settings,
        "SOCKET_SERVER_URL",
        None,
    )

    if configured_url:
        return str(configured_url).strip().rstrip("/")

    return get_assessment_web_base_url()


def build_bootstrap_url(
    token,
):
    base_url = get_assessment_web_base_url()

    encoded_token = quote(
        token,
        safe="",
    )

    return f"{base_url}" "/student/proctor/bootstrap" f"?token={encoded_token}"


def open_camera():
    if os.name == "nt":
        camera = cv2.VideoCapture(
            CAMERA_INDEX,
            cv2.CAP_DSHOW,
        )

    else:
        camera = cv2.VideoCapture(CAMERA_INDEX)

    if not camera.isOpened():
        raise RuntimeError(f"Unable to open camera index " f"{CAMERA_INDEX}.")

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

        raise RuntimeError("Camera opened but failed to " "provide a valid frame.")

    return camera


def start_microphone():
    try:
        device_info = sd.query_devices(kind="input")

        if not device_info:
            raise RuntimeError("No microphone input device " "was found.")

        samplerate = float(
            device_info.get(
                "default_samplerate",
                44100,
            )
        )

        if samplerate <= 0:
            samplerate = 44100.0

        stream = sd.InputStream(
            device=None,
            channels=MIC_CHANNELS,
            samplerate=samplerate,
            dtype="float32",
            blocksize=1024,
        )

        stream.start()

        return stream

    except Exception as error:
        raise RuntimeError(f"Unable to start microphone: " f"{error}") from error


def stop_microphone(
    microphone,
):
    if microphone is None:
        return

    try:
        microphone.stop()

    except Exception:
        pass

    try:
        microphone.close()

    except Exception:
        pass


def start_kiosk(
    token,
    proctor_socket=None,
    before_security_termination_callback=None,
):
    bootstrap_url = build_bootstrap_url(token)

    print()

    print("[PROCTOR] Starting secure kiosk...")

    print("[PROCTOR] Bootstrap URL prepared.")

    kiosk = KioskManager(
        proctor_socket=proctor_socket,
        before_security_termination_callback=before_security_termination_callback,
    )

    if proctor_socket is not None:
        print("[PROCTOR] Proctor socket attached " "to kiosk manager.")

    else:
        print("[PROCTOR] Kiosk manager started " "without proctor socket.")

    try:
        process = kiosk.start(bootstrap_url)

    except Exception as error:
        print("[PROCTOR] Kiosk launch failed.")

        print(f"[PROCTOR] Reason: {error}")

        sys.exit(1)

    print("[PROCTOR] Kiosk started successfully.")

    return (
        kiosk,
        process,
    )


def start_keyboard_lockdown():
    app_environment = str(
        getattr(
            settings,
            "APP_ENV",
            "development",
        )
    ).lower()

    allow_development_escape = app_environment != "production"

    lockdown = KeyboardLockdownManager(
        allow_development_escape=allow_development_escape
    )

    lockdown.start()

    return lockdown


def get_process_pid(
    process,
):
    if process is None:
        return None

    if isinstance(
        process,
        int,
    ):
        return process if process > 0 else None

    try:
        pid = int(
            getattr(
                process,
                "pid",
            )
        )

    except (
        AttributeError,
        TypeError,
        ValueError,
    ):
        return None

    return pid if pid > 0 else None


def _normalize_process_path(value):
    if not value:
        return ""

    try:
        return os.path.normcase(os.path.abspath(os.path.expanduser(str(value))))
    except Exception:
        return os.path.normcase(str(value))


def _windows_process_snapshot():
    """
    Return a lightweight Windows process snapshot without using
    psutil.Process.parent()/ppid().

    The ProcessMonitor's strict cleanup can create a lot of process churn.
    Repeated psutil parent lookups on Windows rebuild a global PPID map and can
    become very slow. Toolhelp gives us the PID/PPID/name data in one native
    snapshot and avoids that startup bottleneck.
    """
    if os.name != "nt":
        return {}

    try:
        import ctypes
        from ctypes import wintypes

        TH32CS_SNAPPROCESS = 0x00000002
        MAX_PATH = 260
        INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

        class PROCESSENTRY32W(ctypes.Structure):
            _fields_ = [
                ("dwSize", wintypes.DWORD),
                ("cntUsage", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD),
                ("th32DefaultHeapID", ctypes.c_size_t),
                ("th32ModuleID", wintypes.DWORD),
                ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD),
                ("pcPriClassBase", wintypes.LONG),
                ("dwFlags", wintypes.DWORD),
                ("szExeFile", wintypes.WCHAR * MAX_PATH),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        create_snapshot = kernel32.CreateToolhelp32Snapshot
        create_snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
        create_snapshot.restype = wintypes.HANDLE

        process_first = kernel32.Process32FirstW
        process_first.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
        process_first.restype = wintypes.BOOL

        process_next = kernel32.Process32NextW
        process_next.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
        process_next.restype = wintypes.BOOL

        close_handle = kernel32.CloseHandle
        close_handle.argtypes = [wintypes.HANDLE]
        close_handle.restype = wintypes.BOOL

        snapshot_handle = create_snapshot(TH32CS_SNAPPROCESS, 0)

        if snapshot_handle in (None, 0, INVALID_HANDLE_VALUE):
            return {}

        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        processes = {}

        try:
            success = bool(
                process_first(
                    snapshot_handle,
                    ctypes.byref(entry),
                )
            )

            while success:
                pid = int(entry.th32ProcessID)

                if pid >= 0:
                    processes[pid] = {
                        "pid": pid,
                        "ppid": int(entry.th32ParentProcessID),
                        "name": str(entry.szExeFile or "").strip(),
                    }

                success = bool(
                    process_next(
                        snapshot_handle,
                        ctypes.byref(entry),
                    )
                )

        finally:
            close_handle(snapshot_handle)

        return processes

    except Exception as error:
        print(
            "[PROCESS MONITOR] Windows process snapshot warning:",
            error,
        )
        return {}


def _current_proctor_ancestor_pids(process_snapshot):
    current_pid = int(os.getpid())
    protected_pids = {current_pid}

    try:
        direct_parent_pid = int(os.getppid())
    except Exception:
        direct_parent_pid = 0

    if direct_parent_pid > 0:
        protected_pids.add(direct_parent_pid)

    if not isinstance(process_snapshot, dict) or not process_snapshot:
        return protected_pids

    cursor = current_pid
    visited = set()

    for _ in range(32):
        if cursor in visited:
            break

        visited.add(cursor)

        record = process_snapshot.get(cursor)

        if not isinstance(record, dict):
            break

        try:
            parent_pid = int(record.get("ppid") or 0)
        except (TypeError, ValueError):
            break

        if parent_pid <= 0 or parent_pid == cursor:
            break

        protected_pids.add(parent_pid)
        cursor = parent_pid

    return protected_pids


def _install_fast_pre_exam_process_guards(process_monitor):
    """
    Temporarily replace only the ProcessMonitor helpers that repeatedly call
    psutil parent()/ppid() during the pre-exam cleanup.

    Returns a callback that restores the original helpers. If anything needed
    for the safe replacement is unavailable, no patch is installed.
    """
    if process_monitor is None or psutil is None or os.name != "nt":
        return lambda: None

    process_snapshot = _windows_process_snapshot()

    if not process_snapshot:
        return lambda: None

    protected_proctor_pids = _current_proctor_ancestor_pids(process_snapshot)

    original_contains_proctor = getattr(
        process_monitor,
        "_process_tree_contains_proctor",
        None,
    )
    original_get_browser_root = getattr(
        process_monitor,
        "_get_browser_root",
        None,
    )
    original_collect_strict_roots = getattr(
        process_monitor,
        "_collect_strict_user_process_roots",
        None,
    )

    def fast_process_tree_contains_proctor(process):
        if process is None:
            return True

        try:
            target_pid = int(process.pid)
        except (TypeError, ValueError, AttributeError):
            return True

        return target_pid in protected_proctor_pids

    def fast_get_browser_root(process):
        if process is None:
            return None

        try:
            current_pid = int(process.pid)
        except (TypeError, ValueError, AttributeError):
            return process

        root = process
        visited = set()

        while current_pid > 0 and current_pid not in visited:
            visited.add(current_pid)

            current_record = process_snapshot.get(current_pid)

            if not isinstance(current_record, dict):
                break

            current_name = str(current_record.get("name") or "").strip()

            try:
                if not process_monitor._is_browser(current_name):
                    break
            except Exception:
                break

            try:
                root = psutil.Process(current_pid)
            except Exception:
                break

            try:
                parent_pid = int(current_record.get("ppid") or 0)
            except (TypeError, ValueError):
                break

            if parent_pid <= 0 or parent_pid == current_pid:
                break

            parent_record = process_snapshot.get(parent_pid)

            if not isinstance(parent_record, dict):
                break

            parent_name = str(parent_record.get("name") or "").strip()

            try:
                if not process_monitor._is_browser(parent_name):
                    break
            except Exception:
                break

            current_pid = parent_pid

        return root

    def fast_collect_strict_user_process_roots():
        candidates = {}

        for process in psutil.process_iter(
            attrs=[
                "pid",
                "name",
                "exe",
            ]
        ):
            try:
                if int(process.pid) == int(process_monitor.current_pid):
                    continue

                if not process_monitor._is_current_user_process(process):
                    continue

                if process_monitor._is_strict_lockdown_exempt(process):
                    continue

                candidates[int(process.pid)] = process

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess,
            ):
                continue
            except Exception:
                continue

        if not candidates:
            return []

        candidate_pids = set(candidates.keys())
        roots = []

        for pid, process in candidates.items():
            record = process_snapshot.get(pid)

            try:
                parent_pid = int(record.get("ppid") if isinstance(record, dict) else 0)
            except (TypeError, ValueError):
                parent_pid = 0

            if parent_pid in candidate_pids:
                continue

            roots.append(process)

        return roots

    if callable(original_contains_proctor):
        process_monitor._process_tree_contains_proctor = (
            fast_process_tree_contains_proctor
        )

    if callable(original_get_browser_root):
        process_monitor._get_browser_root = fast_get_browser_root

    if callable(original_collect_strict_roots):
        process_monitor._collect_strict_user_process_roots = (
            fast_collect_strict_user_process_roots
        )

    print(
        "[PROCESS MONITOR] Fast Windows startup process guards enabled "
        f"| protected_proctor_pids={sorted(protected_proctor_pids)}"
    )

    def restore():
        try:
            if callable(original_contains_proctor):
                process_monitor._process_tree_contains_proctor = (
                    original_contains_proctor
                )

            if callable(original_get_browser_root):
                process_monitor._get_browser_root = original_get_browser_root

            if callable(original_collect_strict_roots):
                process_monitor._collect_strict_user_process_roots = (
                    original_collect_strict_roots
                )

        except Exception:
            pass

    return restore


def _is_same_proctor_process(process):
    """
    Identify another instance of this exact proctor without treating every
    python.exe process as a duplicate.
    """
    if psutil is None or process is None:
        return False

    try:
        pid = int(process.pid)
    except (TypeError, ValueError, AttributeError):
        return False

    if pid <= 0 or pid == os.getpid():
        return False

    # Never classify the launcher/parent chain of the currently running proctor
    # as a stale duplicate. This is especially important for custom-protocol,
    # batch-file, development Python, and packaged-launcher flows.
    if pid in _get_current_process_ancestor_pids():
        return False

    try:
        current_username = str(psutil.Process(os.getpid()).username() or "").lower()
    except Exception:
        current_username = ""

    try:
        candidate_username = str(process.username() or "").lower()
    except Exception:
        candidate_username = ""

    if (
        current_username
        and candidate_username
        and current_username != candidate_username
    ):
        return False

    current_main_path = _normalize_process_path(__file__)
    current_project_root = _normalize_process_path(
        os.path.dirname(os.path.dirname(current_main_path))
    )
    current_executable = _normalize_process_path(sys.executable)

    try:
        candidate_executable = _normalize_process_path(process.exe())
    except Exception:
        candidate_executable = ""

    if bool(getattr(sys, "frozen", False)):
        if candidate_executable and candidate_executable == current_executable:
            return True

    try:
        cmdline = [
            str(item or "").strip()
            for item in (process.cmdline() or [])
            if str(item or "").strip()
        ]
    except Exception:
        cmdline = []

    has_module_launch = False

    for index, argument in enumerate(cmdline[:-1]):
        if argument == "-m" and cmdline[index + 1].lower() == "src.main":
            has_module_launch = True
            break

    has_exact_main_path = False
    has_src_main_argument = False

    for argument in cmdline:
        cleaned = argument.strip().strip('"').strip("'")

        if not cleaned:
            continue

        if _normalize_process_path(cleaned) == current_main_path:
            has_exact_main_path = True
            break

        slash_argument = cleaned.replace("\\", "/").lower()

        if slash_argument.endswith("/src/main.py") or slash_argument == "src/main.py":
            has_src_main_argument = True

    try:
        candidate_cwd = _normalize_process_path(process.cwd())
    except Exception:
        candidate_cwd = ""

    same_project = bool(
        candidate_cwd and current_project_root and candidate_cwd == current_project_root
    )

    if has_exact_main_path:
        return True

    if same_project and (has_module_launch or has_src_main_argument):
        return True

    return False


def _get_current_process_ancestor_pids():
    """
    Return the PID chain that launched this proctor process.

    These processes are protected from duplicate-instance cleanup because a
    protocol launcher, development wrapper, Python bootstrapper, or packaged
    executable may legitimately be an ancestor of the active proctor process.
    """
    protected_pids = {os.getpid()}

    if psutil is None:
        return protected_pids

    try:
        current_process = psutil.Process(os.getpid())

        for parent in current_process.parents():
            try:
                parent_pid = int(parent.pid)
            except (TypeError, ValueError, AttributeError):
                continue

            if parent_pid > 0:
                protected_pids.add(parent_pid)

    except Exception:
        pass

    return protected_pids


def _is_current_process_or_ancestor(process):
    if process is None:
        return False

    try:
        pid = int(process.pid)
    except (TypeError, ValueError, AttributeError):
        return False

    return pid in _get_current_process_ancestor_pids()


def _force_terminate_previous_proctor(process):
    if psutil is None or process is None:
        return False

    try:
        pid = int(process.pid)
    except (TypeError, ValueError, AttributeError):
        return False

    if pid <= 0 or _is_current_process_or_ancestor(process):
        print(
            "[PROCTOR][DUPLICATE CLEANUP] Protected current/launcher process "
            f"will not be terminated | pid={pid}"
        )
        return False

    if os.name == "nt":
        try:
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

            # Deliberately do NOT use taskkill /T here. A previous proctor may
            # have launched or share a wrapper tree with the new instance.
            # Killing only the exact stale PID prevents Windows from taking the
            # newly launched proctor down with an ancestor/process tree.
            subprocess.run(
                [
                    "taskkill",
                    "/PID",
                    str(pid),
                    "/F",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=PREVIOUS_PROCTOR_INSTANCE_SHUTDOWN_TIMEOUT_SECONDS,
                creationflags=creationflags,
                check=False,
            )

        except Exception as error:
            print(
                "[PROCTOR][DUPLICATE CLEANUP] taskkill warning "
                f"| pid={pid} | error={error}"
            )

        deadline = time.monotonic() + PREVIOUS_PROCTOR_INSTANCE_SHUTDOWN_TIMEOUT_SECONDS

        while time.monotonic() < deadline:
            if not psutil.pid_exists(pid):
                return True

            time.sleep(0.05)

    # Re-check immediately before the psutil fallback in case process ancestry
    # changed while Windows cleanup was attempted.
    if _is_current_process_or_ancestor(process):
        print(
            "[PROCTOR][DUPLICATE CLEANUP] Cleanup aborted because PID became "
            f"part of the active launch chain | pid={pid}"
        )
        return False

    try:
        process.terminate()
    except (
        psutil.NoSuchProcess,
        psutil.ZombieProcess,
    ):
        return True
    except Exception:
        pass

    try:
        process.wait(timeout=1.0)
    except Exception:
        if _is_current_process_or_ancestor(process):
            return False

        try:
            process.kill()
        except Exception:
            pass

    deadline = time.monotonic() + 1.5

    while time.monotonic() < deadline:
        if not psutil.pid_exists(pid):
            return True

        time.sleep(0.05)

    return not psutil.pid_exists(pid)


def terminate_previous_proctor_instances():
    """
    A valid new launch supersedes any stale instance of this same application.

    Unrelated Python/backend processes are deliberately ignored.
    """
    if psutil is None:
        print(
            "[PROCTOR][DUPLICATE CLEANUP] psutil unavailable; "
            "skipping stale-instance cleanup."
        )
        return []

    print()
    print("[PROCTOR][DUPLICATE CLEANUP] Checking for stale proctor instances...")

    candidates = []

    for process in psutil.process_iter(attrs=["pid", "name"]):
        try:
            if _is_same_proctor_process(process):
                candidates.append(process)
        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
        ):
            continue
        except Exception:
            continue

    if not candidates:
        print("[PROCTOR][DUPLICATE CLEANUP] No previous proctor instance found.")
        return []

    terminated_pids = []

    for process in candidates:
        try:
            pid = int(process.pid)
        except Exception:
            continue

        try:
            process_name = process.name()
        except Exception:
            process_name = "unknown"

        print(
            "[PROCTOR][DUPLICATE CLEANUP] Previous instance detected "
            f"| process={process_name} | pid={pid}"
        )

        if _force_terminate_previous_proctor(process):
            terminated_pids.append(pid)
            print(
                "[PROCTOR][DUPLICATE CLEANUP] Previous instance terminated "
                f"| pid={pid}"
            )
        else:
            print(
                "[PROCTOR][DUPLICATE CLEANUP] Warning: previous instance could "
                f"not be fully terminated | pid={pid}. Startup will continue."
            )

    return terminated_pids


def prepare_process_monitor(
    frontend_event_callback=None,
):
    if ProcessMonitor is None:
        print()

        print("[PROCESS MONITOR] Process monitoring is unavailable.")

        if PROCESS_MONITOR_IMPORT_ERROR is not None:
            print(
                "[PROCESS MONITOR] Reason:",
                PROCESS_MONITOR_IMPORT_ERROR,
            )

        return None

    try:
        print()

        print("[PROCESS MONITOR] Initializing process monitor...")

        try:
            process_monitor = ProcessMonitor(
                check_interval=2.0,
                block_external_browsers=True,
                terminate_remote_access=True,
                terminate_screen_sharing=True,
                frontend_event_callback=frontend_event_callback,
            )

        except TypeError:
            # Backward compatibility with an older ProcessMonitor build.
            process_monitor = ProcessMonitor(
                check_interval=2.0,
                block_external_browsers=True,
                terminate_remote_access=True,
                terminate_screen_sharing=True,
            )

            if hasattr(process_monitor, "frontend_event_callback"):
                process_monitor.frontend_event_callback = frontend_event_callback

        process_monitor.capture_pre_kiosk_browser_processes()

        print("[PROCESS MONITOR] Pre-kiosk browser snapshot completed.")

        return process_monitor

    except Exception as error:
        print(
            "[PROCESS MONITOR] Initialization failed:",
            error,
        )

        return None


def perform_pre_exam_process_cleanup(
    process_monitor,
):
    """
    Best-effort targeted process cleanup before camera/microphone startup.

    The production ProcessMonitor still performs the same cleanup. On Windows,
    only its repeated parent/PPID lookups are temporarily replaced with a native
    process snapshot so process churn cannot stall startup inside psutil.ppid().
    """
    if process_monitor is None:
        print(
            "[PROCESS MONITOR] Pre-exam process cleanup is unavailable. "
            "Continuing with normal startup."
        )

        return {
            "supported": False,
            "detected": [],
            "terminated": [],
            "failed": [],
        }

    cleanup_method = getattr(
        process_monitor,
        "terminate_pre_exam_media_processes",
        None,
    )

    if not callable(cleanup_method):
        print(
            "[PROCESS MONITOR] Installed ProcessMonitor does not expose "
            "terminate_pre_exam_media_processes(). "
            "Continuing with normal startup."
        )

        return {
            "supported": False,
            "detected": [],
            "terminated": [],
            "failed": [],
        }

    print()
    print(
        "[PROCESS MONITOR] Performing targeted pre-exam cleanup "
        "before camera/microphone startup..."
    )

    restore_guards = _install_fast_pre_exam_process_guards(process_monitor)

    try:
        result = cleanup_method()

    except Exception as error:
        print(
            "[PROCESS MONITOR] Pre-exam cleanup error:",
            error,
        )
        print(
            "[PROCESS MONITOR] Cleanup failure is non-blocking. "
            "Continuing with camera/microphone and secure kiosk startup."
        )

        return {
            "supported": True,
            "detected": [],
            "terminated": [],
            "failed": [],
            "cleanup_error": str(error),
        }

    finally:
        try:
            restore_guards()
        except Exception:
            pass

    if not isinstance(result, dict):
        result = {
            "detected": [],
            "terminated": [],
            "failed": [],
        }

    detected = result.get("detected", [])
    terminated = result.get("terminated", [])
    failed = result.get("failed", [])

    if not isinstance(detected, list):
        detected = []

    if not isinstance(terminated, list):
        terminated = []

    if not isinstance(failed, list):
        failed = []

    result["supported"] = True
    result["detected"] = detected
    result["terminated"] = terminated
    result["failed"] = failed

    print(
        "[PROCESS MONITOR] Targeted pre-exam cleanup completed "
        f"| detected={len(detected)} "
        f"| terminated={len(terminated)} "
        f"| remaining={len(failed)}"
    )

    if failed:
        remaining_processes = []

        for item in failed:
            if not isinstance(item, dict):
                continue

            process_name = str(item.get("process_name", "") or "unknown").strip()
            pid = item.get("pid")

            remaining_processes.append(
                f"{process_name}" + (f" (PID {pid})" if pid is not None else "")
            )

        remaining_text = (
            ", ".join(remaining_processes)
            if remaining_processes
            else f"{len(failed)} process(es)"
        )

        print(
            "[PROCESS MONITOR] Warning: some restricted processes "
            f"could not be terminated yet: {remaining_text}"
        )
        print(
            "[PROCESS MONITOR] This is non-blocking. The assessment will "
            "continue starting, and continuous process monitoring will retry "
            "restricted applications."
        )

    print(
        "[PROCESS MONITOR] Pre-exam cleanup finished. "
        "Camera/microphone initialization may proceed."
    )

    return result


def _get_process_monitor_frontend_message(
    payload,
):
    if isinstance(
        payload,
        dict,
    ):
        message = payload.get("message")

    else:
        message = payload

    message = str(message or "").strip()

    return message or None


def emit_process_monitor_frontend_event(
    socket_client,
    payload,
):
    """
    Emit a process-monitor notification to Node using a dedicated event.

    Privacy contract:
    the outbound payload contains exactly ONE field:
        {"message": "..."}

    No PID, process name, executable path, user/session/test/schedule ID,
    timestamp, category, action, or diagnostic metadata is emitted.
    """

    message = _get_process_monitor_frontend_message(payload)

    if not message or socket_client is None:
        return False

    sio_client = getattr(
        socket_client,
        "sio",
        None,
    )

    if sio_client is None or not getattr(
        sio_client,
        "connected",
        False,
    ):
        return False

    if not bool(
        getattr(
            socket_client,
            "joined_room",
            False,
        )
    ):
        return False

    try:
        sio_client.emit(
            "proctor-process-monitor-event",
            {
                "message": message,
            },
        )

        print("[PROCESS MONITOR][SOCKET] Frontend message emitted: " f"{message}")

        return True

    except Exception as error:
        print(
            "[PROCESS MONITOR][SOCKET] Frontend message emit failed:",
            error,
        )

        return False


def start_process_monitor_frontend_forwarder(
    pipeline,
    socket_client,
):
    """
    Forward sanitized ProcessMonitor messages to the already joined proctor
    socket room. Events detected during pre-exam cleanup are buffered until the
    socket has connected and joined the room, so they are not lost.
    """

    if not isinstance(
        pipeline,
        dict,
    ):
        return False

    event_queue = pipeline.get("process_monitor_frontend_queue")

    if event_queue is None or socket_client is None:
        return False

    existing_thread = pipeline.get("process_monitor_frontend_thread")

    if existing_thread is not None and existing_thread.is_alive():
        return True

    stop_event = threading.Event()
    pipeline["process_monitor_frontend_stop_event"] = stop_event

    def worker():
        pending_payload = None

        while not stop_event.is_set():
            if pending_payload is None:
                try:
                    pending_payload = event_queue.get(
                        timeout=0.20,
                    )

                except queue.Empty:
                    continue

                except Exception:
                    pending_payload = None
                    continue

            if emit_process_monitor_frontend_event(
                socket_client=socket_client,
                payload=pending_payload,
            ):
                pending_payload = None
                continue

            stop_event.wait(0.20)

    thread = threading.Thread(
        target=worker,
        name="SkolariqProcessMonitorFrontendForwarder",
        daemon=True,
    )

    pipeline["process_monitor_frontend_thread"] = thread

    thread.start()

    print(
        "[PROCESS MONITOR] Frontend notification forwarder started. "
        "Only human-readable message text will be emitted."
    )

    return True


def stop_process_monitor_frontend_forwarder(
    pipeline,
):
    if not isinstance(
        pipeline,
        dict,
    ):
        return

    stop_event = pipeline.get("process_monitor_frontend_stop_event")

    if stop_event is not None:
        try:
            stop_event.set()
        except Exception:
            pass

    thread = pipeline.get("process_monitor_frontend_thread")

    if (
        thread is not None
        and thread.is_alive()
        and thread is not threading.current_thread()
    ):
        try:
            thread.join(timeout=1.0)
        except Exception:
            pass

    pipeline["process_monitor_frontend_stop_event"] = None
    pipeline["process_monitor_frontend_thread"] = None


def activate_process_monitor(
    process_monitor,
    kiosk_process,
):
    """
    Protect the kiosk process tree and start continuous targeted monitoring.

    Deliberately avoids the legacy blanket/strict cleanup loop. The updated
    ProcessMonitor's normal scan already blocks the restricted categories
    (external browsers, remote access, screen sharing, user media/camera/audio
    apps, and duplicate proctor instances) without repeatedly sweeping every
    current-user process.
    """
    if process_monitor is None:
        return False

    kiosk_pid = get_process_pid(kiosk_process)

    if kiosk_pid is None:
        print(
            "[PROCESS MONITOR] Kiosk PID is unavailable. "
            "External-browser termination will remain disabled until a "
            "kiosk PID is available, but other targeted monitoring can start."
        )

    else:
        try:
            process_monitor.set_kiosk_root_pid(kiosk_pid)

            print("[PROCESS MONITOR] Secure kiosk process tree protected.")

            enable_strict_lockdown = getattr(
                process_monitor,
                "enable_strict_user_process_lockdown",
                None,
            )

            if callable(enable_strict_lockdown):
                enable_strict_lockdown(False)

                print(
                    "[PROCESS MONITOR] Legacy blanket strict-lockdown loop "
                    "disabled. Targeted continuous monitoring will be used."
                )

        except Exception as error:
            print(
                "[PROCESS MONITOR] Failed to register kiosk PID:",
                error,
            )

            kiosk_pid = None

    if kiosk_pid is not None:
        try:
            terminated_browser_pids = (
                process_monitor.terminate_pre_kiosk_browser_processes()
            )

            if terminated_browser_pids:
                print(
                    "[PROCESS MONITOR] Pre-existing browser sessions terminated. "
                    f"Root PIDs={terminated_browser_pids}"
                )

            else:
                print(
                    "[PROCESS MONITOR] No pre-existing browser session "
                    "required termination."
                )

        except Exception as error:
            print(
                "[PROCESS MONITOR] Failed to terminate "
                "pre-existing browser sessions:",
                error,
            )

    try:
        started = process_monitor.start()

        if started:
            print("[PROCESS MONITOR] Continuous targeted process monitoring started.")

        else:
            print(
                "[PROCESS MONITOR] Continuous monitor was already active "
                "or could not be started."
            )

        return bool(started)

    except Exception as error:
        print(
            "[PROCESS MONITOR] Failed to start continuous monitoring:",
            error,
        )

        return False


def stop_process_monitor(
    process_monitor,
):
    if process_monitor is None:
        return

    try:
        process_monitor.stop()

        print("[PROCESS MONITOR] Process monitoring stopped.")

    except Exception as error:
        print(
            "[PROCESS MONITOR] Cleanup error:",
            error,
        )


def start_proctor_socket(
    session,
    tracking_start_event=None,
    audio_monitor=None,
    before_exam_complete_callback=None,
    before_tracking_start_callback=None,
):
    """
    Start the native Socket.IO client.

    Backward compatibility:
    - tracking_start_event is optional.
    - audio_monitor is optional.
    - before_exam_complete_callback is optional.
    - before_tracking_start_callback is optional.
    - Existing calls that pass only session continue to work.

    Secure kiosk behavior:
    - When tracking_start_event is supplied, Python listens for
      "proctor-tracking-start".
    - Camera/microphone may already be active before this event.
    - Violation detection remains paused until the validated
      frontend signal reaches Python through Node.
    """

    try:
        socket_client = ProctorSocketClient(
            server_url=get_socket_server_url(),
            token=session.get("raw_token"),
            proctor_session_id=session["proctor_session_id"],
            test_id=session["test_id"],
            schedule_id=session["schedule_id"],
        )

        def exam_completed(
            data,
        ):
            global exam_completed_flag

            print()

            print("[PROCTOR] Exam completion " "received.")

            print(
                "[PROCTOR]",
                data,
            )

            exam_completed_flag = True

            if callable(before_exam_complete_callback):
                try:
                    before_exam_complete_callback()

                except Exception as error:
                    print(
                        "[PROCTOR] Exam-complete final evidence callback error:",
                        error,
                    )

        socket_client.exam_completed_callback = exam_completed

        if audio_monitor is not None:

            def microphone_devices_request(
                data,
            ):
                status = audio_monitor.get_status()

                return {
                    "devices": audio_monitor.get_available_microphones(),
                    "current_device": status.get("active_microphone"),
                    "reason": None,
                }

            def microphone_change_request(
                data,
            ):
                payload = (
                    data
                    if isinstance(
                        data,
                        dict,
                    )
                    else {}
                )

                device_key = str(
                    payload.get(
                        "device_key",
                        "",
                    )
                ).strip()

                if not device_key:
                    return {
                        "success": False,
                        "reason": "MICROPHONE_DEVICE_KEY_REQUIRED",
                    }

                return audio_monitor.switch_microphone(
                    device_key=device_key,
                    timeout=8.0,
                )

            socket_client.microphone_devices_request_callback = (
                microphone_devices_request
            )

            socket_client.microphone_change_request_callback = microphone_change_request

            print("[PROCTOR] Microphone device-control callbacks registered.")

        if tracking_start_event is not None:

            expected_session_id = str(
                session.get(
                    "proctor_session_id",
                    "",
                )
            )

            expected_test_id = str(
                session.get(
                    "test_id",
                    "",
                )
            )

            expected_schedule_id = str(
                session.get(
                    "schedule_id",
                    "",
                )
            )

            def proctor_tracking_start(
                data,
            ):
                payload = (
                    data
                    if isinstance(
                        data,
                        dict,
                    )
                    else {}
                )

                received_session_id = str(
                    payload.get(
                        "proctor_session_id",
                        "",
                    )
                )

                received_test_id = str(
                    payload.get(
                        "test_id",
                        "",
                    )
                )

                received_schedule_id = str(
                    payload.get(
                        "schedule_id",
                        "",
                    )
                )

                if (
                    not received_session_id
                    or not received_test_id
                    or not received_schedule_id
                ):
                    print(
                        "[SOCKET][TRACKING START IGNORED] "
                        "Missing session/exam/schedule information."
                    )

                    return

                if (
                    received_session_id != expected_session_id
                    or received_test_id != expected_test_id
                    or received_schedule_id != expected_schedule_id
                ):
                    print(
                        "[SOCKET][TRACKING START IGNORED] "
                        "Received event does not match the active proctor session."
                    )

                    return

                if tracking_start_event.is_set():
                    print(
                        "[SOCKET][TRACKING START] "
                        "Duplicate start signal received; tracking is already active."
                    )

                    return

                if callable(before_tracking_start_callback):
                    try:
                        before_tracking_start_callback()

                    except Exception as error:
                        print(
                            "[SOCKET][TRACKING START ERROR] "
                            "Unable to prepare audio tracking state:",
                            error,
                        )

                        return

                tracking_start_event.set()

                print()

                print(
                    "[SOCKET][TRACKING START] "
                    "Validated frontend start signal received."
                )

                print("[PROCTOR] Violation tracking is now ACTIVE.")

            sio_client = getattr(
                socket_client,
                "sio",
                None,
            )

            if sio_client is None or not hasattr(
                sio_client,
                "on",
            ):
                raise RuntimeError(
                    "Socket client does not expose a Socket.IO event interface."
                )

            sio_client.on(
                "proctor-tracking-start",
                proctor_tracking_start,
            )

            print(
                "[PROCTOR] Tracking start listener registered. "
                "Violation tracking will remain paused until the secure exam page signals readiness."
            )

        socket_client.start_background()

        print("[PROCTOR] Proctor socket " "startup requested.")

        return socket_client

    except Exception as error:
        print(
            "[PROCTOR] Socket startup failed:",
            error,
        )

        return None


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


def get_landmark_xy(
    landmark,
):
    if landmark is None:
        return None

    try:
        if isinstance(landmark, dict):
            x = float(landmark.get("x"))
            y = float(landmark.get("y"))
        else:
            x = float(getattr(landmark, "x"))
            y = float(getattr(landmark, "y"))
    except (TypeError, ValueError, AttributeError):
        return None

    if not (math.isfinite(x) and math.isfinite(y)):
        return None

    return (x, y)


def get_valid_landmark_points(
    landmarks,
):
    if landmarks is None:
        return []

    try:
        iterable = list(landmarks)
    except TypeError:
        return []

    points = []

    for landmark in iterable:
        point = get_landmark_xy(landmark)

        if point is not None:
            points.append(point)

    return points


def is_yunet_face_clipped_by_frame(
    face,
    frame_shape,
):
    coordinates = get_face_coordinates(face)

    if coordinates is None:
        return False

    frame_height = int(frame_shape[0])
    frame_width = int(frame_shape[1])

    x1 = int(coordinates["x"])
    y1 = int(coordinates["y"])
    x2 = int(coordinates["x"] + coordinates["width"])
    y2 = int(coordinates["y"] + coordinates["height"])

    tolerance = max(
        1,
        int(min(frame_width, frame_height) * 0.003),
    )

    return bool(
        x1 <= tolerance
        or y1 <= tolerance
        or x2 >= (frame_width - 1 - tolerance)
        or y2 >= (frame_height - 1 - tolerance)
    )


def are_face_landmarks_out_of_frame(
    landmarks,
    frame_shape,
):
    points = get_valid_landmark_points(landmarks)

    if len(points) < 20:
        return False

    frame_height = int(frame_shape[0])
    frame_width = int(frame_shape[1])

    normalized_count = sum(
        1 for x, y in points if (-2.0 <= x <= 2.0 and -2.0 <= y <= 2.0)
    )

    coordinates_are_normalized = normalized_count >= int(len(points) * 0.90)

    if coordinates_are_normalized:
        outside_count = sum(
            1 for x, y in points if (x < 0.0 or x > 1.0 or y < 0.0 or y > 1.0)
        )

        near_edge_count = sum(
            1
            for x, y in points
            if (x <= 0.002 or x >= 0.998 or y <= 0.002 or y >= 0.998)
        )
    else:
        outside_count = sum(
            1
            for x, y in points
            if (x < 0.0 or x > (frame_width - 1) or y < 0.0 or y > (frame_height - 1))
        )

        pixel_edge_tolerance = max(
            1,
            int(min(frame_width, frame_height) * 0.003),
        )

        near_edge_count = sum(
            1
            for x, y in points
            if (
                x <= pixel_edge_tolerance
                or x >= (frame_width - 1 - pixel_edge_tolerance)
                or y <= pixel_edge_tolerance
                or y >= (frame_height - 1 - pixel_edge_tolerance)
            )
        )

    outside_threshold = max(
        3,
        int(math.ceil(len(points) * 0.01)),
    )

    near_edge_threshold = max(
        12,
        int(math.ceil(len(points) * 0.08)),
    )

    return bool(
        outside_count >= outside_threshold or near_edge_count >= near_edge_threshold
    )


def evaluate_face_presence(
    faces,
    landmark_result,
    frame_shape,
):
    if faces is None:
        faces = []

    face_count = len(faces)

    if not isinstance(landmark_result, dict):
        landmark_result = {}

    landmark_valid = bool(landmark_result.get("valid", False))

    try:
        landmark_face_count = int(landmark_result.get("face_count", 0) or 0)
    except (TypeError, ValueError):
        landmark_face_count = 0

    landmarks = landmark_result.get("landmarks")

    yunet_face_present = face_count > 0
    landmarker_face_present = bool(landmark_valid or landmark_face_count > 0)

    yunet_face_clipped = False

    if face_count == 1:
        yunet_face_clipped = is_yunet_face_clipped_by_frame(
            faces[0],
            frame_shape,
        )

    landmark_face_out_of_frame = False

    if landmarker_face_present:
        landmark_face_out_of_frame = are_face_landmarks_out_of_frame(
            landmarks,
            frame_shape,
        )

    partial_face_out_of_frame = False

    if face_count <= 1:
        if landmarker_face_present:
            partial_face_out_of_frame = landmark_face_out_of_frame
        elif yunet_face_present:
            partial_face_out_of_frame = yunet_face_clipped

    any_face_present = bool(yunet_face_present or landmarker_face_present)

    no_face = bool((not any_face_present) or partial_face_out_of_frame)

    if no_face:
        if partial_face_out_of_frame:
            decision = "FACE_PARTIALLY_OUT"
        else:
            decision = "NO_FACE"
    elif face_count > 1:
        decision = "MULTIPLE_FACES"
    elif yunet_face_present and landmarker_face_present:
        decision = "FACE_PRESENT_BOTH"
    elif yunet_face_present:
        decision = "FACE_PRESENT_YUNET"
    elif landmarker_face_present:
        decision = "FACE_PRESENT_LANDMARKER"
    else:
        decision = "NO_FACE"

    return {
        "no_face": no_face,
        "decision": decision,
        "face_count": face_count,
        "landmark_valid": landmark_valid,
        "landmark_face_count": landmark_face_count,
        "yunet_face_present": yunet_face_present,
        "landmarker_face_present": landmarker_face_present,
        "yunet_face_clipped": yunet_face_clipped,
        "landmark_face_out_of_frame": landmark_face_out_of_frame,
        "partial_face_out_of_frame": partial_face_out_of_frame,
    }


def get_object_anomalies(
    object_detections,
):
    phone_detected = False

    book_detected = False

    extra_person_detected = False

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

            phone_detected = True

            phone_detections.append(detection)

        elif label == "BOOK":

            book_detected = True

            book_detections.append(detection)

        elif label == "PERSON":

            person_detections.append(detection)

    if len(person_detections) > 1:
        extra_person_detected = True

    return {
        "phone_detected": phone_detected,
        "book_detected": book_detected,
        "extra_person_detected": extra_person_detected,
        "phone_detections": phone_detections,
        "book_detections": book_detections,
        "person_detections": person_detections,
    }


def initialize_proctoring_pipeline(
    session,
):
    camera = None

    microphone = None

    audio_device_manager = None

    voice_activity_detector = None

    audio_monitor = None

    voice_incident_recorder = None

    audio_event_queue = None

    face_detector = None

    face_landmarker = None

    gaze_tracker = None

    head_tracker = None

    pose_landmarker = None

    posture_monitor = None

    object_detector = None

    evidence_store = None

    anomaly_manager = None

    proctoring_api = None

    try:
        print()

        print("[PROCTOR] Initializing native proctoring hardware...")

        print("[CAMERA] Starting camera...")

        camera = open_camera()

        print("[CAMERA] Camera opened successfully.")

        print("[MICROPHONE] Discovering microphone devices...")

        audio_device_manager = AudioDeviceManager()

        microphone_selection = audio_device_manager.select_default_microphone()

        if not microphone_selection.get(
            "success",
            False,
        ):
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

        audio_event_queue = queue.Queue()

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

        print("[EVIDENCE] Initializing evidence store...")

        real_evidence_store = EvidenceStore(
            student_id=session.get(
                "student_id",
                session.get(
                    "user_id",
                    "local_test",
                ),
            ),
            exam_id=session.get(
                "test_id",
                "local_test",
            ),
            schedule_id=session.get(
                "schedule_id",
                "local_test",
            ),
            session_id=session.get(
                "proctor_session_id",
                "local_test",
            ),
        )

        evidence_store = DeferredAudioEvidenceStore(real_evidence_store)

        print(
            "[EVIDENCE] Evidence store initialized. "
            "Image evidence saves immediately; VOICE_DETECTED uses an "
            "immediate socket marker and saves the complete WAV when the "
            "voice incident ends."
        )

        print("[ANOMALY] Initializing anomaly manager...")

        anomaly_manager = AnomalyManager(evidence_store=evidence_store)

        configure_voice_anomaly_for_production(anomaly_manager)

        print("[ANOMALY] Anomaly manager initialized.")

        voice_incident_recorder = VoiceIncidentEvidenceRecorder(
            pre_roll_seconds=VOICE_EVIDENCE_PRE_ROLL_SECONDS,
            spool_memory_limit_bytes=VOICE_EVIDENCE_SPOOL_MEMORY_BYTES,
        )

        # Start the audio monitor only after the heavy vision models and
        # AnomalyManager are ready. The monitor preserves the original PCM
        # stream for evidence while the VAD can independently use its
        # detector-compatible processing path.
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

        microphone = audio_monitor

        print("[AUDIO] Audio monitor started successfully.")

        print("[API] Initializing proctoring API...")

        proctoring_api = ProctoringAPI(token=session.get("raw_token"))

        print("[API] Proctoring API initialized.")

        print()

        print("[PROCTOR] Native proctoring pipeline " "initialized successfully.")

        return {
            "camera": camera,
            "microphone": microphone,
            "audio_device_manager": audio_device_manager,
            "voice_activity_detector": voice_activity_detector,
            "audio_monitor": audio_monitor,
            "voice_incident_recorder": voice_incident_recorder,
            "audio_event_queue": audio_event_queue,
            "audio_anomaly_result": None,
            "audio_tracking_prepared": False,
            "audio_worker_thread": None,
            "audio_worker_stop_event": threading.Event(),
            "anomaly_manager_lock": threading.RLock(),
            "face_detector": face_detector,
            "face_landmarker": face_landmarker,
            "gaze_tracker": gaze_tracker,
            "head_tracker": head_tracker,
            "pose_landmarker": pose_landmarker,
            "posture_monitor": posture_monitor,
            "object_detector": object_detector,
            "evidence_store": evidence_store,
            "anomaly_manager": anomaly_manager,
            "proctoring_api": proctoring_api,
            "proctor_socket": None,
            "process_monitor": None,
            "pending_violations": [],
            "pending_violations_lock": threading.RLock(),
            "final_evidence_flush_lock": threading.RLock(),
            "shutdown_requested_event": threading.Event(),
            "final_evidence_flush_completed_event": threading.Event(),
            "shutdown_reason": None,
        }

    except Exception:
        cleanup_proctoring_pipeline(
            camera=camera,
            microphone=microphone,
            face_detector=face_detector,
            face_landmarker=face_landmarker,
            gaze_tracker=gaze_tracker,
            head_tracker=head_tracker,
            pose_landmarker=pose_landmarker,
            posture_monitor=posture_monitor,
            object_detector=object_detector,
            evidence_store=evidence_store,
            anomaly_manager=anomaly_manager,
            proctoring_api=proctoring_api,
            audio_monitor=audio_monitor,
            voice_incident_recorder=voice_incident_recorder,
        )

        raise


def cleanup_proctoring_pipeline(
    camera=None,
    microphone=None,
    face_detector=None,
    face_landmarker=None,
    gaze_tracker=None,
    head_tracker=None,
    pose_landmarker=None,
    posture_monitor=None,
    object_detector=None,
    evidence_store=None,
    anomaly_manager=None,
    proctoring_api=None,
    audio_monitor=None,
    voice_incident_recorder=None,
):
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

    if microphone is not None and microphone is not audio_monitor:
        try:
            stop_microphone(microphone)

        except Exception as error:
            print(
                "[MICROPHONE] Cleanup error:",
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


def queue_api_violations(
    anomaly_results,
    pending_violations,
):
    if pending_violations is None:
        pending_violations = []

    for (
        event_type,
        result,
    ) in anomaly_results.items():

        if not isinstance(
            result,
            dict,
        ):
            continue

        api_violation = result.get("api_violation")

        if not api_violation:
            continue

        if not isinstance(
            api_violation,
            dict,
        ):
            continue

        pending_violations.append(dict(api_violation))

    return pending_violations


def send_pending_violations(
    proctoring_api,
    pending_violations,
    proctor_socket=None,
    require_all_evidence_files=False,
):
    """
    Send queued proctoring violations while preserving
    the exact relationship between each violation and
    its evidence file.

    The violation's local file_path is intentionally
    removed from the JSON payload. Instead, evidence_files
    contains an explicit violation_index -> file path mapping.

    This prevents evidence paths from being attached to the
    wrong violation when some violations have no evidence.

    Backward compatibility:
    - proctor_socket remains an optional argument so existing
      callers do not need to change.
    - Existing two-argument and three-argument calls continue
      to work unchanged.
    - require_all_evidence_files defaults to False so normal periodic
      submission behavior remains unchanged.

    Real-time behavior:
    - Socket.IO notification is NOT emitted from this function.
    - AnomalyManager emits the real-time event immediately after
      local image/audio evidence capture.
    - REST persistence remains independently retryable here.
    """

    if proctoring_api is None or not pending_violations:
        return pending_violations

    violations = []

    evidence_files = []

    missing_evidence_files = []

    for violation in pending_violations:

        if not isinstance(
            violation,
            dict,
        ):
            continue

        violation_copy = dict(violation)

        file_path = violation_copy.pop(
            "file_path",
            None,
        )

        violation_index = len(violations)

        violations.append(violation_copy)

        if not file_path:
            continue

        file_path_string = str(file_path).strip()

        if not file_path_string:
            continue

        if not os.path.isfile(file_path_string):
            print(
                "[API] Evidence file is missing " "for pending violation:",
                file_path_string,
            )

            missing_evidence_files.append(file_path_string)

            continue

        evidence_files.append(
            {
                "violation_index": violation_index,
                "path": file_path_string,
            }
        )

        print(
            "[API] Evidence mapping prepared "
            f"| violation_index={violation_index} "
            f"| path={file_path_string}"
        )

    if require_all_evidence_files and missing_evidence_files:
        print(
            "[API] Strict evidence submission blocked. "
            f"Missing evidence files={len(missing_evidence_files)}"
        )

        return pending_violations

    if not violations:
        return []

    try:
        print(
            "[API] Preparing violation batch "
            f"| violations={len(violations)} "
            f"| evidence_files={len(evidence_files)}"
        )

        result = proctoring_api.send_violations(
            violations=violations,
            evidence_files=evidence_files,
        )

    except Exception as error:
        print("[API] Violation submission " f"error: {error}")

        return pending_violations

    if result.get(
        "success",
        False,
    ):
        print("[API] Violation batch sent " "successfully. " f"Count={len(violations)}")

        return []

    reason = result.get("reason")

    if reason == "API_COOLDOWN":
        return pending_violations

    print("[API] Violation batch was not " "sent.")

    if reason:
        print(f"[API] Reason: {reason}")

    return pending_violations


def request_final_evidence_flush(
    pipeline,
    reason,
):
    if not isinstance(
        pipeline,
        dict,
    ):
        return False

    reason_text = str(reason or "SESSION_FINALIZATION").strip()

    if not reason_text:
        reason_text = "SESSION_FINALIZATION"

    pipeline["shutdown_reason"] = reason_text

    shutdown_event = pipeline.get("shutdown_requested_event")

    if shutdown_event is not None and hasattr(
        shutdown_event,
        "set",
    ):
        shutdown_event.set()

    print("[PROCTOR] Final evidence flush requested " f"| reason={reason_text}")

    return True


def wait_for_final_evidence_flush(
    pipeline,
    reason,
):
    if not request_final_evidence_flush(
        pipeline=pipeline,
        reason=reason,
    ):
        return False

    completed_event = pipeline.get("final_evidence_flush_completed_event")

    if completed_event is None or not hasattr(
        completed_event,
        "wait",
    ):
        return False

    print(
        "[PROCTOR] Waiting for every captured evidence item "
        "to be persisted before termination..."
    )

    while not completed_event.wait(timeout=0.25):
        pass

    print(
        "[PROCTOR] Final evidence persistence confirmed "
        f"| reason={pipeline.get('shutdown_reason')}"
    )

    return True


def flush_all_pending_evidence_until_empty(
    pipeline,
    reason=None,
):
    if not isinstance(
        pipeline,
        dict,
    ):
        return True

    flush_lock = pipeline.get("final_evidence_flush_lock")

    if flush_lock is None:
        flush_lock = threading.RLock()

        pipeline["final_evidence_flush_lock"] = flush_lock

    pending_lock = pipeline.get("pending_violations_lock")

    if pending_lock is None:
        pending_lock = threading.RLock()

        pipeline["pending_violations_lock"] = pending_lock

    completed_event = pipeline.get("final_evidence_flush_completed_event")

    if completed_event is None:
        completed_event = threading.Event()

        pipeline["final_evidence_flush_completed_event"] = completed_event

    reason_text = str(
        reason or pipeline.get("shutdown_reason") or "SESSION_FINALIZATION"
    ).strip()

    if not reason_text:
        reason_text = "SESSION_FINALIZATION"

    pipeline["shutdown_reason"] = reason_text

    attempt = 0

    with flush_lock:
        while True:
            with pending_lock:
                pending_violations = pipeline.get(
                    "pending_violations",
                    [],
                )

                if pending_violations is None:
                    pending_violations = []

                    pipeline["pending_violations"] = pending_violations

                if not pending_violations:
                    completed_event.set()

                    print(
                        "[API] Final evidence flush complete "
                        f"| reason={reason_text} "
                        "| pending=0"
                    )

                    return True

                proctoring_api = pipeline.get("proctoring_api")

                proctor_socket = pipeline.get("proctor_socket")

                if proctoring_api is not None:
                    attempt += 1

                    print(
                        "[API] Final evidence flush attempt "
                        f"{attempt} "
                        f"| reason={reason_text} "
                        f"| pending={len(pending_violations)}"
                    )

                    try:
                        remaining_violations = send_pending_violations(
                            proctoring_api=proctoring_api,
                            pending_violations=pending_violations,
                            proctor_socket=proctor_socket,
                            require_all_evidence_files=True,
                        )

                    except Exception as error:
                        print(
                            "[API] Final evidence flush attempt failed:",
                            error,
                        )

                        remaining_violations = pending_violations

                    pipeline["pending_violations"] = remaining_violations

                    if not remaining_violations:
                        completed_event.set()

                        print(
                            "[API] Every queued violation and evidence file "
                            "was persisted successfully "
                            f"| reason={reason_text}"
                        )

                        return True

                else:
                    print(
                        "[API] Proctoring API unavailable during final "
                        "evidence flush. Retrying before kiosk shutdown."
                    )

            time.sleep(FINAL_EVIDENCE_RETRY_DELAY_SECONDS)


def empty_voice_anomaly_result():
    return {
        "event_type": "VOICE_DETECTED",
        # `active` means anomaly-active. Human speech before the cumulative
        # threshold is TRACKING only and deliberately remains inactive.
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
        "completed_audio_evidence": None,
        "_voice_incident_active": False,
        "_voice_incident_started_at": None,
        "_voice_last_activity_at": None,
        "_voice_silence_started_at": None,
        "_voice_speech_active": False,
        "_voice_incident_captured": False,
        "_voice_incident_number": 0,
        "_voice_core_incident_events_seen": False,
        "_voice_incident_client_captured_at": None,
        "_voice_incident_initial_metadata": {},
    }


def configure_voice_anomaly_for_production(
    anomaly_manager,
):
    """
    Match the validated test_v2 VOICE_DETECTED confirmation behavior.

    VoiceActivityDetector owns:
    - human-speech classification,
    - cumulative speech accumulation,
    - the 1.5-second confirmation threshold,
    - the 5-second continuous-silence incident boundary.

    Therefore AnomalyManager must accept the already-confirmed VOICE_DETECTED
    event immediately instead of applying another multi-second confirmation.
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
            "core-confirmed voice events will use the manager defaults."
        )
        return False

    voice_rule = rules.get("VOICE_DETECTED")

    if not isinstance(
        voice_rule,
        dict,
    ):
        print(
            "[AUDIO] Warning: VOICE_DETECTED anomaly rule is unavailable; "
            "core-confirmed voice events will use the manager defaults."
        )
        return False

    # The cumulative speech threshold is already enforced by
    # VoiceActivityDetector. Do not apply a second duration gate here.
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


def _start_voice_tracking_incident(
    result,
    now,
    voice_incident_recorder=None,
    incident_number=None,
    core_event=False,
):
    """
    Start a logical voice incident without declaring a violation.

    This mirrors test_v2: speech can be tracked before the cumulative
    confirmation threshold is reached.
    """
    if result.get(
        "_voice_incident_active",
        False,
    ):
        if core_event:
            result["_voice_core_incident_events_seen"] = True

        return result

    previous_number = int(
        result.get(
            "_voice_incident_number",
            0,
        )
        or 0
    )

    if incident_number is None:
        incident_number = previous_number + 1

    else:
        try:
            incident_number = int(incident_number)

        except (
            TypeError,
            ValueError,
        ):
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
            "completed_audio_evidence": None,
            "_voice_incident_active": True,
            "_voice_incident_started_at": now,
            "_voice_last_activity_at": now,
            "_voice_silence_started_at": None,
            "_voice_speech_active": True,
            "_voice_incident_captured": False,
            "_voice_incident_number": incident_number,
            "_voice_incident_client_captured_at": None,
            "_voice_incident_initial_metadata": {},
        }
    )

    if core_event:
        result["_voice_core_incident_events_seen"] = True

    if voice_incident_recorder is not None:
        try:
            recorder_started = voice_incident_recorder.start()

            if not recorder_started:
                print(
                    "[AUDIO][VOICE EVIDENCE WARNING] "
                    "Incident recorder could not start from pre-roll. "
                    "Tracking will continue."
                )

        except Exception as error:
            print(
                "[AUDIO][VOICE EVIDENCE WARNING] " "Unable to start incident recorder:",
                error,
            )

    print(
        "[AUDIO][VOICE TRACKING STARTED] "
        f"incident={incident_number} "
        f"| threshold={VOICE_TRIGGER_SECONDS:.1f}s cumulative speech"
    )

    return result


def _refresh_voice_tracking_state(
    result,
    now,
):
    if not result.get(
        "_voice_incident_active",
        False,
    ):
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

        except (
            TypeError,
            ValueError,
        ):
            result["silence_duration_seconds"] = 0.0

    result["required_duration"] = VOICE_TRIGGER_SECONDS
    result["short_gap_grace_seconds"] = VOICE_SHORT_GAP_GRACE_SECONDS
    result["incident_end_silence_seconds"] = VOICE_INCIDENT_END_SILENCE_SECONDS

    if not result.get(
        "confirmed",
        False,
    ):
        # Human speech is being tracked, but it has not yet accumulated enough
        # actual speech time to be a violation.
        result["active"] = False

    else:
        # After confirmation, natural pauses remain part of the same incident.
        result["active"] = True

    return result


def _get_evidence_capture_timestamp(
    evidence,
):
    if not isinstance(
        evidence,
        dict,
    ):
        return None

    event_payload = evidence.get("event")

    if isinstance(
        event_payload,
        dict,
    ):
        captured_at = event_payload.get("captured_at")

        if captured_at:
            return captured_at

    captured_at = evidence.get("client_captured_at")

    if captured_at:
        return captured_at

    return None


def _build_completed_voice_api_violation(
    completed_evidence,
    result,
    incident_number,
    incident_duration,
    silence_elapsed,
    recorded_audio,
    forced_finalize=False,
    finalize_reason=None,
):
    if not isinstance(
        completed_evidence,
        dict,
    ):
        return None

    file_path = completed_evidence.get("file_path") or completed_evidence.get(
        "audio_path"
    )

    if not file_path:
        return None

    initial_metadata = result.get(
        "_voice_incident_initial_metadata",
        {},
    )

    if not isinstance(
        initial_metadata,
        dict,
    ):
        initial_metadata = {}

    metadata = dict(initial_metadata)

    cumulative_voice_duration = float(
        result.get(
            "cumulative_voice_duration_seconds",
            result.get(
                "duration",
                0.0,
            ),
        )
        or 0.0
    )

    metadata.update(
        {
            "incident_number": incident_number,
            "incident_duration_seconds": round(
                incident_duration,
                3,
            ),
            "cumulative_voice_duration_seconds": round(
                cumulative_voice_duration,
                3,
            ),
            "confirmation_threshold_seconds": VOICE_TRIGGER_SECONDS,
            "pause_time_excluded": True,
            "continuous_silence_seconds": round(
                silence_elapsed,
                3,
            ),
            "recorded_audio_duration_seconds": (
                recorded_audio.get("duration_seconds")
                if isinstance(
                    recorded_audio,
                    dict,
                )
                else None
            ),
            "recording_started_on_incident_start": True,
            "continuous_audio_evidence": True,
            "evidence_write_deferred_until_incident_end": True,
            "voice_incident_end_silence_seconds": (VOICE_INCIDENT_END_SILENCE_SECONDS),
            "voice_evidence_pre_roll_seconds": (VOICE_EVIDENCE_PRE_ROLL_SECONDS),
            "evidence_type": "audio",
            "audio_sample_rate": completed_evidence.get("sample_rate"),
            "audio_channels": completed_evidence.get(
                "channels",
                1,
            ),
            "audio_sample_width": completed_evidence.get(
                "sample_width",
                2,
            ),
            "sample_rate_change_detected": bool(
                recorded_audio.get(
                    "sample_rate_change_detected",
                    False,
                )
                if isinstance(
                    recorded_audio,
                    dict,
                )
                else False
            ),
            "forced_incident_finalize": bool(forced_finalize),
        }
    )

    if finalize_reason:
        metadata["voice_incident_finalize_reason"] = str(finalize_reason)

    client_captured_at = result.get("_voice_incident_client_captured_at")

    if not client_captured_at:
        client_captured_at = _get_evidence_capture_timestamp(completed_evidence)

    if not client_captured_at:
        client_captured_at = datetime.now(timezone.utc).isoformat()

    return {
        "violation_type": "VOICE_DETECTED",
        "client_captured_at": client_captured_at,
        "metadata": metadata,
        "file_path": str(file_path),
    }


def _update_audio_anomaly_with_lock(
    anomaly_manager,
    anomaly_manager_lock=None,
    **kwargs,
):
    if anomaly_manager_lock is None:
        return anomaly_manager.update_audio(**kwargs)

    with anomaly_manager_lock:
        return anomaly_manager.update_audio(**kwargs)


def _finalize_voice_incident(
    result,
    anomaly_manager,
    now,
    voice_incident_recorder=None,
    evidence_store=None,
    anomaly_manager_lock=None,
    cumulative_voice_duration=None,
    continuous_silence=None,
    confirmed=None,
    force=False,
    finalize_reason=None,
    ended_by_core=False,
):
    """
    Close one logical voice incident.

    Unconfirmed tracking incidents are discarded without evidence/API/socket
    violation creation. Confirmed incidents persist the held WAV and create the
    final file-backed REST violation while the real-time socket notification has
    already been emitted at confirmation time.
    """
    if not result.get(
        "_voice_incident_active",
        False,
    ):
        return (
            result,
            None,
        )

    incident_number = int(
        result.get(
            "_voice_incident_number",
            0,
        )
        or 0
    )

    was_confirmed = bool(
        result.get(
            "confirmed",
            False,
        )
        if confirmed is None
        else confirmed
    )

    if cumulative_voice_duration is None:
        cumulative_voice_duration = float(
            result.get(
                "cumulative_voice_duration_seconds",
                result.get(
                    "duration",
                    0.0,
                ),
            )
            or 0.0
        )

    else:
        cumulative_voice_duration = float(cumulative_voice_duration or 0.0)

    if continuous_silence is None:
        continuous_silence = _voice_silence_elapsed(
            result,
            now,
        )

    else:
        continuous_silence = float(continuous_silence or 0.0)

    result["cumulative_voice_duration_seconds"] = cumulative_voice_duration
    result["duration"] = cumulative_voice_duration

    incident_duration = _voice_incident_elapsed(
        result,
        now,
    )

    completed_evidence = None
    completed_api_violation = None
    recorded_audio = None

    if was_confirmed:
        if voice_incident_recorder is not None:
            try:
                recorded_audio = voice_incident_recorder.stop()

            except Exception as error:
                print(
                    "[AUDIO][VOICE EVIDENCE STOP ERROR] "
                    f"incident={incident_number} "
                    f"| error={error}"
                )

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
                    "cumulative_voice_duration_seconds": round(
                        cumulative_voice_duration,
                        3,
                    ),
                    "confirmation_threshold_seconds": VOICE_TRIGGER_SECONDS,
                    "pause_time_excluded": True,
                    "continuous_silence_seconds": round(
                        continuous_silence,
                        3,
                    ),
                    "recorded_audio_duration_seconds": recorded_audio.get(
                        "duration_seconds"
                    ),
                    "recording_started_on_incident_start": True,
                    "continuous_audio_evidence": True,
                    "evidence_write_deferred_until_incident_end": True,
                    "voice_incident_end_silence_seconds": (
                        VOICE_INCIDENT_END_SILENCE_SECONDS
                    ),
                    "voice_evidence_pre_roll_seconds": (
                        VOICE_EVIDENCE_PRE_ROLL_SECONDS
                    ),
                    "sample_rate_change_detected": bool(
                        recorded_audio.get(
                            "sample_rate_change_detected",
                            False,
                        )
                    ),
                    "forced_incident_finalize": bool(force),
                    "ended_by_core_incident_event": bool(ended_by_core),
                }

                if finalize_reason:
                    evidence_metadata["voice_incident_finalize_reason"] = str(
                        finalize_reason
                    )

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
                        completed_api_violation = _build_completed_voice_api_violation(
                            completed_evidence=completed_evidence,
                            result=result,
                            incident_number=incident_number,
                            incident_duration=incident_duration,
                            silence_elapsed=continuous_silence,
                            recorded_audio=recorded_audio,
                            forced_finalize=force,
                            finalize_reason=finalize_reason,
                        )

                        print(
                            "[AUDIO][VOICE EVIDENCE SAVED] "
                            f"incident={incident_number} "
                            f"| cumulative_speech="
                            f"{cumulative_voice_duration:.2f}s "
                            f"| recorded_duration="
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

        ended_result = _update_audio_anomaly_with_lock(
            anomaly_manager=anomaly_manager,
            anomaly_manager_lock=anomaly_manager_lock,
            event_type="VOICE_DETECTED",
            active=False,
            audio_evidence=None,
            metadata={
                "incident_number": incident_number,
                "cumulative_voice_duration_seconds": round(
                    cumulative_voice_duration,
                    3,
                ),
                "confirmation_threshold_seconds": VOICE_TRIGGER_SECONDS,
                "pause_time_excluded": True,
                "continuous_silence_seconds": round(
                    continuous_silence,
                    3,
                ),
                "ended_by_core_incident_event": bool(ended_by_core),
                "forced_incident_finalize": bool(force),
                "voice_incident_finalize_reason": (
                    str(finalize_reason) if finalize_reason else None
                ),
            },
        )

    else:
        # Tracking never reached the cumulative speech threshold, therefore it
        # must not become an anomaly and must not persist evidence.
        if voice_incident_recorder is not None:
            try:
                voice_incident_recorder.discard()

            except Exception:
                pass

        ended_result = None

    fresh = empty_voice_anomaly_result()
    fresh["_voice_incident_number"] = incident_number
    fresh["_voice_core_incident_events_seen"] = bool(
        result.get(
            "_voice_core_incident_events_seen",
            False,
        )
        or ended_by_core
    )

    if isinstance(
        ended_result,
        dict,
    ):
        fresh["cooldown"] = float(
            ended_result.get(
                "cooldown",
                0.0,
            )
            or 0.0
        )

        fresh["cooldown_remaining"] = float(
            ended_result.get(
                "cooldown_remaining",
                0.0,
            )
            or 0.0
        )

    fresh["completed_audio_evidence"] = completed_evidence

    print(
        "[AUDIO][VOICE INCIDENT ENDED] "
        f"incident={incident_number} "
        f"| cumulative_speech={cumulative_voice_duration:.2f}s "
        f"| continuous_silence={continuous_silence:.2f}s "
        f"| anomaly={was_confirmed} "
        f"| forced={bool(force)}"
    )

    return (
        fresh,
        completed_api_violation,
    )


def _legacy_finish_voice_incident_if_needed(
    result,
    anomaly_manager,
    now,
    voice_incident_recorder=None,
    evidence_store=None,
    anomaly_manager_lock=None,
):
    """
    Local 5-second silence safeguard for the validated test_v2 incident model.

    AudioMonitor may emit VOICE_INCIDENT_STARTED/ENDED, but production must not
    depend exclusively on the final INCIDENT_ENDED event. Once speech pauses,
    the local state machine tracks continuous silence itself and closes the
    incident after VOICE_INCIDENT_END_SILENCE_SECONDS.

    This preserves test_v2 behavior even if a core incident-end event is delayed
    or missed:
    - speech resumes before 5 seconds -> same incident continues;
    - cumulative human-speech duration is preserved;
    - silence is never added to the speech total;
    - 5 continuous seconds without speech -> incident closes.
    """
    result = _refresh_voice_tracking_state(
        result,
        now,
    )

    if not result.get(
        "_voice_incident_active",
        False,
    ):
        return (
            result,
            None,
        )

    silence_elapsed = float(
        result.get(
            "silence_duration_seconds",
            0.0,
        )
        or 0.0
    )

    if silence_elapsed < VOICE_INCIDENT_END_SILENCE_SECONDS:
        return (
            result,
            None,
        )

    return _finalize_voice_incident(
        result=result,
        anomaly_manager=anomaly_manager,
        now=now,
        voice_incident_recorder=voice_incident_recorder,
        evidence_store=evidence_store,
        anomaly_manager_lock=anomaly_manager_lock,
        continuous_silence=silence_elapsed,
        force=False,
        ended_by_core=False,
    )


def _finish_voice_incident_if_silent(
    result,
    anomaly_manager,
    now,
    voice_incident_recorder=None,
    evidence_store=None,
    anomaly_manager_lock=None,
    force=False,
    finalize_reason=None,
):
    """
    Backward-compatible wrapper retained for existing callers.

    Normal operation delegates to the legacy silence fallback only when the
    installed AudioMonitor does not provide logical incident boundary events.
    Shutdown force-finalization always closes the currently tracked incident.
    """
    if force:
        return _finalize_voice_incident(
            result=result,
            anomaly_manager=anomaly_manager,
            now=now,
            voice_incident_recorder=voice_incident_recorder,
            evidence_store=evidence_store,
            anomaly_manager_lock=anomaly_manager_lock,
            force=True,
            finalize_reason=finalize_reason,
            ended_by_core=False,
        )

    return _legacy_finish_voice_incident_if_needed(
        result=result,
        anomaly_manager=anomaly_manager,
        now=now,
        voice_incident_recorder=voice_incident_recorder,
        evidence_store=evidence_store,
        anomaly_manager_lock=anomaly_manager_lock,
    )


def process_audio_events(
    audio_event_queue,
    anomaly_manager,
    current_result=None,
    tracking_enabled=True,
    anomaly_manager_lock=None,
    voice_incident_recorder=None,
    evidence_store=None,
    force_finalize=False,
    finalize_reason=None,
):
    """
    Production version of the validated test_v2 voice state machine.

    Backward compatibility:
    - Existing positional arguments remain valid.
    - Recorder/evidence/finalization arguments remain optional.
    - Return value remains (result, new_api_violations).

    Detection behavior:
    - Proper human speech starts TRACKING, not a violation.
    - Only actual human-speech time contributes to the cumulative threshold.
    - Pause/silence time contributes zero seconds.
    - Speech returning before 5 continuous seconds of silence stays in the same
      logical incident and keeps the previous cumulative speech total.
    - VOICE_DETECTED is confirmed only after 1.5 seconds cumulative speech.
    - Once confirmed, short pauses do not deactivate the violation.
    - The logical incident closes after 5 continuous seconds without speech.

    Production evidence behavior:
    - Original PCM starts recording when the logical incident starts.
    - At confirmation, AnomalyManager gets the lightweight deferred-audio marker
      so the Socket.IO violation can be emitted immediately.
    - The placeholder marker is NOT queued to REST.
    - When the incident ends, the complete WAV is persisted and the final
      file-backed violation is queued for REST.
    """
    result = dict(current_result or empty_voice_anomaly_result())

    new_api_violations = []

    if audio_event_queue is None or anomaly_manager is None:
        return (
            result,
            new_api_violations,
        )

    if not tracking_enabled:
        return (
            result,
            new_api_violations,
        )

    now = time.monotonic()

    (
        result,
        completed_api_violation,
    ) = _finish_voice_incident_if_silent(
        result=result,
        anomaly_manager=anomaly_manager,
        now=now,
        voice_incident_recorder=voice_incident_recorder,
        evidence_store=evidence_store,
        anomaly_manager_lock=anomaly_manager_lock,
        force=False,
    )

    if isinstance(
        completed_api_violation,
        dict,
    ):
        new_api_violations.append(dict(completed_api_violation))

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

        if event_type == "VOICE_INCIDENT_STARTED":
            result = _start_voice_tracking_incident(
                result=result,
                now=now,
                voice_incident_recorder=voice_incident_recorder,
                incident_number=payload.get("incident_number"),
                core_event=True,
            )

            continue

        if event_type == "VOICE_ACTIVITY_STARTED":
            if not result.get(
                "_voice_incident_active",
                False,
            ):
                result = _start_voice_tracking_incident(
                    result=result,
                    now=now,
                    voice_incident_recorder=voice_incident_recorder,
                    incident_number=payload.get("incident_number"),
                    core_event=False,
                )

            result["_voice_speech_active"] = True
            result["_voice_last_activity_at"] = now
            result["_voice_silence_started_at"] = None
            result["silence_duration_seconds"] = 0.0

            continue

        if event_type == "VOICE_ACTIVITY_ENDED":
            if result.get(
                "_voice_incident_active",
                False,
            ):
                result["_voice_speech_active"] = False

                if result.get("_voice_silence_started_at") is None:
                    result["_voice_silence_started_at"] = now

                    print(
                        "[AUDIO][VOICE PAUSE] "
                        "Speech stopped; cumulative speech is preserved. "
                        f"Waiting {VOICE_INCIDENT_END_SILENCE_SECONDS:.1f}s "
                        "of continuous silence before ending the incident."
                    )

                result = _refresh_voice_tracking_state(
                    result,
                    now,
                )

            continue

        if event_type == "VOICE_DETECTED":
            if not result.get(
                "_voice_incident_active",
                False,
            ):
                result = _start_voice_tracking_incident(
                    result=result,
                    now=now,
                    voice_incident_recorder=voice_incident_recorder,
                    incident_number=payload.get("incident_number"),
                    core_event=False,
                )

            cumulative_voice_duration = float(
                payload.get(
                    "cumulative_voice_duration_seconds",
                    payload.get(
                        "voice_duration_seconds",
                        VOICE_TRIGGER_SECONDS,
                    ),
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
                    "incident_number": result.get(
                        "_voice_incident_number",
                        0,
                    ),
                    "cumulative_voice_duration_seconds": round(
                        cumulative_voice_duration,
                        3,
                    ),
                    "confirmation_threshold_seconds": VOICE_TRIGGER_SECONDS,
                    "incident_end_silence_seconds": (
                        VOICE_INCIDENT_END_SILENCE_SECONDS
                    ),
                    "pause_time_excluded": True,
                    "continuous_audio_evidence": True,
                    "evidence_write_deferred_until_incident_end": True,
                }
            )

            manager_result = _update_audio_anomaly_with_lock(
                anomaly_manager=anomaly_manager,
                anomaly_manager_lock=anomaly_manager_lock,
                event_type="VOICE_DETECTED",
                active=True,
                audio_evidence=audio_evidence,
                metadata=metadata,
            )

            if not isinstance(
                manager_result,
                dict,
            ):
                manager_result = {}

            previous_incident_captured = bool(
                result.get(
                    "_voice_incident_captured",
                    False,
                )
            )

            previous_client_captured_at = result.get(
                "_voice_incident_client_captured_at"
            )

            previous_initial_metadata = result.get(
                "_voice_incident_initial_metadata",
                {},
            )

            if not isinstance(
                previous_initial_metadata,
                dict,
            ):
                previous_initial_metadata = {}

            immediate_api_violation = manager_result.get("api_violation")

            if not previous_client_captured_at and isinstance(
                immediate_api_violation,
                dict,
            ):
                previous_client_captured_at = immediate_api_violation.get(
                    "client_captured_at"
                )

            if not previous_client_captured_at:
                previous_client_captured_at = (
                    payload.get("timestamp")
                    or payload.get("captured_at")
                    or datetime.now(timezone.utc).isoformat()
                )

            if not previous_initial_metadata:
                previous_initial_metadata = dict(metadata)

            # Keep the production-only tracking fields that are not returned by
            # AnomalyManager.
            manager_result["_voice_incident_active"] = True
            manager_result["_voice_incident_started_at"] = result.get(
                "_voice_incident_started_at"
            )
            manager_result["_voice_last_activity_at"] = now
            manager_result["_voice_silence_started_at"] = None
            manager_result["_voice_speech_active"] = True
            manager_result["_voice_incident_number"] = result.get(
                "_voice_incident_number",
                0,
            )
            manager_result["_voice_core_incident_events_seen"] = bool(
                result.get(
                    "_voice_core_incident_events_seen",
                    False,
                )
            )
            manager_result["_voice_incident_client_captured_at"] = (
                previous_client_captured_at
            )
            manager_result["_voice_incident_initial_metadata"] = (
                previous_initial_metadata
            )
            manager_result["_voice_incident_captured"] = bool(
                previous_incident_captured
                or manager_result.get(
                    "captured",
                    False,
                )
            )

            manager_result["active"] = True
            manager_result["confirmed"] = True
            manager_result["captured"] = bool(
                manager_result["_voice_incident_captured"]
            )
            manager_result["duration"] = cumulative_voice_duration
            manager_result["required_duration"] = VOICE_TRIGGER_SECONDS
            manager_result["incident_duration_seconds"] = cumulative_voice_duration
            manager_result["cumulative_voice_duration_seconds"] = (
                cumulative_voice_duration
            )
            manager_result["silence_duration_seconds"] = 0.0
            manager_result["short_gap_grace_seconds"] = VOICE_SHORT_GAP_GRACE_SECONDS
            manager_result["incident_end_silence_seconds"] = (
                VOICE_INCIDENT_END_SILENCE_SECONDS
            )

            # Important: this immediate api_violation belongs to the real-time
            # socket marker and intentionally has no final WAV path. It is NOT
            # appended to REST. REST receives the file-backed violation when the
            # incident is finalized.
            result = manager_result

            if result.get(
                "captured",
                False,
            ):
                print(
                    "[AUDIO][VOICE VIOLATION CONFIRMED] "
                    f"incident={result.get('_voice_incident_number', 0)} "
                    f"| cumulative_speech={cumulative_voice_duration:.2f}s "
                    f"| threshold={VOICE_TRIGGER_SECONDS:.1f}s "
                    "| socket event emitted immediately; "
                    "continuous WAV recording remains active."
                )

            else:
                print(
                    "[AUDIO][VOICE VIOLATION CONFIRMED] "
                    f"incident={result.get('_voice_incident_number', 0)} "
                    f"| cumulative_speech={cumulative_voice_duration:.2f}s "
                    f"| threshold={VOICE_TRIGGER_SECONDS:.1f}s "
                    "| no new evidence/socket marker due to "
                    "existing incident/cooldown."
                )

            continue

        if event_type == "VOICE_INCIDENT_ENDED":
            result["_voice_core_incident_events_seen"] = True

            cumulative_voice_duration = float(
                payload.get(
                    "cumulative_voice_duration_seconds",
                    result.get(
                        "cumulative_voice_duration_seconds",
                        0.0,
                    ),
                )
                or 0.0
            )

            continuous_silence = float(
                payload.get(
                    "continuous_silence_seconds",
                    result.get(
                        "silence_duration_seconds",
                        0.0,
                    ),
                )
                or 0.0
            )

            # Keep production behavior strictly aligned with test_v2's contract:
            # an incident may end only after a full 5-second stretch with no
            # further detected speech. If an early/stale core event arrives,
            # remain in HOLD and let either resumed speech continue the same
            # incident or the local silence safeguard close it at 5 seconds.
            if continuous_silence < VOICE_INCIDENT_END_SILENCE_SECONDS:
                if result.get(
                    "_voice_incident_active",
                    False,
                ):
                    result["_voice_speech_active"] = False

                    if result.get("_voice_silence_started_at") is None:
                        result["_voice_silence_started_at"] = now - max(
                            0.0, continuous_silence
                        )

                    result = _refresh_voice_tracking_state(
                        result,
                        now,
                    )

                continue

            (
                result,
                completed_api_violation,
            ) = _finalize_voice_incident(
                result=result,
                anomaly_manager=anomaly_manager,
                now=now,
                voice_incident_recorder=voice_incident_recorder,
                evidence_store=evidence_store,
                anomaly_manager_lock=anomaly_manager_lock,
                cumulative_voice_duration=cumulative_voice_duration,
                continuous_silence=continuous_silence,
                confirmed=bool(
                    payload.get(
                        "confirmed",
                        result.get(
                            "confirmed",
                            False,
                        ),
                    )
                ),
                force=False,
                ended_by_core=True,
            )

            if isinstance(
                completed_api_violation,
                dict,
            ):
                new_api_violations.append(dict(completed_api_violation))

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
                if key != "evidence_audio"
            }

            print(
                f"[AUDIO][{event_type}]",
                safe_payload,
            )

    now = time.monotonic()

    (
        result,
        completed_api_violation,
    ) = _finish_voice_incident_if_silent(
        result=result,
        anomaly_manager=anomaly_manager,
        now=now,
        voice_incident_recorder=voice_incident_recorder,
        evidence_store=evidence_store,
        anomaly_manager_lock=anomaly_manager_lock,
        force=bool(force_finalize),
        finalize_reason=finalize_reason,
    )

    if isinstance(
        completed_api_violation,
        dict,
    ):
        new_api_violations.append(dict(completed_api_violation))

    result = _refresh_voice_tracking_state(
        result,
        time.monotonic(),
    )

    return (
        result,
        new_api_violations,
    )


def discard_pretracking_audio_events(
    audio_event_queue,
):
    """
    Remove audio events produced before frontend tracking starts.

    Important:
    - Does NOT reset VoiceActivityDetector.
    - Does NOT call AnomalyManager.
    - Prevents pre-exam speech from becoming a violation.
    - Keeps the live AudioMonitor/microphone running for device checks.
    """
    if audio_event_queue is None:
        return 0

    discarded = 0

    while True:
        try:
            audio_event_queue.get_nowait()
            discarded += 1

        except queue.Empty:
            break

    return discarded


def reset_audio_tracking_state(
    pipeline,
):
    """
    Start production audio tracking from the same clean detector state used by
    the working test_v2 flow.

    Camera/microphone are intentionally opened before the secure exam page is
    ready. Any voice activity produced during that bootstrap period must not
    leak into the real assessment incident state.
    """

    audio_event_queue = pipeline.get("audio_event_queue")

    # Remove everything emitted before the validated frontend tracking-start.
    discard_pretracking_audio_events(audio_event_queue)

    voice_incident_recorder = pipeline.get("voice_incident_recorder")

    if voice_incident_recorder is not None:
        try:
            voice_incident_recorder.discard()
        except Exception:
            pass

    audio_monitor = pipeline.get("audio_monitor")

    if audio_monitor is not None:
        clear_audio_buffer = getattr(
            audio_monitor,
            "clear_audio_buffer",
            None,
        )

        if callable(clear_audio_buffer):
            try:
                clear_audio_buffer()
            except Exception:
                pass

        voice_detector = getattr(
            audio_monitor,
            "voice_detector",
            None,
        )

        reset_detector = getattr(
            voice_detector,
            "reset",
            None,
        )

        if callable(reset_detector):
            try:
                reset_detector(recalibrate=True)

            except TypeError:
                reset_detector()

        # AudioMonitor uses these edge-state flags to decide when to emit
        # VOICE_ACTIVITY_STARTED / VOICE_DETECTED. Reset them alongside VAD so
        # the first real assessment speech always begins a fresh incident.
        try:
            audio_monitor._last_voice_active = False
        except Exception:
            pass

        try:
            audio_monitor._last_confirmed = False
        except Exception:
            pass

        set_status = getattr(
            audio_monitor,
            "_set_status",
            None,
        )

        if callable(set_status):
            try:
                set_status(
                    calibrating=True,
                    voice_active=False,
                    voice_confirmed=False,
                    voice_duration_seconds=0.0,
                    cumulative_voice_duration_seconds=0.0,
                    silence_duration_seconds=0.0,
                    incident_active=False,
                    vad_speech=False,
                    whisper_candidate=False,
                    detection_source=None,
                )
            except Exception:
                pass

    # Reset once more after detector reset so no stale callback event created
    # during bootstrap can survive into the tracked assessment.
    discard_pretracking_audio_events(audio_event_queue)

    pipeline["audio_anomaly_result"] = empty_voice_anomaly_result()
    pipeline["audio_tracking_prepared"] = True

    print(
        "[AUDIO] Tracking-start reset complete. "
        "Voice detection begins from a clean incident state."
    )


def _append_audio_api_violations(
    pipeline,
    violations,
):
    if not violations:
        return

    pending_violations_lock = pipeline.get("pending_violations_lock")

    if pending_violations_lock is None:
        pending_violations_lock = threading.RLock()
        pipeline["pending_violations_lock"] = pending_violations_lock

    with pending_violations_lock:
        pending_violations = pipeline.get(
            "pending_violations",
            [],
        )

        if pending_violations is None:
            pending_violations = []

        pending_violations.extend(
            dict(item)
            for item in violations
            if isinstance(
                item,
                dict,
            )
        )

        pipeline["pending_violations"] = pending_violations


def run_audio_tracking_worker(
    pipeline,
):
    """
    Dedicated low-cost audio consumer.

    The preview/test processes audio immediately from AudioMonitor's queue.
    In production, doing that work inside the heavy camera/vision loop can
    delay VOICE_DETECTED handling whenever vision inference or REST I/O takes
    longer than expected. This worker preserves the same direct
    AudioMonitor -> queue -> AnomalyManager path while running independently
    from the vision loop.

    The worker also owns full voice-incident finalization. On normal operation
    it waits for the configured silence hold; on shutdown it force-finalizes
    any active recording before the final REST evidence flush.

    Tracking remains gated by tracking_start_event. Pre-tracking queue
    cleanup is performed synchronously by before_tracking_start immediately
    before the event is set.
    """
    audio_event_queue = pipeline.get("audio_event_queue")
    anomaly_manager = pipeline.get("anomaly_manager")
    tracking_start_event = pipeline.get("tracking_start_event")
    anomaly_manager_lock = pipeline.get("anomaly_manager_lock")
    voice_incident_recorder = pipeline.get("voice_incident_recorder")
    evidence_store = pipeline.get("evidence_store")

    if anomaly_manager_lock is None:
        anomaly_manager_lock = threading.RLock()
        pipeline["anomaly_manager_lock"] = anomaly_manager_lock

    stop_event = pipeline.get("audio_worker_stop_event")

    if stop_event is None:
        stop_event = threading.Event()
        pipeline["audio_worker_stop_event"] = stop_event

    audio_anomaly_result = pipeline.get("audio_anomaly_result")

    if not isinstance(
        audio_anomaly_result,
        dict,
    ):
        audio_anomaly_result = empty_voice_anomaly_result()
        pipeline["audio_anomaly_result"] = audio_anomaly_result

    print("[AUDIO] Dedicated real-time tracking worker started.")

    try:
        while not stop_event.is_set():
            tracking_enabled = (
                True if tracking_start_event is None else tracking_start_event.is_set()
            )

            if not tracking_enabled:
                stop_event.wait(0.02)
                continue

            (
                audio_anomaly_result,
                new_audio_violations,
            ) = process_audio_events(
                audio_event_queue=audio_event_queue,
                anomaly_manager=anomaly_manager,
                current_result=audio_anomaly_result,
                tracking_enabled=True,
                anomaly_manager_lock=anomaly_manager_lock,
                voice_incident_recorder=voice_incident_recorder,
                evidence_store=evidence_store,
            )

            pipeline["audio_anomaly_result"] = audio_anomaly_result

            _append_audio_api_violations(
                pipeline=pipeline,
                violations=new_audio_violations,
            )

            stop_event.wait(0.01)

    finally:
        tracking_enabled = (
            True if tracking_start_event is None else tracking_start_event.is_set()
        )

        if tracking_enabled:
            (
                audio_anomaly_result,
                final_audio_violations,
            ) = process_audio_events(
                audio_event_queue=audio_event_queue,
                anomaly_manager=anomaly_manager,
                current_result=audio_anomaly_result,
                tracking_enabled=True,
                anomaly_manager_lock=anomaly_manager_lock,
                voice_incident_recorder=voice_incident_recorder,
                evidence_store=evidence_store,
                force_finalize=True,
                finalize_reason=(
                    pipeline.get("shutdown_reason") or "AUDIO_WORKER_STOP"
                ),
            )

            pipeline["audio_anomaly_result"] = audio_anomaly_result

            _append_audio_api_violations(
                pipeline=pipeline,
                violations=final_audio_violations,
            )

        print("[AUDIO] Dedicated real-time tracking worker stopped.")


def start_audio_tracking_worker(
    pipeline,
):
    if not isinstance(
        pipeline,
        dict,
    ):
        return False

    existing_thread = pipeline.get("audio_worker_thread")

    if existing_thread is not None and existing_thread.is_alive():
        return True

    stop_event = pipeline.get("audio_worker_stop_event")

    if stop_event is None:
        stop_event = threading.Event()
        pipeline["audio_worker_stop_event"] = stop_event

    stop_event.clear()

    thread = threading.Thread(
        target=run_audio_tracking_worker,
        args=(pipeline,),
        name="SkolariqAudioTrackingWorker",
        daemon=True,
    )

    pipeline["audio_worker_thread"] = thread

    thread.start()

    return True


def stop_audio_tracking_worker(
    pipeline,
    timeout=3.0,
):
    if not isinstance(
        pipeline,
        dict,
    ):
        return

    stop_event = pipeline.get("audio_worker_stop_event")

    if stop_event is not None:
        stop_event.set()

    thread = pipeline.get("audio_worker_thread")

    if (
        thread is not None
        and thread.is_alive()
        and thread is not threading.current_thread()
    ):
        thread.join(
            timeout=max(
                0.0,
                float(timeout),
            )
        )

        if thread.is_alive():
            print(
                "[AUDIO] Waiting for active voice evidence "
                "to finish finalizing before shutdown..."
            )

            thread.join()

    pipeline["audio_worker_thread"] = None


def run_proctoring_detection_loop(
    pipeline,
):
    global exam_completed_flag

    camera = pipeline["camera"]

    face_detector = pipeline["face_detector"]

    face_landmarker = pipeline["face_landmarker"]

    gaze_tracker = pipeline["gaze_tracker"]

    head_tracker = pipeline["head_tracker"]

    pose_landmarker = pipeline["pose_landmarker"]

    posture_monitor = pipeline["posture_monitor"]

    object_detector = pipeline["object_detector"]

    anomaly_manager = pipeline["anomaly_manager"]

    anomaly_manager_lock = pipeline.get("anomaly_manager_lock")

    if anomaly_manager_lock is None:
        anomaly_manager_lock = threading.RLock()
        pipeline["anomaly_manager_lock"] = anomaly_manager_lock

    proctoring_api = pipeline.get("proctoring_api")

    proctor_socket = pipeline.get("proctor_socket")

    audio_monitor = pipeline.get("audio_monitor")

    pending_violations = pipeline.get("pending_violations")

    if pending_violations is None:
        pending_violations = []

        pipeline["pending_violations"] = pending_violations

    pending_violations_lock = pipeline.get("pending_violations_lock")

    if pending_violations_lock is None:
        pending_violations_lock = threading.RLock()

        pipeline["pending_violations_lock"] = pending_violations_lock

    shutdown_requested_event = pipeline.get("shutdown_requested_event")

    if shutdown_requested_event is None:
        shutdown_requested_event = threading.Event()

        pipeline["shutdown_requested_event"] = shutdown_requested_event

    tracking_start_event = pipeline.get("tracking_start_event")

    if tracking_start_event is None:
        tracking_start_event = threading.Event()

        tracking_start_event.set()

        pipeline["tracking_start_event"] = tracking_start_event

    frame_count = 0

    last_log_time = 0.0

    last_waiting_log_time = 0.0

    tracking_started_logged = False

    print()

    if tracking_start_event.is_set():
        print("[PROCTOR] Detection pipeline started.")

    else:
        print("[PROCTOR] Camera and microphone are active.")

        print(
            "[PROCTOR] Violation tracking is PAUSED until "
            "the secure exam page signals readiness."
        )

    while True:
        if exam_completed_flag or shutdown_requested_event.is_set():
            print()

            shutdown_reason = pipeline.get("shutdown_reason") or (
                "EXAM_COMPLETE" if exam_completed_flag else "SESSION_FINALIZATION"
            )

            print(
                "[PROCTOR] Finalization requested. "
                f"Stopping detection | reason={shutdown_reason}"
            )

            # The dedicated audio worker owns audio queue consumption and
            # drains any final queued audio before final REST persistence.
            break

        success, frame = camera.read()

        if not success or frame is None:
            print("[CAMERA] Failed to read frame.")

            time.sleep(0.05)

            continue

        if not tracking_start_event.is_set():
            # AudioMonitor remains live for microphone status/device switching,
            # but the dedicated audio worker does not consume or evaluate voice
            # events until the validated tracking-start event is set. The
            # before_tracking_start callback clears pre-tracking audio exactly
            # once immediately before tracking becomes active.
            current_time = time.time()

            if current_time - last_waiting_log_time >= 2.0:
                print(
                    "[PROCTOR] Waiting for secure exam page. "
                    "Violation tracking remains paused."
                )

                if audio_monitor is not None:
                    audio_status = audio_monitor.get_status()

                    print(
                        "[AUDIO] "
                        f"mic_available="
                        f"{audio_status.get('microphone_available', False)} "
                        "| calibrating="
                        f"{audio_status.get('calibrating', False)} "
                        "| tracking=PAUSED"
                    )

                last_waiting_log_time = current_time

            time.sleep(0.02)

            continue

        if not tracking_started_logged:
            tracking_started_logged = True

            print()

            print(
                "[PROCTOR] Frontend readiness confirmed. "
                "Starting violation tracking."
            )

            print("[PROCTOR] Detection pipeline started.")

        frame_count += 1

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

        # Keep production face-count behavior aligned with test_v2.
        # NO_FACE and MULTIPLE_FACES come from the MediaPipe face detector only.
        # Face Landmarker remains responsible for landmarks/gaze/head tracking.
        face_presence = {
            "decision": (
                "NO_FACE"
                if face_count == 0
                else ("MULTIPLE_FACES" if face_count > 1 else "SINGLE_FACE")
            ),
            "no_face": (face_count == 0),
            "face_count": face_count,
            "landmark_valid": landmark_valid,
            "landmark_face_count": (
                landmark_result.get("face_count", 0)
                if isinstance(
                    landmark_result,
                    dict,
                )
                else 0
            ),
            "mediapipe_face_present": (face_count > 0),
        }

        no_face_detected = face_count == 0

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

        object_anomalies = get_object_anomalies(object_detections)

        # Build lightweight, event-specific evidence regions once per frame.
        # The AnomalyManager draws only the regions belonging to the violation
        # that is actually being captured, so saved evidence stays clean and
        # does not contain unrelated detector boxes.
        face_evidence_regions = []

        for face in faces:
            coordinates = get_face_coordinates(face)

            if not isinstance(coordinates, dict):
                continue

            try:
                face_x = int(coordinates.get("x"))
                face_y = int(coordinates.get("y"))
                face_width = int(coordinates.get("width"))
                face_height = int(coordinates.get("height"))
            except (TypeError, ValueError):
                continue

            if face_width <= 0 or face_height <= 0:
                continue

            face_evidence_regions.append(
                {
                    "x": face_x,
                    "y": face_y,
                    "width": face_width,
                    "height": face_height,
                    "evidence_label": "FACE",
                }
            )

        phone_evidence_regions = [
            dict(detection)
            for detection in object_anomalies.get(
                "phone_detections",
                [],
            )
            if isinstance(detection, dict)
        ]

        book_evidence_regions = [
            dict(detection)
            for detection in object_anomalies.get(
                "book_detections",
                [],
            )
            if isinstance(detection, dict)
        ]

        person_evidence_regions = [
            dict(detection)
            for detection in object_anomalies.get(
                "person_detections",
                [],
            )
            if isinstance(detection, dict)
        ]

        evidence_regions = {
            "PHONE_DETECTED": phone_evidence_regions,
            "BOOK_DETECTED": book_evidence_regions,
            "MULTIPLE_FACES": face_evidence_regions,
            "EXTRA_PERSON": person_evidence_regions,
        }

        anomaly_metadata = {
            "frame_number": frame_count,
            "face_count": face_count,
            "landmark_valid": landmark_valid,
            "faces": face_evidence_regions,
            "face_presence": {
                "decision": face_presence.get(
                    "decision",
                    "UNKNOWN",
                ),
                "no_face": no_face_detected,
                "face_count": face_count,
                "mediapipe_face_present": (face_count > 0),
                "landmark_valid": landmark_valid,
                "landmark_face_count": face_presence.get(
                    "landmark_face_count",
                    0,
                ),
            },
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

        with anomaly_manager_lock:
            visual_anomaly_results = anomaly_manager.update_many(
                anomalies={
                    "NO_FACE": no_face_detected,
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
                    "PHONE_DETECTED": object_anomalies["phone_detected"],
                    "BOOK_DETECTED": object_anomalies["book_detected"],
                    "EXTRA_PERSON": object_anomalies["extra_person_detected"],
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
                evidence_regions=evidence_regions,
            )

        with pending_violations_lock:
            pending_violations = pipeline.get(
                "pending_violations",
                [],
            )

            if pending_violations is None:
                pending_violations = []

            pending_violations = queue_api_violations(
                visual_anomaly_results,
                pending_violations,
            )

            pipeline["pending_violations"] = pending_violations

            if pending_violations:
                pending_violations = send_pending_violations(
                    proctoring_api=proctoring_api,
                    pending_violations=pending_violations,
                    proctor_socket=proctor_socket,
                )

                pipeline["pending_violations"] = pending_violations

        anomaly_results = dict(visual_anomaly_results)

        audio_anomaly_result = pipeline.get("audio_anomaly_result")

        if not isinstance(
            audio_anomaly_result,
            dict,
        ):
            audio_anomaly_result = empty_voice_anomaly_result()

        anomaly_results["VOICE_DETECTED"] = dict(audio_anomaly_result)

        current_time = time.time()

        if current_time - last_log_time >= 1.0:
            if face_count == 0:
                print("[DETECTION] NO FACE")

            elif face_count == 1:
                print("[DETECTION] SINGLE FACE")

            else:
                print("[DETECTION] " f"MULTIPLE FACES: {face_count}")

            print(
                "[FACE PRESENCE] "
                f"mediapipe_count={face_count} "
                "| landmarker_valid="
                f"{landmark_valid} "
                "| landmarker_count="
                f"{face_presence.get('landmark_face_count', 0)} "
                "| no_face="
                f"{no_face_detected}"
            )

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
                print("[OBJECT] " "No monitored objects detected.")

            if audio_monitor is not None:
                audio_status = audio_monitor.get_status()

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
                    "| cumulative="
                    f"{float(audio_status.get('cumulative_voice_duration_seconds', audio_status.get('voice_duration_seconds', 0.0)) or 0.0):.2f}s "
                    "| silence="
                    f"{float(audio_status.get('silence_duration_seconds', 0.0) or 0.0):.2f}s "
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

            if pending_violations:
                print("[API] Pending violations: " f"{len(pending_violations)}")

            last_log_time = current_time


def run_proctor_session(
    kiosk,
    keyboard_lockdown,
    pipeline,
):
    print()

    print("[PROCTOR] Proctoring session active.")

    try:

        run_proctoring_detection_loop(pipeline)

    except KeyboardInterrupt:

        print()

        print("[PROCTOR] Development stop requested.")

        request_final_evidence_flush(
            pipeline=pipeline,
            reason="DEVELOPMENT_STOP",
        )

    finally:

        final_reason = pipeline.get("shutdown_reason") or (
            "EXAM_COMPLETE" if exam_completed_flag else "SESSION_FINALIZATION"
        )

        stop_audio_tracking_worker(pipeline)

        request_final_evidence_flush(
            pipeline=pipeline,
            reason=final_reason,
        )

        flush_all_pending_evidence_until_empty(
            pipeline=pipeline,
            reason=final_reason,
        )

        stop_process_monitor_frontend_forwarder(pipeline)

        stop_process_monitor_frontend_forwarder(pipeline)

        process_monitor = pipeline.get("process_monitor")

        if process_monitor is not None:
            stop_process_monitor(process_monitor)

            pipeline["process_monitor"] = None

        try:

            keyboard_lockdown.stop()

        except Exception as error:

            print(
                "[PROCTOR] Keyboard unlock error:",
                error,
            )

        try:

            cleanup_proctoring_pipeline(
                camera=pipeline.get("camera"),
                microphone=pipeline.get("microphone"),
                face_detector=pipeline.get("face_detector"),
                face_landmarker=pipeline.get("face_landmarker"),
                gaze_tracker=pipeline.get("gaze_tracker"),
                head_tracker=pipeline.get("head_tracker"),
                pose_landmarker=pipeline.get("pose_landmarker"),
                posture_monitor=pipeline.get("posture_monitor"),
                object_detector=pipeline.get("object_detector"),
                evidence_store=pipeline.get("evidence_store"),
                anomaly_manager=pipeline.get("anomaly_manager"),
                proctoring_api=pipeline.get("proctoring_api"),
                audio_monitor=pipeline.get("audio_monitor"),
                voice_incident_recorder=pipeline.get("voice_incident_recorder"),
            )

        except Exception as error:

            print(
                "[PROCTOR] Pipeline cleanup error:",
                error,
            )

        try:

            kiosk.stop()

        except Exception as error:

            print(
                "[PROCTOR] Kiosk stop error:",
                error,
            )

        if exam_completed_flag:
            open_assessments_center()


def terminate_startup_failure(
    kiosk,
    keyboard_lockdown,
    socket_client,
    pipeline,
    error,
):
    print()

    print("[PROCTOR] " "========================================")

    print("[PROCTOR] " "CAMERA/MICROPHONE STARTUP FAILED")

    print("[PROCTOR] " "Exam session got terminated.")

    print(f"[PROCTOR] Reason: {error}")

    print("[PROCTOR] " "========================================")

    if pipeline is not None:
        try:
            stop_audio_tracking_worker(pipeline)

            request_final_evidence_flush(
                pipeline=pipeline,
                reason="STARTUP_FAILURE",
            )

            flush_all_pending_evidence_until_empty(
                pipeline=pipeline,
                reason="STARTUP_FAILURE",
            )

        except Exception as flush_error:
            print(
                "[API] Startup-failure evidence flush error:",
                flush_error,
            )

    if pipeline is not None:

        process_monitor = pipeline.get("process_monitor")

        if process_monitor is not None:
            try:
                stop_process_monitor(process_monitor)

                pipeline["process_monitor"] = None

            except Exception:
                pass

    if keyboard_lockdown is not None:

        try:
            keyboard_lockdown.stop()

        except Exception:
            pass

    if socket_client is not None:

        try:
            socket_client.disconnect()

        except Exception:
            pass

    if pipeline is not None:

        try:

            cleanup_proctoring_pipeline(
                camera=pipeline.get("camera"),
                microphone=pipeline.get("microphone"),
                face_detector=pipeline.get("face_detector"),
                face_landmarker=pipeline.get("face_landmarker"),
                gaze_tracker=pipeline.get("gaze_tracker"),
                head_tracker=pipeline.get("head_tracker"),
                pose_landmarker=pipeline.get("pose_landmarker"),
                posture_monitor=pipeline.get("posture_monitor"),
                object_detector=pipeline.get("object_detector"),
                evidence_store=pipeline.get("evidence_store"),
                anomaly_manager=pipeline.get("anomaly_manager"),
                proctoring_api=pipeline.get("proctoring_api"),
                audio_monitor=pipeline.get("audio_monitor"),
                voice_incident_recorder=pipeline.get("voice_incident_recorder"),
            )

        except Exception:
            pass

    if kiosk is not None:

        try:
            kiosk.stop()

        except Exception:
            pass


def main():
    global exam_completed_flag

    exam_completed_flag = False

    # This event gates every detector/anomaly operation.
    #
    # Camera and microphone are initialized before the kiosk opens,
    # but this event remains unset until AssessmentsNewPage has
    # rendered, joined the secure socket room, and Node forwards
    # "proctor-tracking-start" to this Python client.
    tracking_start_event = threading.Event()

    token = get_launch_token()

    try:

        session = validate_launch_token(token)

    except LaunchTokenError as error:

        print(f"Launch rejected: {error}")

        sys.exit(1)

    session = session.model_dump()

    session["raw_token"] = token

    print()

    print("[PROCTOR] Launch token validated.")

    safe_session_log = {
        key: value for key, value in session.items() if key != "raw_token"
    }

    print(
        "[PROCTOR] Session:",
        safe_session_log,
    )

    # A valid new launch may supersede an independently running stale proctor.
    # This cleanup is deliberately best-effort and MUST NEVER prevent the new
    # assessment from starting. The cleanup implementation also protects this
    # process and every launcher/ancestor in its active process chain.
    try:
        terminate_previous_proctor_instances()
    except Exception as error:
        print(
            "[PROCTOR][DUPLICATE CLEANUP] Unexpected cleanup error; "
            "continuing startup safely. "
            f"Reason: {error}"
        )

    kiosk = None

    keyboard_lockdown = None

    socket_client = None

    process_monitor = None

    pipeline = None

    # ProcessMonitor may detect and close restricted applications before the
    # Socket.IO connection exists. Keep only frontend-safe message payloads in
    # this queue until the proctor socket has joined its room.
    process_monitor_frontend_queue = queue.Queue()

    try:

        print()

        print("[PROCTOR] Securing desktop before camera and microphone startup...")

        process_monitor = prepare_process_monitor(
            frontend_event_callback=process_monitor_frontend_queue.put,
        )

        perform_pre_exam_process_cleanup(process_monitor)

        print()

        print("[PROCTOR] Performing mandatory " "camera and microphone check...")

        pipeline = initialize_proctoring_pipeline(session)

        pipeline["process_monitor"] = process_monitor
        pipeline["process_monitor_frontend_queue"] = process_monitor_frontend_queue

        print()

        print("[PROCTOR] Camera check: PASSED")

        print("[PROCTOR] Microphone check: PASSED")

        print()

        print("[PROCTOR] Starting secure exam " "environment...")

        # Attach the new tracking gate before starting the socket.
        # The detection loop will keep the camera/microphone alive,
        # but all detector/anomaly/evidence work remains paused until
        # this event is set by the validated socket start signal.
        pipeline["tracking_start_event"] = tracking_start_event

        def before_tracking_start():
            # Match the working test_v2 behavior: discard bootstrap audio and
            # begin the real assessment from a fresh VAD/incident state.
            reset_audio_tracking_state(pipeline)

        def before_exam_complete():
            return wait_for_final_evidence_flush(
                pipeline=pipeline,
                reason="EXAM_COMPLETE",
            )

        socket_client = start_proctor_socket(
            session,
            tracking_start_event=tracking_start_event,
            audio_monitor=pipeline.get("audio_monitor"),
            before_exam_complete_callback=before_exam_complete,
            before_tracking_start_callback=before_tracking_start,
        )

        # Attach the same live socket client to the running pipeline.
        pipeline["proctor_socket"] = socket_client

        if socket_client is not None:

            start_process_monitor_frontend_forwarder(
                pipeline=pipeline,
                socket_client=socket_client,
            )

            print("[PROCTOR] Socket client created " "successfully.")

            # Real-time violation notifications must not wait for REST
            # persistence. Image anomalies emit after their normal local
            # evidence capture. VOICE_DETECTED emits immediately using the
            # lightweight deferred-audio marker, while its complete WAV
            # continues recording and is queued to REST only after the held
            # voice incident ends.
            anomaly_manager = pipeline.get("anomaly_manager")

            if anomaly_manager is not None:

                anomaly_manager.set_socket_client(socket_client)

                print(
                    "[PROCTOR] Live socket attached to anomaly manager. "
                    "Image violations emit after local evidence capture; "
                    "voice violations emit immediately while complete WAV "
                    "evidence continues recording."
                )

                if not start_audio_tracking_worker(pipeline):
                    raise RuntimeError(
                        "Unable to start the dedicated real-time audio "
                        "tracking worker."
                    )

                print(
                    "[PROCTOR] Dedicated audio tracking worker ready. "
                    "Voice violations will be processed independently "
                    "from vision inference and REST submission."
                )

            else:

                raise RuntimeError(
                    "Anomaly manager is unavailable. "
                    "Real-time proctor violation events cannot be enabled."
                )

        else:

            raise RuntimeError(
                "Secure proctor socket could not be started. "
                "The exam cannot begin without the tracking-start channel."
            )

        def before_security_termination():
            return wait_for_final_evidence_flush(
                pipeline=pipeline,
                reason="SECURE_DESKTOP",
            )

        kiosk, kiosk_process = start_kiosk(
            token,
            proctor_socket=socket_client,
            before_security_termination_callback=before_security_termination,
        )

        activate_process_monitor(
            process_monitor=process_monitor,
            kiosk_process=kiosk_process,
        )

        keyboard_lockdown = start_keyboard_lockdown()

        run_proctor_session(
            kiosk,
            keyboard_lockdown,
            pipeline,
        )

        pipeline = None

    except Exception as error:

        print()

        print("[PROCTOR] Startup/session failure.")

        print(f"[PROCTOR] Reason: {error}")

        terminate_startup_failure(
            kiosk=kiosk,
            keyboard_lockdown=keyboard_lockdown,
            socket_client=socket_client,
            pipeline=pipeline,
            error=error,
        )

        kiosk = None

        keyboard_lockdown = None

        socket_client = None

        pipeline = None

    finally:

        if pipeline is not None:
            try:
                stop_audio_tracking_worker(pipeline)

                request_final_evidence_flush(
                    pipeline=pipeline,
                    reason=(pipeline.get("shutdown_reason") or "MAIN_FINALIZATION"),
                )

                flush_all_pending_evidence_until_empty(
                    pipeline=pipeline,
                    reason=(pipeline.get("shutdown_reason") or "MAIN_FINALIZATION"),
                )

            except Exception as flush_error:
                print(
                    "[API] Main final evidence flush error:",
                    flush_error,
                )

        if process_monitor is not None:
            stop_process_monitor(process_monitor)

            process_monitor = None

        if socket_client:

            try:
                socket_client.disconnect()

            except Exception:
                pass

        if pipeline is not None:

            try:

                cleanup_proctoring_pipeline(
                    camera=pipeline.get("camera"),
                    microphone=pipeline.get("microphone"),
                    face_detector=pipeline.get("face_detector"),
                    face_landmarker=pipeline.get("face_landmarker"),
                    gaze_tracker=pipeline.get("gaze_tracker"),
                    head_tracker=pipeline.get("head_tracker"),
                    pose_landmarker=pipeline.get("pose_landmarker"),
                    posture_monitor=pipeline.get("posture_monitor"),
                    object_detector=pipeline.get("object_detector"),
                    evidence_store=pipeline.get("evidence_store"),
                    anomaly_manager=pipeline.get("anomaly_manager"),
                    proctoring_api=pipeline.get("proctoring_api"),
                    audio_monitor=pipeline.get("audio_monitor"),
                    voice_incident_recorder=pipeline.get("voice_incident_recorder"),
                )

            except Exception:
                pass


if __name__ == "__main__":
    main()
