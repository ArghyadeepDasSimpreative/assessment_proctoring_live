# import argparse
# import os
# import sys
# import time

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


# def start_proctor_socket(
#     session,
# ):
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
#     """

#     if proctoring_api is None or not pending_violations:
#         return pending_violations

#     violations = []

#     evidence_files = []

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

#     pending_violations = pipeline.get("pending_violations")

#     if pending_violations is None:
#         pending_violations = []

#         pipeline["pending_violations"] = pending_violations

#     frame_count = 0

#     last_log_time = 0.0

#     print()

#     print("[PROCTOR] Detection pipeline started.")

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
#                 "NO_FACE": (face_count == 0),
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
#             )

#             pipeline["pending_violations"] = pending_violations

#         current_time = time.time()

#         if current_time - last_log_time >= 1.0:

#             if face_count == 0:
#                 print("[DETECTION] NO FACE")

#             elif face_count == 1:
#                 print("[DETECTION] SINGLE FACE")

#             else:
#                 print("[DETECTION] " f"MULTIPLE FACES: " f"{face_count}")

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

#         try:

#             pending_violations = pipeline.get(
#                 "pending_violations",
#                 [],
#             )

#             proctoring_api = pipeline.get("proctoring_api")

#             if pending_violations and proctoring_api is not None:

#                 pending_violations = send_pending_violations(
#                     proctoring_api=proctoring_api,
#                     pending_violations=pending_violations,
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

#     print(
#         "[PROCTOR] Session:",
#         session,
#     )

#     kiosk = None

#     keyboard_lockdown = None

#     socket_client = None

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

#         socket_client = start_proctor_socket(session)

#         if socket_client is not None:

#             print("[PROCTOR] Socket client created " "successfully.")

#         else:

#             print("[PROCTOR] WARNING: Socket client " "could not be created.")

#         kiosk, _ = start_kiosk(
#             token,
#             proctor_socket=socket_client,
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
import threading

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
):
    bootstrap_url = build_bootstrap_url(token)

    print()

    print("[PROCTOR] Starting secure kiosk...")

    print("[PROCTOR] Bootstrap URL prepared.")

    kiosk = KioskManager(proctor_socket=proctor_socket)

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


