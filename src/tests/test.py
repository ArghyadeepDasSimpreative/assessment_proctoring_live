# import os
# import time

# import cv2
# import sounddevice as sd

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

# from src.core.anomaly_manager import (
#     AnomalyManager,
# )

# from src.evidence.evidence_store import (
#     EvidenceStore,
# )

# CAMERA_INDEX = 0

# CAMERA_WIDTH = 640

# CAMERA_HEIGHT = 480

# MIC_CHANNELS = 1

# WINDOW_NAME = "Skolariq Proctoring - Production Engine Preview Test"


# ANOMALY_ORDER = [
#     "NO_FACE",
#     "MULTIPLE_FACES",
#     "GAZE_AWAY",
#     "HEAD_AWAY",
#     "PHONE_DETECTED",
#     "BOOK_DETECTED",
#     "EXTRA_PERSON",
#     "BODY_LEAN_LEFT",
#     "BODY_LEAN_RIGHT",
#     "LEFT_ARM_RAISED",
#     "RIGHT_ARM_RAISED",
#     "UNUSUAL_ARM_MOVEMENT",
#     "UPPER_BODY_NOT_VISIBLE",
# ]


# def open_camera():
#     """
#     Same camera startup behavior as main.py.
#     """

#     if os.name == "nt":

#         camera = cv2.VideoCapture(
#             CAMERA_INDEX,
#             cv2.CAP_DSHOW,
#         )

#     else:

#         camera = cv2.VideoCapture(CAMERA_INDEX)

#     if not camera.isOpened():

#         raise RuntimeError(f"Unable to open camera index {CAMERA_INDEX}.")

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

#         raise RuntimeError("Camera opened but failed to provide a valid frame.")

#     return camera


# def start_microphone():
#     """
#     Same microphone startup behavior as main.py.
#     """

#     try:

#         device_info = sd.query_devices(kind="input")

#         if not device_info:

#             raise RuntimeError("No microphone input device was found.")

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

#         raise RuntimeError(f"Unable to start microphone: {error}") from error


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
#     """
#     Same object-to-anomaly mapping as main.py.
#     """

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


# def draw_face_box(
#     frame,
#     face,
#     mirrored=False,
# ):

#     coordinates = get_face_coordinates(face)

#     if coordinates is None:

#         return None

#     x = coordinates["x"]

#     y = coordinates["y"]

#     width = coordinates["width"]

#     height = coordinates["height"]

#     frame_width = frame.shape[1]

#     frame_height = frame.shape[0]

#     if mirrored:

#         x = frame_width - (x + width)

#     x1 = max(
#         0,
#         x,
#     )

#     y1 = max(
#         0,
#         y,
#     )

#     x2 = min(
#         frame_width - 1,
#         x + width,
#     )

#     y2 = min(
#         frame_height - 1,
#         y + height,
#     )

#     if x2 <= x1 or y2 <= y1:

#         return None

#     cv2.rectangle(
#         frame,
#         (
#             x1,
#             y1,
#         ),
#         (
#             x2,
#             y2,
#         ),
#         (
#             0,
#             255,
#             0,
#         ),
#         2,
#     )

#     return {
#         "x": x1,
#         "y": y1,
#         "x2": x2,
#         "y2": y2,
#     }


# def draw_object_box(
#     frame,
#     detection,
#     mirrored=False,
# ):

#     if not isinstance(
#         detection,
#         dict,
#     ):

#         return

#     try:

#         x1 = int(detection["x"])

#         y1 = int(detection["y"])

#         x2 = int(detection["x2"])

#         y2 = int(detection["y2"])

#         label = str(
#             detection.get(
#                 "label",
#                 "OBJECT",
#             )
#         )

#         confidence = float(
#             detection.get(
#                 "confidence",
#                 0.0,
#             )
#         )

#     except (
#         KeyError,
#         TypeError,
#         ValueError,
#     ):

#         return

