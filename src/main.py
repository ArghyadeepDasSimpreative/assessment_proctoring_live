# import argparse
# import os
# import sys
# import time
# import math
# import threading

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

# from src.vision.face_detector_yunet import (
#     YuNetFaceDetector,
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
# ):
#     bootstrap_url = build_bootstrap_url(token)

#     print()

#     print("[PROCTOR] Starting secure kiosk...")

#     print("[PROCTOR] Bootstrap URL prepared.")

#     kiosk = KioskManager(proctor_socket=proctor_socket)

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


# def prepare_process_monitor():
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

#         process_monitor = ProcessMonitor(
#             check_interval=2.0,
#             block_external_browsers=True,
#             terminate_remote_access=True,
#             terminate_screen_sharing=True,
#         )

#         process_monitor.capture_pre_kiosk_browser_processes()

#         print("[PROCESS MONITOR] Pre-kiosk browser snapshot completed.")

#         return process_monitor

#     except Exception as error:
#         print(
#             "[PROCESS MONITOR] Initialization failed:",
#             error,
#         )

#         return None


# def activate_process_monitor(
#     process_monitor,
#     kiosk_process,
# ):
#     if process_monitor is None:
#         return False

#     kiosk_pid = get_process_pid(kiosk_process)

#     if kiosk_pid is None:
#         print(
#             "[PROCESS MONITOR] Kiosk PID is unavailable. "
#             "External-browser termination will remain disabled, "
#             "but remote-access monitoring will still be started."
#         )

#     else:
#         try:
#             process_monitor.set_kiosk_root_pid(kiosk_pid)

#             print("[PROCESS MONITOR] Secure kiosk process tree protected.")

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
#             print("[PROCESS MONITOR] Continuous process monitoring started.")

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
# ):
#     """
#     Start the native Socket.IO client.

#     Backward compatibility:
#     - tracking_start_event is optional.
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

#         socket_client.exam_completed_callback = exam_completed

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

#         print("[PROCTOR] Initializing native " "proctoring hardware...")

#         print("[CAMERA] Starting camera...")

#         camera = open_camera()

#         print("[CAMERA] Camera opened successfully.")

#         print("[MICROPHONE] Starting microphone...")

#         microphone = start_microphone()

#         print("[MICROPHONE] Microphone started " "successfully.")

#         print("[YUNET] Loading face detector...")

#         face_detector = YuNetFaceDetector()

#         print("[YUNET] Face detector loaded " "successfully.")

#         print("[FACE LANDMARKER] Loading " "MediaPipe Face Landmarker...")

#         face_landmarker = FaceLandmarker()

#         print("[FACE LANDMARKER] MediaPipe model " "loaded successfully.")

#         print("[GAZE] Initializing gaze tracker...")

#         gaze_tracker = GazeTracker()

#         print("[GAZE] Gaze tracker initialized.")

#         print("[HEAD] Initializing head tracker...")

#         head_tracker = HeadTracker()

#         print("[HEAD] Head tracker initialized.")

#         print("[POSE] Loading MediaPipe " "Pose Landmarker...")

#         pose_landmarker = PoseLandmarker()

#         print("[POSE] Pose Landmarker loaded " "successfully.")

#         print("[POSTURE] Initializing posture " "monitor...")

#         posture_monitor = PostureMonitor()

#         print("[POSTURE] Posture monitor " "initialized.")

#         print("[YOLO26] Loading object detector...")

#         object_detector = YOLO26ObjectDetector()

#         print("[YOLO26] Object detector loaded " "successfully.")

#         print("[EVIDENCE] Initializing evidence " "store...")

#         evidence_store = EvidenceStore(
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

#         print("[EVIDENCE] Evidence store " "initialized.")

#         print("[ANOMALY] Initializing anomaly " "manager...")

#         anomaly_manager = AnomalyManager(evidence_store=evidence_store)

#         print("[ANOMALY] Anomaly manager " "initialized.")

#         print("[API] Initializing proctoring API...")

#         proctoring_api = ProctoringAPI(token=session.get("raw_token"))

#         print("[API] Proctoring API initialized.")

#         print()

#         print("[PROCTOR] Native proctoring " "pipeline initialized successfully.")

#         return {
#             "camera": camera,
#             "microphone": microphone,
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
# ):
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

