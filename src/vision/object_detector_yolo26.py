# """
# Skolariq - YOLO26n Object Detector
# ==================================

# Production-ready YOLO26n ONNX detector.

# Responsibilities:
#     - Detect PERSON
#     - Detect CELL_PHONE
#     - Detect BOOK
#     - Preserve detections for partially visible objects
#     - Preserve detections touching the camera frame edges
#     - Perform class-aware NMS
#     - Return coordinates in ORIGINAL camera-frame space

# Runtime:
#     - ONNX Runtime
#     - CPUExecutionProvider

# Model:
#     models/yolo26n.onnx

# Public interface:

#     detector = YOLO26ObjectDetector()

#     detections = detector.detect(frame)

#     detector.close()


# Detection format:

#     {
#         "class_id": 67,
#         "label": "CELL_PHONE",
#         "confidence": 0.81,
#         "x": 100,
#         "y": 120,
#         "x2": 180,
#         "y2": 300,
#     }

# IMPORTANT
# ---------
# This detector does NOT contain separate rules such as:

#     "if half a phone is visible, call it a phone"

# That decision is made by the YOLO26n model itself.

# This class is responsible for making sure valid model detections
# are not unnecessarily lost because of preprocessing, confidence
# thresholding, coordinate conversion, or NMS.
# """

# from pathlib import Path

# import cv2
# import numpy as np
# import onnxruntime as ort


# class YOLO26ObjectDetector:

#     # ============================================================
#     # COCO CLASSES
#     # ============================================================

#     MONITORED_CLASSES = {
#         0: "PERSON",
#         67: "CELL_PHONE",
#         73: "BOOK",
#     }

#     # ============================================================
#     # CONFIDENCE THRESHOLDS
#     #
#     # Phone and book are intentionally lower than PERSON.
#     #
#     # This is important for our proctoring use case because
#     # partially visible objects often have lower confidence.
#     #
#     # These are evaluation/initial-production values and can
#     # later be tuned using real camera evidence.
#     # ============================================================

#     CLASS_THRESHOLDS = {
#         0: 0.35,
#         67: 0.25,
#         73: 0.25,
#     }

#     DEFAULT_THRESHOLD = 0.35

#     # ============================================================
#     # MODEL INPUT
#     # ============================================================

#     DEFAULT_INPUT_WIDTH = 640
#     DEFAULT_INPUT_HEIGHT = 640

#     # ============================================================
#     # NMS
#     # ============================================================

#     DEFAULT_NMS_THRESHOLD = 0.45

#     # ============================================================
#     # CONSTRUCTOR
#     # ============================================================

#     def __init__(
#         self,
#         model_path=None,
#         nms_threshold=DEFAULT_NMS_THRESHOLD,
#         intra_op_num_threads=1,
#         inter_op_num_threads=1,
#     ):
#         """
#         Initialize YOLO26n ONNX detector.

#         Parameters
#         ----------
#         model_path:
#             Optional custom ONNX model.

#             Default:

#                 <project-root>/models/yolo26n.onnx

#         nms_threshold:
#             IoU threshold for class-aware NMS.

#         intra_op_num_threads:
#             ONNX Runtime CPU thread count.

#         inter_op_num_threads:
#             ONNX Runtime CPU thread count.
#         """

#         # ========================================================
#         # MODEL PATH
#         # ========================================================

#         if model_path is None:

#             project_root = Path(__file__).resolve().parents[2]

#             model_path = project_root / "models" / "yolo26n.onnx"

#         self.model_path = Path(model_path)

#         if not self.model_path.exists():

#             raise RuntimeError("YOLO26n ONNX model not found: " f"{self.model_path}")

#         # ========================================================
#         # NMS CONFIGURATION
#         # ========================================================

#         self.nms_threshold = float(nms_threshold)

#         if not 0.0 <= self.nms_threshold <= 1.0:

#             raise ValueError("nms_threshold must be between " "0.0 and 1.0.")

#         # ========================================================
#         # ONNX SESSION OPTIONS
#         # ========================================================

#         session_options = ort.SessionOptions()

#         session_options.graph_optimization_level = (
#             ort.GraphOptimizationLevel.ORT_ENABLE_ALL
#         )

#         session_options.intra_op_num_threads = int(intra_op_num_threads)

#         session_options.inter_op_num_threads = int(inter_op_num_threads)

#         # ========================================================
#         # LOAD ONNX MODEL
#         # ========================================================

#         self.session = ort.InferenceSession(
#             str(self.model_path),
#             sess_options=session_options,
#             providers=["CPUExecutionProvider"],
#         )

#         # ========================================================
#         # INPUT
#         # ========================================================

#         inputs = self.session.get_inputs()

#         if not inputs:

#             raise RuntimeError("YOLO26n ONNX model has no inputs.")

#         self.input = inputs[0]

#         self.input_name = self.input.name

#         input_shape = self.input.shape

#         self.input_height = self.DEFAULT_INPUT_HEIGHT

#         self.input_width = self.DEFAULT_INPUT_WIDTH

#         if len(input_shape) >= 4:

#             if isinstance(
#                 input_shape[2],
#                 int,
#             ):

#                 self.input_height = int(input_shape[2])

#             if isinstance(
#                 input_shape[3],
#                 int,
#             ):