#     if mirrored:

#         frame_width = frame.shape[1]

#         old_x1 = x1
#         old_x2 = x2

#         x1 = frame_width - old_x2

#         x2 = frame_width - old_x1

#     x1 = max(
#         0,
#         min(
#             frame.shape[1] - 1,
#             x1,
#         ),
#     )

#     x2 = max(
#         0,
#         min(
#             frame.shape[1] - 1,
#             x2,
#         ),
#     )

#     y1 = max(
#         0,
#         min(
#             frame.shape[0] - 1,
#             y1,
#         ),
#     )

#     y2 = max(
#         0,
#         min(
#             frame.shape[0] - 1,
#             y2,
#         ),
#     )

#     if x2 <= x1 or y2 <= y1:

#         return

#     cv2.rectangle(
#         frame,
#         (
#             x1,
#             y1,
#         ),
#         (
#             x2,
#             y2,
#         ),
#         (
#             0,
#             165,
#             255,
#         ),
#         2,
#     )

#     text = f"{label} " f"{confidence:.2f}"

#     cv2.putText(
#         frame,
#         text,
#         (
#             x1,
#             max(
#                 18,
#                 y1 - 6,
#             ),
#         ),
#         cv2.FONT_HERSHEY_SIMPLEX,
#         0.45,
#         (
#             0,
#             165,
#             255,
#         ),
#         2,
#         cv2.LINE_AA,
#     )


# def get_preview_point(
#     landmark,
#     width,
#     height,
#     minimum_visibility=0.50,
# ):

#     if landmark is None:

#         return None

#     if (
#         getattr(
#             landmark,
#             "visibility",
#             0.0,
#         )
#         < minimum_visibility
#     ):

#         return None

#     raw_x = int(landmark.x * width)

#     raw_y = int(landmark.y * height)

#     mirrored_x = width - 1 - raw_x

#     return (
#         mirrored_x,
#         raw_y,
#     )


# def draw_pose(
#     frame,
#     pose_result,
# ):

#     if not pose_result.get(
#         "valid",
#         False,
#     ):

#         return

#     landmarks = pose_result.get("landmarks")

#     if landmarks is None or len(landmarks) < 17:

#         return

#     height, width = frame.shape[:2]

#     indexes = [
#         11,
#         12,
#         13,
#         14,
#         15,
#         16,
#     ]

#     points = {}

#     for index in indexes:

#         point = get_preview_point(
#             landmarks[index],
#             width,
#             height,
#         )

#         points[index] = point

#         if point is not None:

#             cv2.circle(
#                 frame,
#                 point,
#                 5,
#                 (
#                     255,
#                     0,
#                     255,
#                 ),
#                 -1,
#             )

#     connections = [
#         (
#             11,
#             12,
#         ),
#         (
#             11,
#             13,
#         ),
#         (
#             13,
#             15,
#         ),
#         (
#             12,
#             14,
#         ),
#         (
#             14,
#             16,
#         ),
#     ]

#     for (
#         start,
#         end,
#     ) in connections:

#         start_point = points.get(start)

#         end_point = points.get(end)

#         if start_point is not None and end_point is not None:

#             cv2.line(
#                 frame,
#                 start_point,
#                 end_point,
#                 (
#                     255,
#                     0,
#                     255,
#                 ),
#                 2,
#             )


# def draw_anomaly_panel(
#     frame,
#     results,
# ):

#     panel_height = 40 + (len(ANOMALY_ORDER) * 22)

#     panel_height = min(
#         panel_height,
#         frame.shape[0] - 5,
#     )

#     x1 = frame.shape[1] - 335

#     y1 = 5

#     x2 = frame.shape[1] - 5

#     y2 = y1 + panel_height

#     overlay = frame.copy()

#     cv2.rectangle(
#         overlay,
#         (
#             x1,
#             y1,
#         ),
#         (
#             x2,
#             y2,
#         ),
#         (
#             0,
#             0,
#             0,
#         ),
#         -1,
#     )