#     if microphone is not None:
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
#                 "[YUNET] Cleanup error:",
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
#     - proctor_socket is optional.
#     - Existing two-argument calls continue to work unchanged.

#     New behavior:
#     - Socket.IO notification is emitted only AFTER the REST API
#       confirms that the violation batch was recorded successfully.
#     """

#     if proctoring_api is None or not pending_violations:
#         return pending_violations

#     violations = []

#     evidence_files = []

#     socket_violations = []

#     for violation in pending_violations:

#         if not isinstance(
#             violation,
#             dict,
#         ):
#             continue

#         original_violation = dict(violation)

#         violation_copy = dict(violation)

#         file_path = violation_copy.pop(
#             "file_path",
#             None,
#         )

#         violation_index = len(violations)

#         violations.append(violation_copy)

#         socket_violations.append(original_violation)

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

#         # Only emit the real-time Socket.IO notification after
#         # the backend REST API has confirmed successful persistence.
#         #
#         # A socket failure must not put the already-saved violation
#         # back into the REST retry queue, otherwise duplicate DB rows
#         # could be created later.
#         if proctor_socket is not None:

#             notify_method = getattr(
#                 proctor_socket,
#                 "notify_proctor_violation",
#                 None,
#             )

#             if callable(notify_method):

#                 for (
#                     violation_index,
#                     socket_violation,
#                 ) in enumerate(socket_violations):

#                     try:
#                         violation_type = (
#                             socket_violation.get("violation_type")
#                             or socket_violation.get("event_type")
#                             or "UNKNOWN"
#                         )

#                         print(
#                             "[SOCKET][VIOLATION AFTER API SUCCESS] "
#                             f"violation_index={violation_index} "
#                             f"| violation_type={violation_type}"
#                         )

#                         emitted = notify_method(socket_violation)

#                         if emitted:
#                             print(
#                                 "[SOCKET][VIOLATION EMISSION REQUESTED] "
#                                 f"violation_type={violation_type}"
#                             )

#                         else:
#                             print(
#                                 "[SOCKET][VIOLATION EMISSION FAILED] "
#                                 f"violation_type={violation_type}"
#                             )

#                     except Exception as socket_error:
#                         print(
#                             "[SOCKET][VIOLATION EMISSION ERROR] "
#                             f"violation_index={violation_index} "
#                             f"| error={socket_error}"
#                         )

#             else:
#                 print(
#                     "[SOCKET][VIOLATION NOT EMITTED] "
#                     "Socket client does not provide "
#                     "notify_proctor_violation()."
#                 )

#         # REST persistence succeeded, so clear these violations
#         # regardless of whether the real-time socket notification
#         # was delivered successfully.
#         return []

#     reason = result.get("reason")

#     if reason == "API_COOLDOWN":
#         return pending_violations

#     print("[API] Violation batch was not " "sent.")

#     if reason:
#         print(f"[API] Reason: {reason}")

#     return pending_violations


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

#     proctoring_api = pipeline.get("proctoring_api")

#     proctor_socket = pipeline.get("proctor_socket")

#     pending_violations = pipeline.get("pending_violations")

#     if pending_violations is None:
#         pending_violations = []

#         pipeline["pending_violations"] = pending_violations

#     tracking_start_event = pipeline.get("tracking_start_event")

#     # Backward compatibility:
#     # If an older caller invokes this loop without the new
#     # tracking_start_event, preserve the previous behavior
#     # and begin detection immediately.
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
#             "[PROCTOR] Violation tracking is PAUSED until the secure exam page signals readiness."
#         )

#     while True:

#         if exam_completed_flag:

#             print()

#             print("[PROCTOR] Exam completion " "received. Stopping detection.")

#             break

#         success, frame = camera.read()

#         if not success or frame is None:
#             print("[CAMERA] Failed to read frame.")

#             time.sleep(0.05)

#             continue

#         # Keep consuming camera frames so the camera remains warm and
#         # does not build up a stale capture buffer, but do not execute
#         # any detector, anomaly timer, evidence capture, REST request,
#         # or violation socket emission before the frontend start signal.
#         if not tracking_start_event.is_set():

#             current_time = time.time()

#             if current_time - last_waiting_log_time >= 2.0:

#                 print(
#                     "[PROCTOR] Waiting for secure exam page. Violation tracking remains paused."
#                 )

#                 last_waiting_log_time = current_time

#             time.sleep(0.02)

#             continue

#         if not tracking_started_logged:

#             tracking_started_logged = True

#             print()

#             print(
#                 "[PROCTOR] Frontend readiness confirmed. Starting violation tracking."
#             )

#             print("[PROCTOR] Detection pipeline started.")

#         frame_count += 1

#         try:
#             faces = face_detector.detect(frame)

#             if faces is None:
#                 faces = []

#         except Exception as error:

#             print(
#                 "[YUNET] Detection error:",
#                 error,
#             )

#             faces = []

#         face_count = len(faces)

#         try:
#             landmark_result = face_landmarker.process(frame)

#         except Exception as error:

#             print(
#                 "[FACE LANDMARKER] " "Processing error:",
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

#         face_presence = evaluate_face_presence(
#             faces=faces,
#             landmark_result=landmark_result,
#             frame_shape=frame.shape,
#         )

#         no_face_detected = bool(
#             face_presence.get(
#                 "no_face",
#                 False,
#             )
#         )

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
#                 "yunet_face_present": face_presence.get(
#                     "yunet_face_present",
#                     False,
#                 ),
#                 "landmarker_face_present": face_presence.get(
#                     "landmarker_face_present",
#                     False,
#                 ),
#                 "landmark_face_count": face_presence.get(
#                     "landmark_face_count",
#                     0,
#                 ),
#                 "yunet_face_clipped": face_presence.get(
#                     "yunet_face_clipped",
#                     False,
#                 ),
#                 "landmark_face_out_of_frame": face_presence.get(
#                     "landmark_face_out_of_frame",
#                     False,
#                 ),
#                 "partial_face_out_of_frame": face_presence.get(
#                     "partial_face_out_of_frame",
#                     False,
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

#         anomaly_results = anomaly_manager.update_many(
#             anomalies={
#                 "NO_FACE": no_face_detected,
#                 "MULTIPLE_FACES": (face_count > 1),
#                 "GAZE_AWAY": bool(
#                     gaze_result.get(
#                         "away",
#                         False,
#                     )
#                 ),
#                 "HEAD_AWAY": bool(
#                     head_result.get(
#                         "away",
#                         False,
#                     )
#                 ),
#                 "PHONE_DETECTED": object_anomalies["phone_detected"],
#                 "BOOK_DETECTED": object_anomalies["book_detected"],
#                 "EXTRA_PERSON": object_anomalies["extra_person_detected"],
#                 "BODY_LEAN_LEFT": bool(
#                     posture_result.get(
#                         "leaning_left",
#                         False,
#                     )
#                 ),
#                 "BODY_LEAN_RIGHT": bool(
#                     posture_result.get(
#                         "leaning_right",
#                         False,
#                     )
#                 ),
#                 "LEFT_ARM_RAISED": bool(
#                     posture_result.get(
#                         "left_arm_raised",
#                         False,
#                     )
#                 ),
#                 "RIGHT_ARM_RAISED": bool(
#                     posture_result.get(
#                         "right_arm_raised",
#                         False,
#                     )
#                 ),
#                 "UNUSUAL_ARM_MOVEMENT": bool(
#                     posture_result.get(
#                         "unusual_arm_movement",
#                         False,
#                     )
#                 ),
#                 "UPPER_BODY_NOT_VISIBLE": (
#                     posture_result.get(
#                         "valid",
#                         False,
#                     )
#                     and not posture_result.get(
#                         "upper_body_visible",
#                         False,
#                     )
#                 ),
#             },
#             frame=frame,
#             metadata=anomaly_metadata,
#         )

#         pending_violations = queue_api_violations(
#             anomaly_results,
#             pending_violations,
#         )

#         pipeline["pending_violations"] = pending_violations

#         if pending_violations:

#             pending_violations = send_pending_violations(
#                 proctoring_api=proctoring_api,
#                 pending_violations=pending_violations,
#                 proctor_socket=proctor_socket,
#             )

#             pipeline["pending_violations"] = pending_violations

#         current_time = time.time()

#         if current_time - last_log_time >= 1.0:

#             face_decision = face_presence.get(
#                 "decision",
#                 "UNKNOWN",
#             )