#                 self.input_width = int(input_shape[3])

#         # ========================================================
#         # OUTPUTS
#         # ========================================================

#         outputs = self.session.get_outputs()

#         self.output_names = [output.name for output in outputs]

#         if not self.output_names:

#             raise RuntimeError("YOLO26n ONNX model has no outputs.")

#         # ========================================================
#         # STATE
#         # ========================================================

#         self.closed = False

#         # ========================================================
#         # STARTUP LOGGING
#         # ========================================================

#         print("[OBJECT DETECTOR] " "YOLO26n loaded successfully.")

#         print("[OBJECT DETECTOR] " f"Model: {self.model_path}")

#         print(
#             "[OBJECT DETECTOR] "
#             f"Input: "
#             f"{self.input_width}x"
#             f"{self.input_height}"
#         )

#         print("[OBJECT DETECTOR] " f"Output(s): " f"{self.output_names}")

#         print("[OBJECT DETECTOR] " f"Providers: " f"{self.session.get_providers()}")

#         print("[OBJECT DETECTOR] " "Monitored classes: " "PERSON, CELL_PHONE, BOOK")

#     # ============================================================
#     # LETTERBOX
#     # ============================================================

#     def _letterbox(
#         self,
#         frame,
#     ):
#         """
#         Resize frame while preserving aspect ratio.

#         The resized image is centered on a 640x640 canvas.

#         Returns
#         -------
#         blob:
#             NCHW float32 tensor.

#         scale:
#             Resize scale used.

#         pad_x:
#             Horizontal padding.

#         pad_y:
#             Vertical padding.
#         """

#         frame_height, frame_width = frame.shape[:2]

#         if frame_height <= 0 or frame_width <= 0:

#             raise ValueError("Invalid frame dimensions.")

#         # --------------------------------------------------------
#         # Calculate scale.
#         # --------------------------------------------------------

#         scale = min(
#             self.input_width / float(frame_width),
#             self.input_height / float(frame_height),
#         )

#         # --------------------------------------------------------
#         # Calculate resized dimensions.
#         # --------------------------------------------------------

#         resized_width = max(
#             1,
#             int(round(frame_width * scale)),
#         )

#         resized_height = max(
#             1,
#             int(round(frame_height * scale)),
#         )

#         # --------------------------------------------------------
#         # Resize.
#         # --------------------------------------------------------

#         resized = cv2.resize(
#             frame,
#             (
#                 resized_width,
#                 resized_height,
#             ),
#             interpolation=cv2.INTER_LINEAR,
#         )

#         # --------------------------------------------------------
#         # Create letterbox canvas.
#         # --------------------------------------------------------

#         canvas = np.full(
#             (
#                 self.input_height,
#                 self.input_width,
#                 3,
#             ),
#             114,
#             dtype=np.uint8,
#         )

#         # --------------------------------------------------------
#         # Center resized image.
#         # --------------------------------------------------------

#         pad_x = (self.input_width - resized_width) // 2

#         pad_y = (self.input_height - resized_height) // 2

#         canvas[
#             pad_y : pad_y + resized_height,
#             pad_x : pad_x + resized_width,
#         ] = resized

#         # --------------------------------------------------------
#         # BGR -> RGB.
#         # --------------------------------------------------------

#         rgb = cv2.cvtColor(
#             canvas,
#             cv2.COLOR_BGR2RGB,
#         )

#         # --------------------------------------------------------
#         # Normalize.
#         # --------------------------------------------------------

#         blob = rgb.astype(np.float32) / 255.0

#         # --------------------------------------------------------
#         # HWC -> CHW.
#         # --------------------------------------------------------

#         blob = np.transpose(
#             blob,
#             (
#                 2,
#                 0,
#                 1,
#             ),
#         )

#         # --------------------------------------------------------
#         # Add batch dimension.
#         # --------------------------------------------------------

#         blob = np.expand_dims(
#             blob,
#             axis=0,
#         )

#         # --------------------------------------------------------
#         # Ensure contiguous float32 memory.
#         # --------------------------------------------------------

#         blob = np.ascontiguousarray(
#             blob,
#             dtype=np.float32,
#         )

#         return (
#             blob,
#             scale,
#             pad_x,
#             pad_y,
#         )

#     # ============================================================
#     # OUTPUT PREPARATION
#     # ============================================================

#     def _prepare_output(
#         self,
#         output,
#     ):
#         """
#         Normalize YOLO26n output layout.

#         Current exported model:

#             (1, 84, 8400)

#         After squeeze:

#             (84, 8400)

#         Final expected format:

#             (8400, 84)
#         """

#         if output is None:

#             return np.empty(
#                 (
#                     0,
#                     84,
#                 ),
#                 dtype=np.float32,
#             )

#         predictions = np.asarray(output)

#         # --------------------------------------------------------
#         # Remove batch dimension(s).
#         # --------------------------------------------------------

#         predictions = np.squeeze(predictions)

#         if predictions.ndim != 2:

#             return np.empty(
#                 (
#                     0,
#                     84,
#                 ),
#                 dtype=np.float32,
#             )

#         # --------------------------------------------------------
#         # YOLO output is normally:
#         #
#         #     84 x 8400
#         #
#         # Convert to:
#         #
#         #     8400 x 84
#         #
#         # --------------------------------------------------------