#     cv2.addWeighted(
#         overlay,
#         0.72,
#         frame,
#         0.28,
#         0,
#         frame,
#     )

#     cv2.putText(
#         frame,
#         "ANOMALY STATUS",
#         (
#             x1 + 10,
#             y1 + 22,
#         ),
#         cv2.FONT_HERSHEY_SIMPLEX,
#         0.50,
#         (
#             255,
#             255,
#             255,
#         ),
#         2,
#         cv2.LINE_AA,
#     )

#     y = y1 + 45

#     for event_type in ANOMALY_ORDER:

#         result = results.get(
#             event_type,
#             {},
#         )

#         confirmed = bool(
#             result.get(
#                 "confirmed",
#                 False,
#             )
#         )

#         active = bool(
#             result.get(
#                 "active",
#                 False,
#             )
#         )

#         captured = bool(
#             result.get(
#                 "captured",
#                 False,
#             )
#         )

#         if captured:

#             status = "CAPTURED"

#             text_color = (
#                 0,
#                 0,
#                 255,
#             )

#         elif confirmed:

#             status = "CONFIRMED"

#             text_color = (
#                 0,
#                 165,
#                 255,
#             )

#         elif active:

#             status = "ACTIVE"

#             text_color = (
#                 0,
#                 255,
#                 255,
#             )

#         else:

#             status = "NORMAL"

#             text_color = (
#                 0,
#                 255,
#                 0,
#             )

#         short_name = event_type.replace(
#             "_",
#             " ",
#         )

#         text = f"{short_name}: " f"{status}"

#         cv2.putText(
#             frame,
#             text,
#             (
#                 x1 + 10,
#                 y,
#             ),
#             cv2.FONT_HERSHEY_SIMPLEX,
#             0.36,
#             text_color,
#             1,
#             cv2.LINE_AA,
#         )

#         y += 22

#         if y >= frame.shape[0] - 8:

#             break


# def draw_top_status(
#     frame,
#     face_count,
#     landmark_valid,
#     gaze_result,
#     head_result,
#     pose_result,
#     posture_result,
#     object_anomalies,
# ):

#     cv2.rectangle(
#         frame,
#         (
#             0,
#             0,
#         ),
#         (
#             335,
#             164,
#         ),
#         (
#             0,
#             0,
#             0,
#         ),
#         -1,
#     )

#     if face_count == 0:

#         face_text = "NO FACE"

#     elif face_count == 1:

#         face_text = "SINGLE FACE"

#     else:

#         face_text = f"MULTIPLE FACES " f"({face_count})"

#     cv2.putText(
#         frame,
#         f"Face: {face_text}",
#         (
#             10,
#             22,
#         ),
#         cv2.FONT_HERSHEY_SIMPLEX,
#         0.45,
#         (
#             255,
#             255,
#             255,
#         ),
#         1,
#         cv2.LINE_AA,
#     )

#     cv2.putText(
#         frame,
#         ("Landmarks: " f"{'VALID' if landmark_valid else 'NOT AVAILABLE'}"),
#         (
#             10,
#             44,
#         ),
#         cv2.FONT_HERSHEY_SIMPLEX,
#         0.40,
#         (
#             255,
#             255,
#             255,
#         ),
#         1,
#         cv2.LINE_AA,
#     )

#     cv2.putText(
#         frame,
#         (
#             "Gaze: "
#             f"{gaze_result.get('direction', 'UNKNOWN')} "
#             "| away="
#             f"{gaze_result.get('away', False)}"
#         ),
#         (
#             10,
#             66,
#         ),
#         cv2.FONT_HERSHEY_SIMPLEX,
#         0.38,
#         (
#             255,
#             255,
#             255,
#         ),
#         1,
#         cv2.LINE_AA,
#     )