def start_proctor_socket(
    session,
    tracking_start_event=None,
):
    """
    Start the native Socket.IO client.

    Backward compatibility:
    - tracking_start_event is optional.
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

        socket_client.exam_completed_callback = exam_completed

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

        print("[PROCTOR] Initializing native " "proctoring hardware...")

        print("[CAMERA] Starting camera...")

        camera = open_camera()

        print("[CAMERA] Camera opened successfully.")

        print("[MICROPHONE] Starting microphone...")

        microphone = start_microphone()

        print("[MICROPHONE] Microphone started " "successfully.")

        print("[YUNET] Loading face detector...")

        face_detector = YuNetFaceDetector()

        print("[YUNET] Face detector loaded " "successfully.")

        print("[FACE LANDMARKER] Loading " "MediaPipe Face Landmarker...")

        face_landmarker = FaceLandmarker()

        print("[FACE LANDMARKER] MediaPipe model " "loaded successfully.")

        print("[GAZE] Initializing gaze tracker...")

        gaze_tracker = GazeTracker()

        print("[GAZE] Gaze tracker initialized.")

        print("[HEAD] Initializing head tracker...")

        head_tracker = HeadTracker()

        print("[HEAD] Head tracker initialized.")

        print("[POSE] Loading MediaPipe " "Pose Landmarker...")

        pose_landmarker = PoseLandmarker()

        print("[POSE] Pose Landmarker loaded " "successfully.")

        print("[POSTURE] Initializing posture " "monitor...")

        posture_monitor = PostureMonitor()

        print("[POSTURE] Posture monitor " "initialized.")

        print("[YOLO26] Loading object detector...")

        object_detector = YOLO26ObjectDetector()

        print("[YOLO26] Object detector loaded " "successfully.")

        print("[EVIDENCE] Initializing evidence " "store...")

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

        print("[EVIDENCE] Evidence store " "initialized.")

        print("[ANOMALY] Initializing anomaly " "manager...")

        anomaly_manager = AnomalyManager(evidence_store=evidence_store)

        print("[ANOMALY] Anomaly manager " "initialized.")

        print("[API] Initializing proctoring API...")

        proctoring_api = ProctoringAPI(token=session.get("raw_token"))

        print("[API] Proctoring API initialized.")

        print()

        print("[PROCTOR] Native proctoring " "pipeline initialized successfully.")

        return {
            "camera": camera,
            "microphone": microphone,
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
            "pending_violations": [],
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
):
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

    if microphone is not None:
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
    - proctor_socket is optional.
    - Existing two-argument calls continue to work unchanged.

    New behavior:
    - Socket.IO notification is emitted only AFTER the REST API
      confirms that the violation batch was recorded successfully.
    """

    if proctoring_api is None or not pending_violations:
        return pending_violations

    violations = []

    evidence_files = []

    socket_violations = []

    for violation in pending_violations:

        if not isinstance(
            violation,
            dict,
        ):
            continue

        original_violation = dict(violation)

        violation_copy = dict(violation)

        file_path = violation_copy.pop(
            "file_path",
            None,
        )

        violation_index = len(violations)

        violations.append(violation_copy)

        socket_violations.append(original_violation)

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

        # Only emit the real-time Socket.IO notification after
        # the backend REST API has confirmed successful persistence.
        #
        # A socket failure must not put the already-saved violation
        # back into the REST retry queue, otherwise duplicate DB rows
        # could be created later.
        if proctor_socket is not None:

            notify_method = getattr(
                proctor_socket,
                "notify_proctor_violation",
                None,
            )

            if callable(notify_method):

                for (
                    violation_index,
                    socket_violation,
                ) in enumerate(socket_violations):

                    try:
                        violation_type = (
                            socket_violation.get("violation_type")
                            or socket_violation.get("event_type")
                            or "UNKNOWN"
                        )

                        print(
                            "[SOCKET][VIOLATION AFTER API SUCCESS] "
                            f"violation_index={violation_index} "
                            f"| violation_type={violation_type}"
                        )

                        emitted = notify_method(socket_violation)

                        if emitted:
                            print(
                                "[SOCKET][VIOLATION EMISSION REQUESTED] "
                                f"violation_type={violation_type}"
                            )

                        else:
                            print(
                                "[SOCKET][VIOLATION EMISSION FAILED] "
                                f"violation_type={violation_type}"
                            )

                    except Exception as socket_error:
                        print(
                            "[SOCKET][VIOLATION EMISSION ERROR] "
                            f"violation_index={violation_index} "
                            f"| error={socket_error}"
                        )

            else:
                print(
                    "[SOCKET][VIOLATION NOT EMITTED] "
                    "Socket client does not provide "
                    "notify_proctor_violation()."
                )

        # REST persistence succeeded, so clear these violations
        # regardless of whether the real-time socket notification
        # was delivered successfully.
        return []

    reason = result.get("reason")

    if reason == "API_COOLDOWN":
        return pending_violations

    print("[API] Violation batch was not " "sent.")

    if reason:
        print(f"[API] Reason: {reason}")

    return pending_violations


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

    pending_violations = pipeline.get("pending_violations")

    if pending_violations is None:
        pending_violations = []

        pipeline["pending_violations"] = pending_violations

    tracking_start_event = pipeline.get("tracking_start_event")

    # Backward compatibility:
    # If an older caller invokes this loop without the new
    # tracking_start_event, preserve the previous behavior
    # and begin detection immediately.
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
            "[PROCTOR] Violation tracking is PAUSED until the secure exam page signals readiness."
        )

    while True:

        if exam_completed_flag:

            print()

            print("[PROCTOR] Exam completion " "received. Stopping detection.")

            break

        success, frame = camera.read()

        if not success or frame is None:
            print("[CAMERA] Failed to read frame.")

            time.sleep(0.05)

            continue

        # Keep consuming camera frames so the camera remains warm and
        # does not build up a stale capture buffer, but do not execute
        # any detector, anomaly timer, evidence capture, REST request,
        # or violation socket emission before the frontend start signal.
        if not tracking_start_event.is_set():

            current_time = time.time()

            if current_time - last_waiting_log_time >= 2.0:

                print(
                    "[PROCTOR] Waiting for secure exam page. Violation tracking remains paused."
                )

                last_waiting_log_time = current_time

            time.sleep(0.02)

            continue

        if not tracking_started_logged:

            tracking_started_logged = True

            print()

            print(
                "[PROCTOR] Frontend readiness confirmed. Starting violation tracking."
            )

            print("[PROCTOR] Detection pipeline started.")

        frame_count += 1

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
                "[FACE LANDMARKER] " "Processing error:",
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

        object_anomalies = get_object_anomalies(object_detections)

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

        pending_violations = queue_api_violations(
            anomaly_results,
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
                print("[FACE LANDMARKER] " "NOT AVAILABLE")

            if gaze_result:
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

            if head_result:
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

            if posture_result:

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

    finally:

        try:

            pending_violations = pipeline.get(
                "pending_violations",
                [],
            )

            proctoring_api = pipeline.get("proctoring_api")

            proctor_socket = pipeline.get("proctor_socket")

            if pending_violations and proctoring_api is not None:

                pending_violations = send_pending_violations(
                    proctoring_api=proctoring_api,
                    pending_violations=pending_violations,
                    proctor_socket=proctor_socket,
                )

                pipeline["pending_violations"] = pending_violations

        except Exception as error:

            print(
                "[API] Final violation " "submission error:",
                error,
            )

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

        # Attach the new tracking gate before starting the socket.
        # The detection loop will keep the camera/microphone alive,
        # but all detector/anomaly/evidence work remains paused until
        # this event is set by the validated socket start signal.
        pipeline["tracking_start_event"] = tracking_start_event

        socket_client = start_proctor_socket(
            session,
            tracking_start_event=tracking_start_event,
        )

        # Attach the same live socket client to the running pipeline.
        # This allows successfully persisted REST violations to be
        # forwarded to Node and then broadcast to the browser room.
        pipeline["proctor_socket"] = socket_client

        if socket_client is not None:

            print("[PROCTOR] Socket client created " "successfully.")

        else:

            raise RuntimeError(
                "Secure proctor socket could not be started. "
                "The exam cannot begin without the tracking-start channel."
            )

        kiosk, _ = start_kiosk(
            token,
            proctor_socket=socket_client,
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
                )

            except Exception:
                pass


if __name__ == "__main__":
    main()