#         if predictions.shape[0] < predictions.shape[1]:

#             predictions = predictions.T

#         return predictions.astype(
#             np.float32,
#             copy=False,
#         )

#     # ============================================================
#     # BOX CONVERSION
#     # ============================================================

#     def _convert_box(
#         self,
#         center_x,
#         center_y,
#         width,
#         height,
#         scale,
#         pad_x,
#         pad_y,
#         original_width,
#         original_height,
#     ):
#         """
#         Convert YOLO coordinates from the letterboxed
#         image into ORIGINAL FRAME coordinates.

#         Coordinates are clipped to the camera frame.

#         This is particularly important for objects touching
#         the left/right/top/bottom edge of the camera frame.
#         """

#         # --------------------------------------------------------
#         # Remove padding.
#         # --------------------------------------------------------

#         x1 = center_x - width / 2.0 - pad_x

#         y1 = center_y - height / 2.0 - pad_y

#         x2 = center_x + width / 2.0 - pad_x

#         y2 = center_y + height / 2.0 - pad_y

#         # --------------------------------------------------------
#         # Undo resize.
#         # --------------------------------------------------------

#         x1 /= scale
#         y1 /= scale
#         x2 /= scale
#         y2 /= scale

#         # --------------------------------------------------------
#         # Clip coordinates.
#         #
#         # We intentionally clip instead of discarding boxes
#         # that extend beyond the frame.
#         #
#         # This allows edge-of-frame objects to survive.
#         # --------------------------------------------------------

#         x1 = max(
#             0.0,
#             min(
#                 float(original_width - 1),
#                 x1,
#             ),
#         )

#         y1 = max(
#             0.0,
#             min(
#                 float(original_height - 1),
#                 y1,
#             ),
#         )

#         x2 = max(
#             0.0,
#             min(
#                 float(original_width - 1),
#                 x2,
#             ),
#         )

#         y2 = max(
#             0.0,
#             min(
#                 float(original_height - 1),
#                 y2,
#             ),
#         )

#         return (
#             int(round(x1)),
#             int(round(y1)),
#             int(round(x2)),
#             int(round(y2)),
#         )

#     # ============================================================
#     # VALIDATE BOX
#     # ============================================================

#     @staticmethod
#     def _valid_box(
#         x1,
#         y1,
#         x2,
#         y2,
#     ):
#         """
#         Check whether a converted box has a meaningful area.
#         """

#         return x2 > x1 and y2 > y1

#     # ============================================================
#     # DETECT
#     # ============================================================

#     def detect(
#         self,
#         frame,
#     ):
#         """
#         Detect PERSON, CELL_PHONE and BOOK.

#         Parameters
#         ----------
#         frame:
#             Original BGR OpenCV frame.

#         Returns
#         -------
#         list[dict]

#         Example:

#             [
#                 {
#                     "class_id": 67,
#                     "label": "CELL_PHONE",
#                     "confidence": 0.81,
#                     "x": 100,
#                     "y": 120,
#                     "x2": 180,
#                     "y2": 300,
#                 }
#             ]

#         The coordinates are always relative to the ORIGINAL
#         camera frame, not the letterboxed 640x640 image.
#         """

#         if self.closed:

#             return []

#         if frame is None:

#             return []

#         if not isinstance(
#             frame,
#             np.ndarray,
#         ):

#             return []

#         if frame.ndim != 3:

#             return []

#         if frame.shape[2] != 3:

#             return []

#         original_height, original_width = frame.shape[:2]

#         if original_width <= 0 or original_height <= 0:

#             return []

#         # ========================================================
#         # PREPROCESS
#         # ========================================================

#         (
#             blob,
#             scale,
#             pad_x,
#             pad_y,
#         ) = self._letterbox(frame)

#         # ========================================================
#         # INFERENCE
#         # ========================================================

#         outputs = self.session.run(
#             None,
#             {self.input_name: blob},
#         )

#         if not outputs:

#             return []

#         # ========================================================
#         # PREPARE MODEL OUTPUT
#         # ========================================================

#         predictions = self._prepare_output(outputs[0])

#         if predictions.size == 0:

#             return []

#         # ========================================================
#         # RAW DETECTIONS
#         # ========================================================

#         boxes = []

#         scores = []

#         class_ids = []

#         # ========================================================
#         # PARSE EVERY PREDICTION
#         # ========================================================

#         for prediction in predictions:

#             if prediction.shape[0] < 5:

#                 continue

#             # ----------------------------------------------------
#             # YOLO box
#             # ----------------------------------------------------

#             center_x = float(prediction[0])

#             center_y = float(prediction[1])

#             width = float(prediction[2])

#             height = float(prediction[3])

#             # ----------------------------------------------------
#             # Ignore invalid raw boxes.
#             # ----------------------------------------------------

#             if width <= 0 or height <= 0:

#                 continue

#             # ----------------------------------------------------
#             # Class scores.
#             # ----------------------------------------------------

#             class_scores = prediction[4:]

#             if class_scores is None or len(class_scores) == 0:

#                 continue

#             # ----------------------------------------------------
#             # Highest scoring class.
#             # ----------------------------------------------------

#             class_id = int(np.argmax(class_scores))

#             # ----------------------------------------------------
#             # We only care about monitored classes.
#             # ----------------------------------------------------