#     cv2.putText(
#         frame,
#         (
#             "Head: "
#             f"{head_result.get('direction', 'UNKNOWN')} "
#             "| away="
#             f"{head_result.get('away', False)}"
#         ),
#         (
#             10,
#             88,
#         ),
#         cv2.FONT_HERSHEY_SIMPLEX,
#         0.38,
#         (
#             255,
#             255,
#             255,
#         ),
#         1,
#         cv2.LINE_AA,
#     )

#     cv2.putText(
#         frame,
#         (
#             "Pose: "
#             f"{'VALID' if pose_result.get('valid', False) else 'INVALID'} "
#             "| upper_body="
#             f"{posture_result.get('upper_body_visible', False)}"
#         ),
#         (
#             10,
#             110,
#         ),
#         cv2.FONT_HERSHEY_SIMPLEX,
#         0.36,
#         (
#             255,
#             255,
#             255,
#         ),
#         1,
#         cv2.LINE_AA,
#     )

#     cv2.putText(
#         frame,
#         (
#             "Arms: "
#             f"L={posture_result.get('left_arm_raised', False)} "
#             f"R={posture_result.get('right_arm_raised', False)} "
#             f"Move={posture_result.get('unusual_arm_movement', False)}"
#         ),
#         (
#             10,
#             132,
#         ),
#         cv2.FONT_HERSHEY_SIMPLEX,
#         0.34,
#         (
#             255,
#             255,
#             255,
#         ),
#         1,
#         cv2.LINE_AA,
#     )

#     cv2.putText(
#         frame,
#         (
#             "Objects: "
#             f"P={len(object_anomalies['person_detections'])} "
#             f"Phone={object_anomalies['phone_detected']} "
#             f"Book={object_anomalies['book_detected']}"
#         ),
#         (
#             10,
#             154,
#         ),
#         cv2.FONT_HERSHEY_SIMPLEX,
#         0.31,
#         (
#             255,
#             255,
#             255,
#         ),
#         1,
#         cv2.LINE_AA,
#     )


# def print_instructions():

#     print()

#     print("=" * 80)

#     print("SKOLARIQ PRODUCTION PROCTORING ENGINE PREVIEW TEST")

#     print("=" * 80)

#     print()

#     print(
#         "This test uses the same camera/microphone setup, "
#         "model constructors, detector cadence, PostureMonitor, "
#         "AnomalyManager inputs, metadata structure and evidence "
#         "capture path as main.py."
#     )

#     print()

#     print(
#         "Only the production-only kiosk, keyboard lockdown, "
#         "authentication, REST submission and Socket.IO transport "
#         "are intentionally omitted."
#     )

#     print()

#     print("Q : Quit")

#     print()

#     print("FACE")

#     print("  No face              -> NO_FACE")

#     print("  Second person        -> MULTIPLE_FACES / EXTRA_PERSON")

#     print()

#     print("GAZE")

#     print("  Look away            -> GAZE_AWAY")

#     print()

#     print("HEAD")

#     print("  Turn head away       -> HEAD_AWAY")

#     print()

#     print("OBJECTS")

#     print("  Show phone           -> PHONE_DETECTED")

#     print("  Show book            -> BOOK_DETECTED")

#     print("  Second person        -> EXTRA_PERSON")

#     print()

#     print("POSTURE")

#     print("  Lean LEFT            -> BODY_LEAN_LEFT")

#     print("  Lean RIGHT           -> BODY_LEAN_RIGHT")

#     print("  Raise LEFT arm       -> LEFT_ARM_RAISED")

#     print("  Raise RIGHT arm      -> RIGHT_ARM_RAISED")

#     print("  Move arms rapidly    -> UNUSUAL_ARM_MOVEMENT")

#     print("  Upper body hidden    -> UPPER_BODY_NOT_VISIBLE")

#     print()

#     print("=" * 80)

#     print()


# def main():

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

#     try:

#         print_instructions()

#         print()

