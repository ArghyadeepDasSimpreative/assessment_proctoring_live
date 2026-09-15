"""
Skolariq - YOLO26n Object Detector
==================================

Production-ready YOLO26n ONNX detector.

Responsibilities:
    - Detect PERSON
    - Detect CELL_PHONE
    - Detect BOOK
    - Preserve detections for partially visible objects
    - Preserve detections touching the camera frame edges
    - Perform class-aware NMS
    - Return coordinates in ORIGINAL camera-frame space

Runtime:
    - ONNX Runtime
    - CPUExecutionProvider

Model:
    models/yolo26n.onnx

Public interface:

    detector = YOLO26ObjectDetector()

    detections = detector.detect(frame)

    detector.close()


Detection format:

    {
        "class_id": 67,
        "label": "CELL_PHONE",
        "confidence": 0.81,
        "x": 100,
        "y": 120,
        "x2": 180,
        "y2": 300,
    }

IMPORTANT
---------
This detector does NOT contain separate rules such as:

    "if half a phone is visible, call it a phone"

That decision is made by the YOLO26n model itself.

This class is responsible for making sure valid model detections
are not unnecessarily lost because of preprocessing, confidence
thresholding, coordinate conversion, or NMS.
"""

from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort


class YOLO26ObjectDetector:

    # ============================================================
    # COCO CLASSES
    # ============================================================

    MONITORED_CLASSES = {
        0: "PERSON",
        67: "CELL_PHONE",
        73: "BOOK",
    }

    # ============================================================
    # CONFIDENCE THRESHOLDS
    #
    # Phone and book are intentionally lower than PERSON.
    #
    # This is important for our proctoring use case because
    # partially visible objects often have lower confidence.
    #
    # These are evaluation/initial-production values and can
    # later be tuned using real camera evidence.
    # ============================================================

    CLASS_THRESHOLDS = {
        0: 0.35,
        67: 0.25,
        73: 0.25,
    }

    DEFAULT_THRESHOLD = 0.35

    # ============================================================
    # MODEL INPUT
    # ============================================================

    DEFAULT_INPUT_WIDTH = 640
    DEFAULT_INPUT_HEIGHT = 640

    # ============================================================
    # NMS
    # ============================================================

    DEFAULT_NMS_THRESHOLD = 0.45

    # ============================================================
    # CONSTRUCTOR
    # ============================================================

    def __init__(
        self,
        model_path=None,
        nms_threshold=DEFAULT_NMS_THRESHOLD,
        intra_op_num_threads=1,
        inter_op_num_threads=1,
    ):
        """
        Initialize YOLO26n ONNX detector.

        Parameters
        ----------
        model_path:
            Optional custom ONNX model.

            Default:

                <project-root>/models/yolo26n.onnx

        nms_threshold:
            IoU threshold for class-aware NMS.

        intra_op_num_threads:
            ONNX Runtime CPU thread count.

        inter_op_num_threads:
            ONNX Runtime CPU thread count.
        """

        # ========================================================
        # MODEL PATH
        # ========================================================

        if model_path is None:

            project_root = Path(__file__).resolve().parents[2]

            model_path = project_root / "models" / "yolo26n.onnx"

        self.model_path = Path(model_path)

        if not self.model_path.exists():

            raise RuntimeError("YOLO26n ONNX model not found: " f"{self.model_path}")

        # ========================================================
        # NMS CONFIGURATION
        # ========================================================

        self.nms_threshold = float(nms_threshold)

        if not 0.0 <= self.nms_threshold <= 1.0:

            raise ValueError("nms_threshold must be between " "0.0 and 1.0.")

        # ========================================================
        # ONNX SESSION OPTIONS
        # ========================================================

        session_options = ort.SessionOptions()

        session_options.graph_optimization_level = (
            ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        )

        session_options.intra_op_num_threads = int(intra_op_num_threads)

        session_options.inter_op_num_threads = int(inter_op_num_threads)

        # ========================================================
        # LOAD ONNX MODEL
        # ========================================================

        self.session = ort.InferenceSession(
            str(self.model_path),
            sess_options=session_options,
            providers=["CPUExecutionProvider"],
        )

        # ========================================================
        # INPUT
        # ========================================================

        inputs = self.session.get_inputs()

        if not inputs:

            raise RuntimeError("YOLO26n ONNX model has no inputs.")

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

        # ========================================================
        # OUTPUTS
        # ========================================================

        outputs = self.session.get_outputs()

        self.output_names = [output.name for output in outputs]

        if not self.output_names:

            raise RuntimeError("YOLO26n ONNX model has no outputs.")

        # ========================================================
        # STATE
        # ========================================================

        self.closed = False

        # ========================================================
        # STARTUP LOGGING
        # ========================================================

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

    # ============================================================
    # LETTERBOX
    # ============================================================

    def _letterbox(
        self,
        frame,
    ):
        """
        Resize frame while preserving aspect ratio.

        The resized image is centered on a 640x640 canvas.

        Returns
        -------
        blob:
            NCHW float32 tensor.

        scale:
            Resize scale used.

        pad_x:
            Horizontal padding.

        pad_y:
            Vertical padding.
        """

        frame_height, frame_width = frame.shape[:2]

        if frame_height <= 0 or frame_width <= 0:

            raise ValueError("Invalid frame dimensions.")

        # --------------------------------------------------------
        # Calculate scale.
        # --------------------------------------------------------

        scale = min(
            self.input_width / float(frame_width),
            self.input_height / float(frame_height),
        )

        # --------------------------------------------------------
        # Calculate resized dimensions.
        # --------------------------------------------------------

        resized_width = max(
            1,
            int(round(frame_width * scale)),
        )

        resized_height = max(
            1,
            int(round(frame_height * scale)),
        )

        # --------------------------------------------------------
        # Resize.
        # --------------------------------------------------------

        resized = cv2.resize(
            frame,
            (
                resized_width,
                resized_height,
            ),
            interpolation=cv2.INTER_LINEAR,
        )

        # --------------------------------------------------------
        # Create letterbox canvas.
        # --------------------------------------------------------

        canvas = np.full(
            (
                self.input_height,
                self.input_width,
                3,
            ),
            114,
            dtype=np.uint8,
        )

        # --------------------------------------------------------
        # Center resized image.
        # --------------------------------------------------------

        pad_x = (self.input_width - resized_width) // 2

        pad_y = (self.input_height - resized_height) // 2

        canvas[
            pad_y : pad_y + resized_height,
            pad_x : pad_x + resized_width,
        ] = resized

        # --------------------------------------------------------
        # BGR -> RGB.
        # --------------------------------------------------------

        rgb = cv2.cvtColor(
            canvas,
            cv2.COLOR_BGR2RGB,
        )

        # --------------------------------------------------------
        # Normalize.
        # --------------------------------------------------------

        blob = rgb.astype(np.float32) / 255.0

        # --------------------------------------------------------
        # HWC -> CHW.
        # --------------------------------------------------------

        blob = np.transpose(
            blob,
            (
                2,
                0,
                1,
            ),
        )

        # --------------------------------------------------------
        # Add batch dimension.
        # --------------------------------------------------------

        blob = np.expand_dims(
            blob,
            axis=0,
        )

        # --------------------------------------------------------
        # Ensure contiguous float32 memory.
        # --------------------------------------------------------

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

    # ============================================================
    # OUTPUT PREPARATION
    # ============================================================

    def _prepare_output(
        self,
        output,
    ):
        """
        Normalize YOLO26n output layout.

        Current exported model:

            (1, 84, 8400)

        After squeeze:

            (84, 8400)

        Final expected format:

            (8400, 84)
        """

        if output is None:

            return np.empty(
                (
                    0,
                    84,
                ),
                dtype=np.float32,
            )

        predictions = np.asarray(output)

        # --------------------------------------------------------
        # Remove batch dimension(s).
        # --------------------------------------------------------

        predictions = np.squeeze(predictions)

        if predictions.ndim != 2:

            return np.empty(
                (
                    0,
                    84,
                ),
                dtype=np.float32,
            )

        # --------------------------------------------------------
        # YOLO output is normally:
        #
        #     84 x 8400
        #
        # Convert to:
        #
        #     8400 x 84
        #
        # --------------------------------------------------------

        if predictions.shape[0] < predictions.shape[1]:

            predictions = predictions.T

        return predictions.astype(
            np.float32,
            copy=False,
        )

    # ============================================================
    # BOX CONVERSION
    # ============================================================

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
        """
        Convert YOLO coordinates from the letterboxed
        image into ORIGINAL FRAME coordinates.

        Coordinates are clipped to the camera frame.

        This is particularly important for objects touching
        the left/right/top/bottom edge of the camera frame.
        """

        # --------------------------------------------------------
        # Remove padding.
        # --------------------------------------------------------

        x1 = center_x - width / 2.0 - pad_x

        y1 = center_y - height / 2.0 - pad_y

        x2 = center_x + width / 2.0 - pad_x

        y2 = center_y + height / 2.0 - pad_y

        # --------------------------------------------------------
        # Undo resize.
        # --------------------------------------------------------

        x1 /= scale
        y1 /= scale
        x2 /= scale
        y2 /= scale

        # --------------------------------------------------------
        # Clip coordinates.
        #
        # We intentionally clip instead of discarding boxes
        # that extend beyond the frame.
        #
        # This allows edge-of-frame objects to survive.
        # --------------------------------------------------------

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

    # ============================================================
    # VALIDATE BOX
    # ============================================================

    @staticmethod
    def _valid_box(
        x1,
        y1,
        x2,
        y2,
    ):
        """
        Check whether a converted box has a meaningful area.
        """

        return x2 > x1 and y2 > y1

    # ============================================================
    # DETECT
    # ============================================================

    def detect(
        self,
        frame,
    ):
        """
        Detect PERSON, CELL_PHONE and BOOK.

        Parameters
        ----------
        frame:
            Original BGR OpenCV frame.

        Returns
        -------
        list[dict]

        Example:

            [
                {
                    "class_id": 67,
                    "label": "CELL_PHONE",
                    "confidence": 0.81,
                    "x": 100,
                    "y": 120,
                    "x2": 180,
                    "y2": 300,
                }
            ]

        The coordinates are always relative to the ORIGINAL
        camera frame, not the letterboxed 640x640 image.
        """

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

        original_height, original_width = frame.shape[:2]

        if original_width <= 0 or original_height <= 0:

            return []

        # ========================================================
        # PREPROCESS
        # ========================================================

        (
            blob,
            scale,
            pad_x,
            pad_y,
        ) = self._letterbox(frame)

        # ========================================================
        # INFERENCE
        # ========================================================

        outputs = self.session.run(
            None,
            {self.input_name: blob},
        )

        if not outputs:

            return []

        # ========================================================
        # PREPARE MODEL OUTPUT
        # ========================================================

        predictions = self._prepare_output(outputs[0])

        if predictions.size == 0:

            return []

        # ========================================================
        # RAW DETECTIONS
        # ========================================================

        boxes = []

        scores = []

        class_ids = []

        # ========================================================
        # PARSE EVERY PREDICTION
        # ========================================================

        for prediction in predictions:

            if prediction.shape[0] < 5:

                continue

            # ----------------------------------------------------
            # YOLO box
            # ----------------------------------------------------

            center_x = float(prediction[0])

            center_y = float(prediction[1])

            width = float(prediction[2])

            height = float(prediction[3])

            # ----------------------------------------------------
            # Ignore invalid raw boxes.
            # ----------------------------------------------------

            if width <= 0 or height <= 0:

                continue

            # ----------------------------------------------------
            # Class scores.
            # ----------------------------------------------------

            class_scores = prediction[4:]

            if class_scores is None or len(class_scores) == 0:

                continue

            # ----------------------------------------------------
            # Highest scoring class.
            # ----------------------------------------------------

            class_id = int(np.argmax(class_scores))

            # ----------------------------------------------------
            # We only care about monitored classes.
            # ----------------------------------------------------

            if class_id not in self.MONITORED_CLASSES:

                continue

            # ----------------------------------------------------
            # Confidence.
            # ----------------------------------------------------

            confidence = float(class_scores[class_id])

            if not np.isfinite(confidence):

                continue

            # ----------------------------------------------------
            # Class-specific threshold.
            #
            # Phone/book deliberately use lower thresholds.
            # ----------------------------------------------------

            threshold = float(
                self.CLASS_THRESHOLDS.get(
                    class_id,
                    self.DEFAULT_THRESHOLD,
                )
            )

            if confidence < threshold:

                continue

            # ----------------------------------------------------
            # Convert coordinates back to original frame.
            # ----------------------------------------------------

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

            # ----------------------------------------------------
            # Keep boxes touching frame edges.
            #
            # We only reject boxes with zero/negative area.
            # ----------------------------------------------------

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

        # ========================================================
        # NO MONITORED OBJECTS
        # ========================================================

        if not boxes:

            return []

        # ========================================================
        # CLASS-AWARE NMS
        #
        # NMS is performed independently for:
        #
        #     PERSON
        #     CELL_PHONE
        #     BOOK
        #
        # This prevents an overlapping PERSON box from
        # suppressing a PHONE or BOOK box.
        # ========================================================

        selected_indices = []

        unique_classes = sorted(set(class_ids))

        for current_class_id in unique_classes:

            class_indices = [
                index
                for index, detected_class_id in enumerate(class_ids)
                if detected_class_id == current_class_id
            ]

            if not class_indices:

                continue

            class_boxes = [boxes[index] for index in class_indices]

            class_scores = [scores[index] for index in class_indices]

            indexes = cv2.dnn.NMSBoxes(
                class_boxes,
                class_scores,
                score_threshold=0.0,
                nms_threshold=self.nms_threshold,
            )

            if indexes is None or len(indexes) == 0:

                continue

            indexes = np.asarray(indexes).reshape(-1)

            for local_index in indexes:

                local_index = int(local_index)

                if local_index < 0 or local_index >= len(class_indices):

                    continue

                selected_indices.append(class_indices[local_index])

        # ========================================================
        # BUILD FINAL DETECTION LIST
        # ========================================================

        detections = []

        for index in selected_indices:

            x, y, width, height = boxes[index]

            class_id = class_ids[index]

            confidence = float(scores[index])

            detections.append(
                {
                    "class_id": int(class_id),
                    "label": (self.MONITORED_CLASSES[class_id]),
                    "confidence": confidence,
                    "x": int(x),
                    "y": int(y),
                    "x2": int(x + width),
                    "y2": int(y + height),
                }
            )

        # ========================================================
        # SORT BY CONFIDENCE
        # ========================================================

        detections.sort(
            key=lambda detection: detection["confidence"],
            reverse=True,
        )

        return detections

    # ============================================================
    # CLOSE
    # ============================================================

    def close(self):
        """
        Release the ONNX Runtime session.
        """

        if self.closed:

            return

        self.session = None

        self.closed = True

        print("[OBJECT DETECTOR] " "YOLO26n closed.")