#             if class_id not in self.MONITORED_CLASSES:

#                 continue

#             # ----------------------------------------------------
#             # Confidence.
#             # ----------------------------------------------------

#             confidence = float(class_scores[class_id])

#             if not np.isfinite(confidence):

#                 continue

#             # ----------------------------------------------------
#             # Class-specific threshold.
#             #
#             # Phone/book deliberately use lower thresholds.
#             # ----------------------------------------------------

#             threshold = float(
#                 self.CLASS_THRESHOLDS.get(
#                     class_id,
#                     self.DEFAULT_THRESHOLD,
#                 )
#             )

#             if confidence < threshold:

#                 continue

#             # ----------------------------------------------------
#             # Convert coordinates back to original frame.
#             # ----------------------------------------------------

#             (
#                 x1,
#                 y1,
#                 x2,
#                 y2,
#             ) = self._convert_box(
#                 center_x,
#                 center_y,
#                 width,
#                 height,
#                 scale,
#                 pad_x,
#                 pad_y,
#                 original_width,
#                 original_height,
#             )

#             # ----------------------------------------------------
#             # Keep boxes touching frame edges.
#             #
#             # We only reject boxes with zero/negative area.
#             # ----------------------------------------------------

#             if not self._valid_box(
#                 x1,
#                 y1,
#                 x2,
#                 y2,
#             ):

#                 continue

#             boxes.append(
#                 [
#                     x1,
#                     y1,
#                     x2 - x1,
#                     y2 - y1,
#                 ]
#             )

#             scores.append(confidence)

#             class_ids.append(class_id)

#         # ========================================================
#         # NO MONITORED OBJECTS
#         # ========================================================

#         if not boxes:

#             return []

#         # ========================================================
#         # CLASS-AWARE NMS
#         #
#         # NMS is performed independently for:
#         #
#         #     PERSON
#         #     CELL_PHONE
#         #     BOOK
#         #
#         # This prevents an overlapping PERSON box from
#         # suppressing a PHONE or BOOK box.
#         # ========================================================

#         selected_indices = []

#         unique_classes = sorted(set(class_ids))

#         for current_class_id in unique_classes:

#             class_indices = [
#                 index
#                 for index, detected_class_id in enumerate(class_ids)
#                 if detected_class_id == current_class_id
#             ]

#             if not class_indices:

#                 continue

#             class_boxes = [boxes[index] for index in class_indices]

#             class_scores = [scores[index] for index in class_indices]

#             indexes = cv2.dnn.NMSBoxes(
#                 class_boxes,
#                 class_scores,
#                 score_threshold=0.0,
#                 nms_threshold=self.nms_threshold,
#             )

#             if indexes is None or len(indexes) == 0:

#                 continue

#             indexes = np.asarray(indexes).reshape(-1)

#             for local_index in indexes:

#                 local_index = int(local_index)

#                 if local_index < 0 or local_index >= len(class_indices):

#                     continue

#                 selected_indices.append(class_indices[local_index])

#         # ========================================================
#         # BUILD FINAL DETECTION LIST
#         # ========================================================

#         detections = []

#         for index in selected_indices:

#             x, y, width, height = boxes[index]

#             class_id = class_ids[index]

#             confidence = float(scores[index])

#             detections.append(
#                 {
#                     "class_id": int(class_id),
#                     "label": (self.MONITORED_CLASSES[class_id]),
#                     "confidence": confidence,
#                     "x": int(x),
#                     "y": int(y),
#                     "x2": int(x + width),
#                     "y2": int(y + height),
#                 }
#             )

#         # ========================================================
#         # SORT BY CONFIDENCE
#         # ========================================================

#         detections.sort(
#             key=lambda detection: detection["confidence"],
#             reverse=True,
#         )

#         return detections

#     # ============================================================
#     # CLOSE
#     # ============================================================

#     def close(self):
#         """
#         Release the ONNX Runtime session.
#         """

#         if self.closed:

#             return

#         self.session = None

#         self.closed = True

#         print("[OBJECT DETECTOR] " "YOLO26n closed.")

from pathlib import Path
import time

import cv2
import numpy as np
import onnxruntime as ort