#         print("[TEST] Performing mandatory camera and microphone check...")

#         print("[CAMERA] Starting camera...")

#         camera = open_camera()

#         print("[CAMERA] Camera opened successfully.")

#         print("[MICROPHONE] Starting microphone...")

#         microphone = start_microphone()

#         print("[MICROPHONE] Microphone started successfully.")

#         print("[YUNET] Loading face detector...")

#         face_detector = YuNetFaceDetector()

#         print("[YUNET] Face detector loaded successfully.")

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

#         # IMPORTANT:
#         # main.py uses the default PostureMonitor configuration.
#         # The test must do exactly the same so thresholds/behavior
#         # cannot drift away from production.
#         posture_monitor = PostureMonitor()

#         print("[POSTURE] Posture monitor initialized.")

#         print("[YOLO26] Loading object detector...")

#         object_detector = YOLO26ObjectDetector()

#         print("[YOLO26] Object detector loaded successfully.")

#         print("[EVIDENCE] Initializing evidence store...")

#         evidence_store = EvidenceStore(
#             student_id="local_test",
#             exam_id="local_test",
#             schedule_id="local_test",
#             session_id="local_test",
#         )

#         print("[EVIDENCE] Evidence store initialized.")

#         print("[ANOMALY] Initializing anomaly manager...")

#         anomaly_manager = AnomalyManager(evidence_store=evidence_store)

#         print("[ANOMALY] Anomaly manager initialized.")

#         print()

#         print("[TEST] Production-equivalent detection pipeline initialized.")

#         print("[TEST] Starting full detection loop with camera preview.")

#         print()

#         cv2.namedWindow(
#             WINDOW_NAME,
#             cv2.WINDOW_NORMAL,
#         )

#         cv2.resizeWindow(
#             WINDOW_NAME,
#             1100,
#             720,
#         )

#         frame_count = 0

#         last_log_time = 0.0

#         while True:

#             success, frame = camera.read()

#             if not success or frame is None:

#                 print("[CAMERA] Failed to read frame.")

#                 time.sleep(0.05)

#                 continue

#             frame_count += 1

#             try:

#                 faces = face_detector.detect(frame)

#                 if faces is None:

#                     faces = []

#             except Exception as error:

#                 print(
#                     "[YUNET] Detection error:",
#                     error,
#                 )

#                 faces = []

#             face_count = len(faces)

#             try:

#                 landmark_result = face_landmarker.process(frame)

#             except Exception as error:

#                 print(
#                     "[FACE LANDMARKER] Processing error:",
#                     error,
#                 )

#                 landmark_result = {
#                     "valid": False,
#                     "landmarks": None,
#                     "face_count": 0,
#                 }

#             landmark_valid = bool(
#                 landmark_result.get(
#                     "valid",
#                     False,
#                 )
#             )

#             landmarks = landmark_result.get("landmarks") if landmark_result else None

#             if landmarks is not None and landmark_valid:

#                 try:

#                     gaze_result = gaze_tracker.process(
#                         landmarks,
#                         frame.shape,
#                     )

#                 except Exception as error:

#                     print(
#                         "[GAZE] Processing error:",
#                         error,
#                     )

#                     gaze_result = {
#                         "direction": "UNKNOWN",
#                         "valid": False,
#                         "calibrated": False,
#                         "away": False,
#                         "away_duration": 0.0,
#                     }

#             else:

#                 gaze_result = {
#                     "direction": "UNKNOWN",
#                     "valid": False,
#                     "calibrated": getattr(
#                         gaze_tracker,
#                         "calibrated",
#                         False,
#                     ),
#                     "away": False,
#                     "away_duration": 0.0,
#                 }

#             if landmarks is not None and landmark_valid:

#                 try:

#                     head_result = head_tracker.process(
#                         landmarks,
#                         frame.shape,
#                     )

#                 except Exception as error:

#                     print(
#                         "[HEAD] Processing error:",
#                         error,
#                     )