#             if no_face_detected:

#                 if face_presence.get(
#                     "partial_face_out_of_frame",
#                     False,
#                 ):

#                     print("[DETECTION] FACE PARTIALLY OUT OF FRAME")

#                 else:

#                     print("[DETECTION] NO FACE CONFIRMED BY BOTH FACE ENGINES")

#             elif face_count > 1:

#                 print("[DETECTION] " f"MULTIPLE FACES: " f"{face_count}")

#             else:

#                 print("[DETECTION] FACE PRESENT " f"| source={face_decision}")

#             print(
#                 "[FACE PRESENCE] "
#                 f"yunet_count={face_count} "
#                 "| landmarker_valid="
#                 f"{landmark_valid} "
#                 "| landmarker_count="
#                 f"{face_presence.get('landmark_face_count', 0)} "
#                 "| yunet_clipped="
#                 f"{face_presence.get('yunet_face_clipped', False)} "
#                 "| landmark_out="
#                 f"{face_presence.get('landmark_face_out_of_frame', False)} "
#                 "| no_face="
#                 f"{no_face_detected}"
#             )

#             if landmark_valid:
#                 print("[FACE LANDMARKER] VALID")

#             else:
#                 print("[FACE LANDMARKER] " "NOT AVAILABLE")

#             if gaze_result:
#                 print(
#                     "[GAZE] "
#                     f"{gaze_result.get('direction', 'UNKNOWN')} "
#                     "| valid="
#                     f"{gaze_result.get('valid', False)} "
#                     "| calibrated="
#                     f"{gaze_result.get('calibrated', False)} "
#                     "| away="
#                     f"{gaze_result.get('away', False)}"
#                 )

#             if head_result:
#                 print(
#                     "[HEAD] "
#                     f"{head_result.get('direction', 'UNKNOWN')} "
#                     "| yaw="
#                     f"{head_result.get('yaw')} "
#                     "| pitch="
#                     f"{head_result.get('pitch')} "
#                     "| roll="
#                     f"{head_result.get('roll')} "
#                     "| away="
#                     f"{head_result.get('away', False)}"
#                 )

#             if posture_result:

#                 print(
#                     "[POSE] "
#                     f"valid="
#                     f"{posture_result.get('valid', False)} "
#                     "| upper_body="
#                     f"{posture_result.get('upper_body_visible', False)} "
#                     "| lean_left="
#                     f"{posture_result.get('leaning_left', False)} "
#                     "| lean_right="
#                     f"{posture_result.get('leaning_right', False)} "
#                     "| left_arm="
#                     f"{posture_result.get('left_arm_raised', False)} "
#                     "| right_arm="
#                     f"{posture_result.get('right_arm_raised', False)} "
#                     "| unusual_movement="
#                     f"{posture_result.get('unusual_arm_movement', False)}"
#                 )

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

#     finally:

#         process_monitor = pipeline.get("process_monitor")

#         if process_monitor is not None:
#             stop_process_monitor(process_monitor)

#             pipeline["process_monitor"] = None

#         try:

#             pending_violations = pipeline.get(
#                 "pending_violations",
#                 [],
#             )

#             proctoring_api = pipeline.get("proctoring_api")

#             proctor_socket = pipeline.get("proctor_socket")

#             if pending_violations and proctoring_api is not None:

#                 pending_violations = send_pending_violations(
#                     proctoring_api=proctoring_api,
#                     pending_violations=pending_violations,
#                     proctor_socket=proctor_socket,
#                 )

#                 pipeline["pending_violations"] = pending_violations

#         except Exception as error:

#             print(
#                 "[API] Final violation " "submission error:",
#                 error,
#             )

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

#     kiosk = None

#     keyboard_lockdown = None

#     socket_client = None

#     process_monitor = None

#     pipeline = None

#     try:

#         print()

#         print("[PROCTOR] Performing mandatory " "camera and microphone check...")

#         pipeline = initialize_proctoring_pipeline(session)

#         print()

#         print("[PROCTOR] Camera check: PASSED")

#         print("[PROCTOR] Microphone check: PASSED")

#         print()

#         print("[PROCTOR] Starting secure exam " "environment...")

#         process_monitor = prepare_process_monitor()

#         pipeline["process_monitor"] = process_monitor