class YOLO26ObjectDetector:
    MONITORED_CLASSES = {
        0: "PERSON",
        67: "CELL_PHONE",
        73: "BOOK",
    }

    CLASS_THRESHOLDS = {
        0: 0.35,
        67: 0.25,
        73: 0.25,
    }

    DEFAULT_THRESHOLD = 0.35

    DEFAULT_INPUT_WIDTH = 640
    DEFAULT_INPUT_HEIGHT = 640

    DEFAULT_NMS_THRESHOLD = 0.45

    PERSON_CLASS_ID = 0
    PHONE_CLASS_ID = 67

    PHONE_STRONG_CONFIDENCE = 0.55
    PHONE_STANDALONE_CONFIDENCE = 0.42

    PHONE_MIN_AREA_RATIO = 0.00008
    PHONE_WEAK_MIN_AREA_RATIO = 0.00025

    PHONE_PREFERRED_MAX_ASPECT_RATIO = 4.5
    PHONE_HARD_MAX_ASPECT_RATIO = 6.5

    PHONE_EDGE_MARGIN_RATIO = 0.025
    PHONE_PERSON_MARGIN_RATIO = 0.08

    PHONE_TRACK_TTL_SECONDS = 2.0
    PHONE_TRACK_MATCH_IOU = 0.30
    PHONE_TRACK_MATCH_CENTER_RATIO = 0.08
    PHONE_MOVEMENT_CONFIRM_RATIO = 0.003
    PHONE_MAX_TRACKS = 12

    def __init__(
        self,
        model_path=None,
        nms_threshold=DEFAULT_NMS_THRESHOLD,
        intra_op_num_threads=1,
        inter_op_num_threads=1,
    ):
        if model_path is None:
            project_root = Path(__file__).resolve().parents[2]

            model_path = project_root / "models" / "yolo26n.onnx"

        self.model_path = Path(model_path)

        if not self.model_path.exists():
            raise RuntimeError("YOLO26n ONNX model not found: " f"{self.model_path}")

        self.nms_threshold = float(nms_threshold)

        if not 0.0 <= self.nms_threshold <= 1.0:
            raise ValueError("nms_threshold must be between " "0.0 and 1.0.")

        session_options = ort.SessionOptions()

        session_options.graph_optimization_level = (
            ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        )

        session_options.intra_op_num_threads = int(intra_op_num_threads)

        session_options.inter_op_num_threads = int(inter_op_num_threads)

        self.session = ort.InferenceSession(
            str(self.model_path),
            sess_options=(session_options),
            providers=["CPUExecutionProvider"],
        )

        inputs = self.session.get_inputs()

        if not inputs:
            raise RuntimeError("YOLO26n ONNX model " "has no inputs.")

        self.input = inputs[0]

        self.input_name = self.input.name

        input_shape = self.input.shape

        self.input_height = self.DEFAULT_INPUT_HEIGHT

        self.input_width = self.DEFAULT_INPUT_WIDTH

        if len(input_shape) >= 4:
            if isinstance(
                input_shape[2],
                int,
            ):
                self.input_height = int(input_shape[2])

            if isinstance(
                input_shape[3],
                int,
            ):
                self.input_width = int(input_shape[3])

        outputs = self.session.get_outputs()

        self.output_names = [output.name for output in outputs]

        if not self.output_names:
            raise RuntimeError("YOLO26n ONNX model " "has no outputs.")

        self.closed = False

        self._detect_sequence = 0

        self._phone_tracks = []

        print("[OBJECT DETECTOR] " "YOLO26n loaded successfully.")

        print("[OBJECT DETECTOR] " f"Model: {self.model_path}")

        print(
            "[OBJECT DETECTOR] "
            f"Input: "
            f"{self.input_width}x"
            f"{self.input_height}"
        )

        print("[OBJECT DETECTOR] " f"Output(s): " f"{self.output_names}")

        print("[OBJECT DETECTOR] " f"Providers: " f"{self.session.get_providers()}")

        print("[OBJECT DETECTOR] " "Monitored classes: " "PERSON, CELL_PHONE, BOOK")

    def _letterbox(
        self,
        frame,
    ):
        (
            frame_height,
            frame_width,
        ) = frame.shape[:2]

        if frame_height <= 0 or frame_width <= 0:
            raise ValueError("Invalid frame dimensions.")

        scale = min(
            self.input_width / float(frame_width),
            self.input_height / float(frame_height),
        )

        resized_width = max(
            1,
            int(round(frame_width * scale)),
        )

        resized_height = max(
            1,
            int(round(frame_height * scale)),
        )

        resized = cv2.resize(
            frame,
            (
                resized_width,
                resized_height,
            ),
            interpolation=(cv2.INTER_LINEAR),
        )

        canvas = np.full(
            (
                self.input_height,
                self.input_width,
                3,
            ),
            114,
            dtype=np.uint8,
        )

        pad_x = (self.input_width - resized_width) // 2

        pad_y = (self.input_height - resized_height) // 2

        canvas[
            pad_y : pad_y + resized_height,
            pad_x : pad_x + resized_width,
        ] = resized

        rgb = cv2.cvtColor(
            canvas,
            cv2.COLOR_BGR2RGB,
        )

        blob = rgb.astype(np.float32) / 255.0

        blob = np.transpose(
            blob,
            (
                2,
                0,
                1,
            ),
        )

        blob = np.expand_dims(
            blob,
            axis=0,
        )

        blob = np.ascontiguousarray(
            blob,
            dtype=np.float32,
        )

        return (
            blob,
            scale,
            pad_x,
            pad_y,
        )

    def _prepare_output(
        self,
        output,
    ):
        if output is None:
            return np.empty(
                (
                    0,
                    84,
                ),
                dtype=np.float32,
            )

        predictions = np.asarray(output)

        predictions = np.squeeze(predictions)

        if predictions.ndim != 2:
            return np.empty(
                (
                    0,
                    84,
                ),
                dtype=np.float32,
            )

        if predictions.shape[0] < predictions.shape[1]:
            predictions = predictions.T

        return predictions.astype(
            np.float32,
            copy=False,
        )

    def _convert_box(
        self,
        center_x,
        center_y,
        width,
        height,
        scale,
        pad_x,
        pad_y,
        original_width,
        original_height,
    ):
        x1 = center_x - width / 2.0 - pad_x

        y1 = center_y - height / 2.0 - pad_y

        x2 = center_x + width / 2.0 - pad_x

        y2 = center_y + height / 2.0 - pad_y

        x1 /= scale
        y1 /= scale
        x2 /= scale
        y2 /= scale

        x1 = max(
            0.0,
            min(
                float(original_width - 1),
                x1,
            ),
        )

        y1 = max(
            0.0,
            min(
                float(original_height - 1),
                y1,
            ),
        )

        x2 = max(
            0.0,
            min(
                float(original_width - 1),
                x2,
            ),
        )

        y2 = max(
            0.0,
            min(
                float(original_height - 1),
                y2,
            ),
        )

        return (
            int(round(x1)),
            int(round(y1)),
            int(round(x2)),
            int(round(y2)),
        )

    @staticmethod
    def _valid_box(
        x1,
        y1,
        x2,
        y2,
    ):
        return x2 > x1 and y2 > y1

    @staticmethod
    def _box_iou(
        box_a,
        box_b,
    ):
        (
            ax1,
            ay1,
            ax2,
            ay2,
        ) = box_a

        (
            bx1,
            by1,
            bx2,
            by2,
        ) = box_b

        intersection_x1 = max(
            ax1,
            bx1,
        )

        intersection_y1 = max(
            ay1,
            by1,
        )

        intersection_x2 = min(
            ax2,
            bx2,
        )

        intersection_y2 = min(
            ay2,
            by2,
        )

        intersection_width = max(
            0.0,
            intersection_x2 - intersection_x1,
        )

        intersection_height = max(
            0.0,
            intersection_y2 - intersection_y1,
        )

        intersection_area = intersection_width * intersection_height

        if intersection_area <= 0.0:
            return 0.0

        area_a = max(
            0.0,
            ax2 - ax1,
        ) * max(
            0.0,
            ay2 - ay1,
        )

        area_b = max(
            0.0,
            bx2 - bx1,
        ) * max(
            0.0,
            by2 - by1,
        )

        union_area = area_a + area_b - intersection_area

        if union_area <= 0.0:
            return 0.0

        return float(intersection_area / union_area)

    @staticmethod
    def _box_center(
        box,
    ):
        (
            x1,
            y1,
            x2,
            y2,
        ) = box

        return (
            (float(x1) + float(x2)) / 2.0,
            (float(y1) + float(y2)) / 2.0,
        )

    @staticmethod
    def _phone_box_metrics(
        detection,
        frame_width,
        frame_height,
    ):
        x1 = float(
            detection.get(
                "x",
                0,
            )
        )

        y1 = float(
            detection.get(
                "y",
                0,
            )
        )

        x2 = float(
            detection.get(
                "x2",
                0,
            )
        )

        y2 = float(
            detection.get(
                "y2",
                0,
            )
        )

        width = max(
            0.0,
            x2 - x1,
        )

        height = max(
            0.0,
            y2 - y1,
        )

        frame_area = max(
            1.0,
            float(frame_width) * float(frame_height),
        )

        area_ratio = (width * height) / frame_area

        short_side = min(
            width,
            height,
        )

        long_side = max(
            width,
            height,
        )

        if short_side <= 0.0:
            aspect_ratio = float("inf")
        else:
            aspect_ratio = long_side / short_side

        return {
            "area_ratio": float(area_ratio),
            "aspect_ratio": float(aspect_ratio),
        }

    def _phone_touches_frame_edge(
        self,
        detection,
        frame_width,
        frame_height,
    ):
        margin_x = max(
            2.0,
            frame_width * self.PHONE_EDGE_MARGIN_RATIO,
        )

        margin_y = max(
            2.0,
            frame_height * self.PHONE_EDGE_MARGIN_RATIO,
        )

        x1 = float(
            detection.get(
                "x",
                0,
            )
        )

        y1 = float(
            detection.get(
                "y",
                0,
            )
        )

        x2 = float(
            detection.get(
                "x2",
                0,
            )
        )

        y2 = float(
            detection.get(
                "y2",
                0,
            )
        )

        return (
            x1 <= margin_x
            or y1 <= margin_y
            or x2 >= (frame_width - 1 - margin_x)
            or y2 >= (frame_height - 1 - margin_y)
        )

    def _phone_near_person(
        self,
        phone_detection,
        person_detections,
        frame_width,
        frame_height,
    ):
        if not person_detections:
            return False

        phone_box = (
            float(
                phone_detection.get(
                    "x",
                    0,
                )
            ),
            float(
                phone_detection.get(
                    "y",
                    0,
                )
            ),
            float(
                phone_detection.get(
                    "x2",
                    0,
                )
            ),
            float(
                phone_detection.get(
                    "y2",
                    0,
                )
            ),
        )

        (
            phone_center_x,
            phone_center_y,
        ) = self._box_center(phone_box)

        frame_margin_x = frame_width * self.PHONE_PERSON_MARGIN_RATIO

        frame_margin_y = frame_height * self.PHONE_PERSON_MARGIN_RATIO

        for person in person_detections:
            px1 = float(
                person.get(
                    "x",
                    0,
                )
            )

            py1 = float(
                person.get(
                    "y",
                    0,
                )
            )

            px2 = float(
                person.get(
                    "x2",
                    0,
                )
            )

            py2 = float(
                person.get(
                    "y2",
                    0,
                )
            )

            person_width = max(
                0.0,
                px2 - px1,
            )

            person_height = max(
                0.0,
                py2 - py1,
            )

            margin_x = max(
                frame_margin_x,
                person_width * 0.15,
            )

            margin_y = max(
                frame_margin_y,
                person_height * 0.12,
            )

            if (px1 - margin_x) <= phone_center_x <= (px2 + margin_x) and (
                py1 - margin_y
            ) <= phone_center_y <= (py2 + margin_y):
                return True

        return False

    def _prune_phone_tracks(
        self,
        now,
    ):
        self._phone_tracks = [
            track
            for track in self._phone_tracks
            if (
                now
                - float(
                    track.get(
                        "last_seen",
                        now,
                    )
                )
            )
            <= self.PHONE_TRACK_TTL_SECONDS
        ]

        if len(self._phone_tracks) > self.PHONE_MAX_TRACKS:
            self._phone_tracks.sort(
                key=lambda track: float(
                    track.get(
                        "last_seen",
                        0.0,
                    )
                ),
                reverse=True,
            )

            self._phone_tracks = self._phone_tracks[: self.PHONE_MAX_TRACKS]

    def _update_phone_track(
        self,
        detection,
        frame_width,
        frame_height,
        now,
    ):
        self._prune_phone_tracks(now)

        current_box = (
            float(
                detection.get(
                    "x",
                    0,
                )
            ),
            float(
                detection.get(
                    "y",
                    0,
                )
            ),
            float(
                detection.get(
                    "x2",
                    0,
                )
            ),
            float(
                detection.get(
                    "y2",
                    0,
                )
            ),
        )

        current_center = self._box_center(current_box)

        frame_diagonal = max(
            1.0,
            float(
                np.hypot(
                    frame_width,
                    frame_height,
                )
            ),
        )

        best_track = None
        best_score = -1.0

        for track in self._phone_tracks:
            if track.get("last_sequence") == self._detect_sequence:
                continue

            previous_box = track.get("box")

            if previous_box is None:
                continue

            iou = self._box_iou(
                current_box,
                previous_box,
            )

            previous_center = self._box_center(previous_box)

            center_distance_ratio = float(
                np.hypot(
                    current_center[0] - previous_center[0],
                    current_center[1] - previous_center[1],
                )
                / frame_diagonal
            )

            if (
                iou < self.PHONE_TRACK_MATCH_IOU
                and center_distance_ratio > self.PHONE_TRACK_MATCH_CENTER_RATIO
            ):
                continue

            score = iou - (center_distance_ratio * 0.25)

            if score > best_score:
                best_score = score
                best_track = track

        confidence = float(
            detection.get(
                "confidence",
                0.0,
            )
            or 0.0
        )

        if best_track is None:
            track = {
                "box": current_box,
                "first_seen": now,
                "last_seen": now,
                "hits": 1,
                "max_confidence": confidence,
                "last_confidence": confidence,
                "last_movement_ratio": 0.0,
                "last_sequence": self._detect_sequence,
            }

            self._phone_tracks.append(track)

            return track

        previous_box = best_track.get(
            "box",
            current_box,
        )

        previous_center = self._box_center(previous_box)

        movement_ratio = float(
            np.hypot(
                current_center[0] - previous_center[0],
                current_center[1] - previous_center[1],
            )
            / frame_diagonal
        )

        best_track["box"] = current_box

        best_track["last_seen"] = now

        best_track["hits"] = (
            int(
                best_track.get(
                    "hits",
                    0,
                )
            )
            + 1
        )

        best_track["max_confidence"] = max(
            float(
                best_track.get(
                    "max_confidence",
                    0.0,
                )
            ),
            confidence,
        )

        best_track["last_confidence"] = confidence

        best_track["last_movement_ratio"] = movement_ratio

        best_track["last_sequence"] = self._detect_sequence

        return best_track

    def _phone_candidate_is_acceptable(
        self,
        detection,
        person_detections,
        frame_width,
        frame_height,
        track,
    ):
        confidence = float(
            detection.get(
                "confidence",
                0.0,
            )
            or 0.0
        )

        metrics = self._phone_box_metrics(
            detection,
            frame_width,
            frame_height,
        )

        area_ratio = metrics["area_ratio"]

        aspect_ratio = metrics["aspect_ratio"]

        edge_partial = self._phone_touches_frame_edge(
            detection,
            frame_width,
            frame_height,
        )

        near_person = self._phone_near_person(
            detection,
            person_detections,
            frame_width,
            frame_height,
        )

        if area_ratio < self.PHONE_MIN_AREA_RATIO:
            if not (edge_partial and confidence >= self.PHONE_STANDALONE_CONFIDENCE):
                return False

        if (
            aspect_ratio > self.PHONE_HARD_MAX_ASPECT_RATIO
            and not edge_partial
            and confidence < self.PHONE_STRONG_CONFIDENCE
        ):
            return False

        if edge_partial:
            return True

        if near_person:
            return True

        if confidence >= self.PHONE_STRONG_CONFIDENCE:
            return True

        preferred_geometry = aspect_ratio <= self.PHONE_PREFERRED_MAX_ASPECT_RATIO

        meaningful_size = area_ratio >= self.PHONE_WEAK_MIN_AREA_RATIO

        if (
            confidence >= self.PHONE_STANDALONE_CONFIDENCE
            and preferred_geometry
            and meaningful_size
        ):
            return True

        hits = int(
            track.get(
                "hits",
                0,
            )
        )

        last_movement_ratio = float(
            track.get(
                "last_movement_ratio",
                0.0,
            )
        )

        if (
            hits >= 2
            and last_movement_ratio >= self.PHONE_MOVEMENT_CONFIRM_RATIO
            and preferred_geometry
            and meaningful_size
        ):
            return True

        return False

    def _filter_phone_detections(
        self,
        detections,
        frame_width,
        frame_height,
    ):
        if not detections:
            return detections

        person_detections = [
            detection
            for detection in detections
            if (
                int(
                    detection.get(
                        "class_id",
                        -1,
                    )
                )
                == self.PERSON_CLASS_ID
            )
        ]

        now = time.monotonic()

        filtered = []

        for detection in detections:
            class_id = int(
                detection.get(
                    "class_id",
                    -1,
                )
            )

            if class_id != self.PHONE_CLASS_ID:
                filtered.append(detection)

                continue

            track = self._update_phone_track(
                detection,
                frame_width,
                frame_height,
                now,
            )

            if self._phone_candidate_is_acceptable(
                detection,
                person_detections,
                frame_width,
                frame_height,
                track,
            ):
                filtered.append(detection)

        return filtered

    def detect(
        self,
        frame,
    ):
        if self.closed:
            return []

        if frame is None:
            return []

        if not isinstance(
            frame,
            np.ndarray,
        ):
            return []

        if frame.ndim != 3:
            return []

        if frame.shape[2] != 3:
            return []

        (
            original_height,
            original_width,
        ) = frame.shape[:2]

        if original_width <= 0 or original_height <= 0:
            return []

        self._detect_sequence += 1

        self._prune_phone_tracks(time.monotonic())

        (
            blob,
            scale,
            pad_x,
            pad_y,
        ) = self._letterbox(frame)

        outputs = self.session.run(
            None,
            {
                self.input_name: blob,
            },
        )

        if not outputs:
            return []

        predictions = self._prepare_output(outputs[0])

        if predictions.size == 0:
            return []

        boxes = []
        scores = []
        class_ids = []

        for prediction in predictions:
            if prediction.shape[0] < 5:
                continue

            center_x = float(prediction[0])

            center_y = float(prediction[1])

            width = float(prediction[2])

            height = float(prediction[3])

            if width <= 0 or height <= 0:
                continue

            class_scores = prediction[4:]

            if class_scores is None or len(class_scores) == 0:
                continue

            class_id = int(np.argmax(class_scores))

            if class_id not in self.MONITORED_CLASSES:
                continue

            confidence = float(class_scores[class_id])

            if not np.isfinite(confidence):
                continue

            threshold = float(
                self.CLASS_THRESHOLDS.get(
                    class_id,
                    self.DEFAULT_THRESHOLD,
                )
            )

            if confidence < threshold:
                continue

            (
                x1,
                y1,
                x2,
                y2,
            ) = self._convert_box(
                center_x,
                center_y,
                width,
                height,
                scale,
                pad_x,
                pad_y,
                original_width,
                original_height,
            )

            if not self._valid_box(
                x1,
                y1,
                x2,
                y2,
            ):
                continue

            boxes.append(
                [
                    x1,
                    y1,
                    x2 - x1,
                    y2 - y1,
                ]
            )

            scores.append(confidence)

            class_ids.append(class_id)

        if not boxes:
            return []

        selected_indices = []

        unique_classes = sorted(set(class_ids))

        for current_class_id in unique_classes:
            class_indices = [
                index
                for (
                    index,
                    detected_class_id,
                ) in enumerate(class_ids)
                if (detected_class_id == current_class_id)
            ]

            if not class_indices:
                continue

            class_boxes = [boxes[index] for index in class_indices]

            class_scores = [scores[index] for index in class_indices]

            indexes = cv2.dnn.NMSBoxes(
                class_boxes,
                class_scores,
                score_threshold=0.0,
                nms_threshold=(self.nms_threshold),
            )

            if indexes is None or len(indexes) == 0:
                continue

            indexes = np.asarray(indexes).reshape(-1)

            for local_index in indexes:
                local_index = int(local_index)

                if local_index < 0 or local_index >= len(class_indices):
                    continue

                selected_indices.append(class_indices[local_index])

        detections = []

        for index in selected_indices:
            (
                x,
                y,
                width,
                height,
            ) = boxes[index]

            class_id = class_ids[index]

            confidence = float(scores[index])

            detections.append(
                {
                    "class_id": int(class_id),
                    "label": self.MONITORED_CLASSES[class_id],
                    "confidence": confidence,
                    "x": int(x),
                    "y": int(y),
                    "x2": int(x + width),
                    "y2": int(y + height),
                }
            )

        detections.sort(
            key=lambda detection: detection["confidence"],
            reverse=True,
        )

        detections = self._filter_phone_detections(
            detections,
            original_width,
            original_height,
        )

        return detections

    def close(
        self,
    ):
        if self.closed:
            return

        self.session = None

        self._phone_tracks.clear()

        self.closed = True

        print("[OBJECT DETECTOR] " "YOLO26n closed.")