#                     head_result = {
#                         "direction": "UNKNOWN",
#                         "valid": False,
#                         "yaw": None,
#                         "pitch": None,
#                         "roll": None,
#                         "away": False,
#                         "away_duration": 0.0,
#                     }

#             else:

#                 head_result = {
#                     "direction": "UNKNOWN",
#                     "valid": False,
#                     "yaw": None,
#                     "pitch": None,
#                     "roll": None,
#                     "away": False,
#                     "away_duration": 0.0,
#                 }

#             try:

#                 pose_result = pose_landmarker.process(frame)

#             except Exception as error:

#                 print(
#                     "[POSE] Processing error:",
#                     error,
#                 )

#                 pose_result = {
#                     "valid": False,
#                     "pose_count": 0,
#                     "landmarks": None,
#                     "world_landmarks": None,
#                 }

#             try:

#                 posture_result = posture_monitor.process(
#                     pose_result,
#                     frame.shape,
#                 )

#             except Exception as error:

#                 print(
#                     "[POSTURE] Processing error:",
#                     error,
#                 )

#                 posture_result = {
#                     "valid": False,
#                     "upper_body_visible": False,
#                     "leaning_left": False,
#                     "leaning_right": False,
#                     "left_arm_raised": False,
#                     "right_arm_raised": False,
#                     "unusual_arm_movement": False,
#                     "left_arm_movement": 0.0,
#                     "right_arm_movement": 0.0,
#                 }

#             try:

#                 object_detections = object_detector.detect(frame)

#                 if object_detections is None:

#                     object_detections = []

#             except Exception as error:

#                 print(
#                     "[YOLO26] Detection error:",
#                     error,
#                 )

#                 object_detections = []

#             object_anomaly_state = get_object_anomalies(object_detections)

#             anomaly_metadata = {
#                 "frame_number": frame_count,
#                 "face_count": face_count,
#                 "landmark_valid": landmark_valid,
#                 "gaze": {
#                     "direction": gaze_result.get(
#                         "direction",
#                         "UNKNOWN",
#                     ),
#                     "valid": gaze_result.get(
#                         "valid",
#                         False,
#                     ),
#                     "calibrated": gaze_result.get(
#                         "calibrated",
#                         False,
#                     ),
#                     "away": gaze_result.get(
#                         "away",
#                         False,
#                     ),
#                     "away_duration": gaze_result.get(
#                         "away_duration",
#                         0.0,
#                     ),
#                 },
#                 "head": {
#                     "direction": head_result.get(
#                         "direction",
#                         "UNKNOWN",
#                     ),
#                     "valid": head_result.get(
#                         "valid",
#                         False,
#                     ),
#                     "yaw": head_result.get("yaw"),
#                     "pitch": head_result.get("pitch"),
#                     "roll": head_result.get("roll"),
#                     "away": head_result.get(
#                         "away",
#                         False,
#                     ),
#                     "away_duration": head_result.get(
#                         "away_duration",
#                         0.0,
#                     ),
#                 },
#                 "pose": {
#                     "valid": posture_result.get(
#                         "valid",
#                         False,
#                     ),
#                     "pose_count": pose_result.get(
#                         "pose_count",
#                         0,
#                     ),
#                     "upper_body_visible": posture_result.get(
#                         "upper_body_visible",
#                         False,
#                     ),
#                     "leaning_left": posture_result.get(
#                         "leaning_left",
#                         False,
#                     ),
#                     "leaning_right": posture_result.get(
#                         "leaning_right",
#                         False,
#                     ),
#                     "left_arm_raised": posture_result.get(
#                         "left_arm_raised",
#                         False,
#                     ),
#                     "right_arm_raised": posture_result.get(
#                         "right_arm_raised",
#                         False,
#                     ),
#                     "unusual_arm_movement": posture_result.get(
#                         "unusual_arm_movement",
#                         False,
#                     ),
#                     "left_arm_movement": posture_result.get(
#                         "left_arm_movement",
#                         0.0,
#                     ),
#                     "right_arm_movement": posture_result.get(
#                         "right_arm_movement",
#                         0.0,
#                     ),
#                     "shoulder_center_x": posture_result.get("shoulder_center_x"),
#                     "shoulder_width": posture_result.get("shoulder_width"),
#                 },
#                 "objects": object_detections,
#             }