#         # Attach the new tracking gate before starting the socket.
#         # The detection loop will keep the camera/microphone alive,
#         # but all detector/anomaly/evidence work remains paused until
#         # this event is set by the validated socket start signal.
#         pipeline["tracking_start_event"] = tracking_start_event

#         socket_client = start_proctor_socket(
#             session,
#             tracking_start_event=tracking_start_event,
#         )

#         # Attach the same live socket client to the running pipeline.
#         # This allows successfully persisted REST violations to be
#         # forwarded to Node and then broadcast to the browser room.
#         pipeline["proctor_socket"] = socket_client

#         if socket_client is not None:

#             print("[PROCTOR] Socket client created " "successfully.")

#         else:

#             raise RuntimeError(
#                 "Secure proctor socket could not be started. "
#                 "The exam cannot begin without the tracking-start channel."
#             )

#         kiosk, kiosk_process = start_kiosk(
#             token,
#             proctor_socket=socket_client,
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
import threading
import webbrowser

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

from src.vision.face_detector_yunet import (
    YuNetFaceDetector,
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


def prepare_process_monitor():
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

        process_monitor = ProcessMonitor(
            check_interval=2.0,
            block_external_browsers=True,
            terminate_remote_access=True,
            terminate_screen_sharing=True,
        )

        process_monitor.capture_pre_kiosk_browser_processes()

        print("[PROCESS MONITOR] Pre-kiosk browser snapshot completed.")

        return process_monitor

    except Exception as error:
        print(
            "[PROCESS MONITOR] Initialization failed:",
            error,
        )

        return None


def activate_process_monitor(
    process_monitor,
    kiosk_process,
):
    if process_monitor is None:
        return False

    kiosk_pid = get_process_pid(kiosk_process)

    if kiosk_pid is None:
        print(
            "[PROCESS MONITOR] Kiosk PID is unavailable. "
            "External-browser termination will remain disabled, "
            "but remote-access monitoring will still be started."
        )

    else:
        try:
            process_monitor.set_kiosk_root_pid(kiosk_pid)

            print("[PROCESS MONITOR] Secure kiosk process tree protected.")

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
            print("[PROCESS MONITOR] Continuous process monitoring started.")

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
):
    """
    Start the native Socket.IO client.

    Backward compatibility:
    - tracking_start_event is optional.
    - audio_monitor is optional.
    - before_exam_complete_callback is optional.
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
            required_voice_duration=3.0,
            aggressiveness=1,
            calibration_seconds=1.0,
            smoothing_window_seconds=0.30,
            minimum_voice_ratio=0.40,
            silence_reset_seconds=0.75,
            whisper_noise_margin_db=6.0,
            whisper_absolute_floor_db=-58.0,
        )

        print("[VOICE] Voice activity detector initialized.")

        audio_event_queue = queue.Queue()

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

        microphone = audio_monitor

        print("[AUDIO] Audio monitor started successfully.")

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

        evidence_store = EvidenceStore(
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

        print("[EVIDENCE] Evidence store initialized.")

        print("[ANOMALY] Initializing anomaly manager...")

        anomaly_manager = AnomalyManager(evidence_store=evidence_store)

        print("[ANOMALY] Anomaly manager initialized.")

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
            "audio_event_queue": audio_event_queue,
            "audio_anomaly_result": None,
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
):
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
                "[YUNET] Cleanup error:",
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
        "active": False,
        "confirmed": False,
        "captured": False,
        "duration": 0.0,
        "required_duration": 3.0,
        "cooldown": 0.0,
        "cooldown_remaining": 0.0,
        "evidence": None,
        "api_violation": None,
    }


def process_audio_events(
    audio_event_queue,
    anomaly_manager,
    current_result=None,
    tracking_enabled=True,
):
    result = dict(current_result or empty_voice_anomaly_result())

    new_api_violations = []

    if audio_event_queue is None:
        return (
            result,
            new_api_violations,
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

        if event_type == "VOICE_DETECTED":
            if not tracking_enabled:
                continue

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

            result = anomaly_manager.update_audio(
                event_type="VOICE_DETECTED",
                active=True,
                audio_evidence=audio_evidence,
                metadata=metadata,
            )

            api_violation = result.get("api_violation")

            if isinstance(
                api_violation,
                dict,
            ):
                new_api_violations.append(dict(api_violation))

            if result.get(
                "captured",
                False,
            ):
                evidence = result.get("evidence") or {}

                print(
                    "[AUDIO][VOICE DETECTED] "
                    "3-second voice threshold reached. "
                    f"Evidence: "
                    f"{evidence.get('audio_path')}"
                )

            continue

        if event_type == "VOICE_ACTIVITY_ENDED":
            if tracking_enabled:
                result = anomaly_manager.update_audio(
                    event_type="VOICE_DETECTED",
                    active=False,
                    audio_evidence=None,
                    metadata={
                        "timestamp": payload.get("timestamp"),
                        "incident_number": payload.get("incident_number"),
                    },
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

    return (
        result,
        new_api_violations,
    )


def reset_audio_tracking_state(
    pipeline,
):
    audio_event_queue = pipeline.get("audio_event_queue")

    if audio_event_queue is not None:
        while True:
            try:
                audio_event_queue.get_nowait()

            except queue.Empty:
                break

    voice_activity_detector = pipeline.get("voice_activity_detector")

    if voice_activity_detector is not None:
        try:
            voice_activity_detector.reset(recalibrate=False)

        except Exception as error:
            print(
                "[AUDIO] Voice detector reset error:",
                error,
            )

    pipeline["audio_anomaly_result"] = empty_voice_anomaly_result()


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

    proctoring_api = pipeline.get("proctoring_api")

    proctor_socket = pipeline.get("proctor_socket")

    audio_monitor = pipeline.get("audio_monitor")

    audio_event_queue = pipeline.get("audio_event_queue")

    audio_anomaly_result = pipeline.get("audio_anomaly_result")

    if not isinstance(
        audio_anomaly_result,
        dict,
    ):
        audio_anomaly_result = empty_voice_anomaly_result()

        pipeline["audio_anomaly_result"] = audio_anomaly_result

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

    audio_tracking_reset = False

    print()

    if tracking_start_event.is_set():
        reset_audio_tracking_state(pipeline)

        audio_anomaly_result = pipeline["audio_anomaly_result"]

        audio_tracking_reset = True

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

            (
                audio_anomaly_result,
                final_audio_violations,
            ) = process_audio_events(
                audio_event_queue=audio_event_queue,
                anomaly_manager=anomaly_manager,
                current_result=audio_anomaly_result,
                tracking_enabled=tracking_start_event.is_set(),
            )

            pipeline["audio_anomaly_result"] = audio_anomaly_result

            if final_audio_violations:
                with pending_violations_lock:
                    pending_violations = pipeline.get(
                        "pending_violations",
                        [],
                    )

                    if pending_violations is None:
                        pending_violations = []

                    pending_violations.extend(final_audio_violations)

                    pipeline["pending_violations"] = pending_violations

            break

        success, frame = camera.read()

        if not success or frame is None:
            print("[CAMERA] Failed to read frame.")

            time.sleep(0.05)

            continue

        if not tracking_start_event.is_set():
            (
                audio_anomaly_result,
                _,
            ) = process_audio_events(
                audio_event_queue=audio_event_queue,
                anomaly_manager=anomaly_manager,
                current_result=audio_anomaly_result,
                tracking_enabled=False,
            )

            pipeline["audio_anomaly_result"] = audio_anomaly_result

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

        if not audio_tracking_reset:
            reset_audio_tracking_state(pipeline)

            audio_anomaly_result = pipeline["audio_anomaly_result"]

            audio_tracking_reset = True

        if not tracking_started_logged:
            tracking_started_logged = True

            print()

            print(
                "[PROCTOR] Frontend readiness confirmed. "
                "Starting violation tracking."
            )

            print("[PROCTOR] Detection pipeline started.")

        frame_count += 1

        (
            audio_anomaly_result,
            new_audio_violations,
        ) = process_audio_events(
            audio_event_queue=audio_event_queue,
            anomaly_manager=anomaly_manager,
            current_result=audio_anomaly_result,
            tracking_enabled=True,
        )

        pipeline["audio_anomaly_result"] = audio_anomaly_result

        if new_audio_violations:
            with pending_violations_lock:
                pending_violations = pipeline.get(
                    "pending_violations",
                    [],
                )

                if pending_violations is None:
                    pending_violations = []

                pending_violations.extend(new_audio_violations)

                pipeline["pending_violations"] = pending_violations

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

        face_presence = evaluate_face_presence(
            faces=faces,
            landmark_result=landmark_result,
            frame_shape=frame.shape,
        )

        no_face_detected = bool(
            face_presence.get(
                "no_face",
                False,
            )
        )

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

        anomaly_metadata = {
            "frame_number": frame_count,
            "face_count": face_count,
            "landmark_valid": landmark_valid,
            "face_presence": {
                "decision": face_presence.get(
                    "decision",
                    "UNKNOWN",
                ),
                "no_face": no_face_detected,
                "yunet_face_present": face_presence.get(
                    "yunet_face_present",
                    False,
                ),
                "landmarker_face_present": face_presence.get(
                    "landmarker_face_present",
                    False,
                ),
                "landmark_face_count": face_presence.get(
                    "landmark_face_count",
                    0,
                ),
                "yunet_face_clipped": face_presence.get(
                    "yunet_face_clipped",
                    False,
                ),
                "landmark_face_out_of_frame": face_presence.get(
                    "landmark_face_out_of_frame",
                    False,
                ),
                "partial_face_out_of_frame": face_presence.get(
                    "partial_face_out_of_frame",
                    False,
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

        anomaly_results["VOICE_DETECTED"] = dict(audio_anomaly_result)

        current_time = time.time()

        if current_time - last_log_time >= 1.0:
            face_decision = face_presence.get(
                "decision",
                "UNKNOWN",
            )

            if no_face_detected:
                if face_presence.get(
                    "partial_face_out_of_frame",
                    False,
                ):
                    print("[DETECTION] " "FACE PARTIALLY OUT OF FRAME")

                else:
                    print("[DETECTION] " "NO FACE CONFIRMED BY BOTH FACE ENGINES")

            elif face_count > 1:
                print("[DETECTION] " f"MULTIPLE FACES: " f"{face_count}")

            else:
                print("[DETECTION] FACE PRESENT " f"| source={face_decision}")

            print(
                "[FACE PRESENCE] "
                f"yunet_count={face_count} "
                "| landmarker_valid="
                f"{landmark_valid} "
                "| landmarker_count="
                f"{face_presence.get('landmark_face_count', 0)} "
                "| yunet_clipped="
                f"{face_presence.get('yunet_face_clipped', False)} "
                "| landmark_out="
                f"{face_presence.get('landmark_face_out_of_frame', False)} "
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

        request_final_evidence_flush(
            pipeline=pipeline,
            reason=final_reason,
        )

        flush_all_pending_evidence_until_empty(
            pipeline=pipeline,
            reason=final_reason,
        )

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

    kiosk = None

    keyboard_lockdown = None

    socket_client = None

    process_monitor = None

    pipeline = None

    try:

        print()

        print("[PROCTOR] Performing mandatory " "camera and microphone check...")

        pipeline = initialize_proctoring_pipeline(session)

        print()

        print("[PROCTOR] Camera check: PASSED")

        print("[PROCTOR] Microphone check: PASSED")

        print()

        print("[PROCTOR] Starting secure exam " "environment...")

        process_monitor = prepare_process_monitor()

        pipeline["process_monitor"] = process_monitor

        # Attach the new tracking gate before starting the socket.
        # The detection loop will keep the camera/microphone alive,
        # but all detector/anomaly/evidence work remains paused until
        # this event is set by the validated socket start signal.
        pipeline["tracking_start_event"] = tracking_start_event

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
        )

        # Attach the same live socket client to the running pipeline.
        pipeline["proctor_socket"] = socket_client

        if socket_client is not None:

            print("[PROCTOR] Socket client created " "successfully.")

            # Real-time violation notifications must not wait for
            # REST persistence. AnomalyManager emits immediately
            # after local evidence capture for both image evidence
            # and VOICE_DETECTED WAV evidence.
            anomaly_manager = pipeline.get("anomaly_manager")

            if anomaly_manager is not None:

                anomaly_manager.set_socket_client(socket_client)

                print(
                    "[PROCTOR] Live socket attached to anomaly manager. "
                    "Image and audio violation events will emit immediately "
                    "after local evidence capture."
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
                )

            except Exception:
                pass


if __name__ == "__main__":
    main()