#             anomaly_results = anomaly_manager.update_many(
#                 anomalies={
#                     "NO_FACE": (face_count == 0),
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
#                     "PHONE_DETECTED": object_anomaly_state["phone_detected"],
#                     "BOOK_DETECTED": object_anomaly_state["book_detected"],
#                     "EXTRA_PERSON": object_anomaly_state["extra_person_detected"],
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

#             preview_frame = cv2.flip(
#                 frame,
#                 1,
#             )

#             for face in faces:

#                 draw_face_box(
#                     preview_frame,
#                     face,
#                     mirrored=True,
#                 )

#             for detection in object_detections:

#                 draw_object_box(
#                     preview_frame,
#                     detection,
#                     mirrored=True,
#                 )

#             draw_pose(
#                 preview_frame,
#                 pose_result,
#             )

#             draw_top_status(
#                 preview_frame,
#                 face_count,
#                 landmark_valid,
#                 gaze_result,
#                 head_result,
#                 pose_result,
#                 posture_result,
#                 object_anomaly_state,
#             )

#             draw_anomaly_panel(
#                 preview_frame,
#                 anomaly_results,
#             )

#             current_time = time.time()

#             if current_time - last_log_time >= 1.0:

#                 if face_count == 0:

#                     print("[DETECTION] NO FACE")

#                 elif face_count == 1:

#                     print("[DETECTION] SINGLE FACE")

#                 else:

#                     print("[DETECTION] " f"MULTIPLE FACES: " f"{face_count}")

#                 if landmark_valid:

#                     print("[FACE LANDMARKER] VALID")

#                 else:

#                     print("[FACE LANDMARKER] NOT AVAILABLE")

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

#                 if object_detections:

#                     for detection in object_detections:

#                         print(
#                             "[OBJECT] "
#                             f"{detection.get('label', 'OBJECT')} "
#                             "| confidence="
#                             f"{float(detection.get('confidence', 0.0)):.3f} "
#                             "| box=("
#                             f"{detection.get('x')},"
#                             f"{detection.get('y')},"
#                             f"{detection.get('x2')},"
#                             f"{detection.get('y2')}"
#                             ")"
#                         )

#                 else:

#                     print("[OBJECT] No monitored objects detected.")

#                 for (
#                     event_type,
#                     result,
#                 ) in anomaly_results.items():

#                     if result.get(
#                         "confirmed",
#                         False,
#                     ):

#                         cooldown_remaining = float(
#                             result.get(
#                                 "cooldown_remaining",
#                                 0.0,
#                             )
#                         )

#                         print(
#                             "[ANOMALY] "
#                             f"{event_type} "
#                             "| confirmed=True "
#                             "| captured="
#                             f"{result.get('captured', False)} "
#                             "| cooldown_remaining="
#                             f"{cooldown_remaining:.1f}s"
#                         )

#                 last_log_time = current_time

#             cv2.imshow(
#                 WINDOW_NAME,
#                 preview_frame,
#             )

#             key = cv2.waitKey(1) & 0xFF

#             if key in (
#                 ord("q"),
#                 ord("Q"),
#             ):

#                 print("[TEST] Q pressed.")

#                 break

#     except KeyboardInterrupt:

#         print()

#         print("[TEST] Keyboard interrupt.")

#     except Exception as error:

#         print()

#         print(
#             "[TEST] Fatal error:",
#             error,
#         )

#     finally:

#         print()

#         print("[TEST] Cleaning up...")

#         if anomaly_manager is not None:

#             try:

#                 anomaly_manager.close()

#             except Exception as error:

#                 print(
#                     "[ANOMALY] Cleanup error:",
#                     error,
#                 )

#         if evidence_store is not None:

#             try:

#                 evidence_store.close()

#             except Exception as error:

#                 print(
#                     "[EVIDENCE] Cleanup error:",
#                     error,
#                 )

#         if posture_monitor is not None:

#             try:

#                 posture_monitor.reset()

#             except Exception as error:

#                 print(
#                     "[POSTURE] Cleanup error:",
#                     error,
#                 )

#         if microphone is not None:

#             try:

#                 stop_microphone(microphone)

#             except Exception as error:

#                 print(
#                     "[MICROPHONE] Cleanup error:",
#                     error,
#                 )

#         if camera is not None:

#             try:

#                 camera.release()

#             except Exception as error:

#                 print(
#                     "[CAMERA] Cleanup error:",
#                     error,
#                 )

#         if object_detector is not None:

#             try:

#                 object_detector.close()

#             except Exception as error:

#                 print(
#                     "[YOLO26] Cleanup error:",
#                     error,
#                 )

#         if pose_landmarker is not None:

#             try:

#                 pose_landmarker.close()

#             except Exception as error:

#                 print(
#                     "[POSE] Cleanup error:",
#                     error,
#                 )

#         if gaze_tracker is not None:

#             try:

#                 gaze_tracker.close()

#             except Exception as error:

#                 print(
#                     "[GAZE] Cleanup error:",
#                     error,
#                 )

#         if head_tracker is not None:

#             try:

#                 head_tracker.close()

#             except Exception as error:

#                 print(
#                     "[HEAD] Cleanup error:",
#                     error,
#                 )

#         if face_landmarker is not None:

#             try:

#                 face_landmarker.close()

#             except Exception as error:

#                 print(
#                     "[FACE LANDMARKER] Cleanup error:",
#                     error,
#                 )

#         if face_detector is not None:

#             try:

#                 face_detector.close()

#             except Exception as error:

#                 print(
#                     "[YUNET] Cleanup error:",
#                     error,
#                 )

#         try:

#             cv2.destroyAllWindows()

#         except Exception:

#             pass

#         print("[TEST] Finished.")


# if __name__ == "__main__":

#     main()


import os
import queue
import time

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

    if calibrating:

        voice_text = "CALIBRATING"

        voice_color = (
            0,
            255,
            255,
        )

    elif evidence_captured:

        voice_text = "CONFIRMED / CAPTURED"

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
            "Voice time: " f"{voice_duration:.2f}s / 3.00s",
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
        "required_duration": 3.0,
        "cooldown": 0.0,
        "cooldown_remaining": 0.0,
        "evidence": None,
        "api_violation": None,
    }


def process_audio_events(
    audio_event_queue,
    anomaly_manager,
    current_result,
):

    result = dict(current_result or empty_voice_anomaly_result())

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

    return result


def print_instructions():

    print()

    print("=" * 80)

    print("SKOLARIQ PRODUCTION PROCTORING ENGINE PREVIEW TEST")

    print("=" * 80)

    print()

    print(
        "This test uses the same camera, microphone, "
        "detectors, anomaly manager and evidence pipeline "
        "intended for the native proctor application."
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

    print("  Normal speech        -> VOICE_DETECTED after 3 seconds")

    print("  Quiet whisper        -> whisper-sensitive detection")

    print("  Short sound < 3 sec  -> no VOICE_DETECTED evidence")

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
            student_id="local_test",
            exam_id="local_test",
            schedule_id="local_test",
            session_id="local_test",
        )

        print("[EVIDENCE] Evidence store initialized.")

        print("[ANOMALY] Initializing anomaly manager...")

        anomaly_manager = AnomalyManager(evidence_store=evidence_store)

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
