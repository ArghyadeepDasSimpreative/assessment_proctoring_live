from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort


class MobileNetPhoneVerifier:
    CELL_PHONE_CLASS_ID = 487

    IMAGE_SIZE = 224
    RESIZE_SIZE = 256

    # For this first test:
    # if ImageNet "cellular telephone" is within top 5,
    # consider the second stage passed.
    PHONE_MAX_RANK = 5

    IMAGENET_MEAN = np.array(
        [0.485, 0.456, 0.406],
        dtype=np.float32,
    ).reshape(1, 1, 3)

    IMAGENET_STD = np.array(
        [0.229, 0.224, 0.225],
        dtype=np.float32,
    ).reshape(1, 1, 3)

    def __init__(
        self,
        model_path=None,
        intra_op_num_threads=1,
        inter_op_num_threads=1,
    ):
        if model_path is None:
            project_root = Path(__file__).resolve().parents[3]

            model_path = project_root / "models" / "mobilenet_v3_small.onnx"

        self.model_path = Path(model_path)

        if not self.model_path.exists():
            raise RuntimeError(f"MobileNet model not found: {self.model_path}")

        session_options = ort.SessionOptions()

        session_options.graph_optimization_level = (
            ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        )

        session_options.intra_op_num_threads = int(intra_op_num_threads)

        session_options.inter_op_num_threads = int(inter_op_num_threads)

        self.session = ort.InferenceSession(
            str(self.model_path),
            sess_options=session_options,
            providers=["CPUExecutionProvider"],
        )

        inputs = self.session.get_inputs()

        if not inputs:
            raise RuntimeError("MobileNet model has no input.")

        outputs = self.session.get_outputs()

        if not outputs:
            raise RuntimeError("MobileNet model has no output.")

        self.input_name = inputs[0].name
        self.output_name = outputs[0].name

        self.closed = False

        print("[PHONE VERIFIER] " "MobileNetV3-Small loaded successfully.")

    def _normalize(self, image):
        rgb = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2RGB,
        )

        rgb = rgb.astype(np.float32) / 255.0

        rgb = (rgb - self.IMAGENET_MEAN) / self.IMAGENET_STD

        blob = np.transpose(
            rgb,
            (2, 0, 1),
        )

        blob = np.expand_dims(
            blob,
            axis=0,
        )

        return np.ascontiguousarray(
            blob,
            dtype=np.float32,
        )

    def _prepare_standard(self, crop):
        height, width = crop.shape[:2]

        if height <= 0 or width <= 0:
            return None

        if height < width:
            new_height = self.RESIZE_SIZE

            new_width = int(round(width * self.RESIZE_SIZE / float(height)))

        else:
            new_width = self.RESIZE_SIZE

            new_height = int(round(height * self.RESIZE_SIZE / float(width)))

        resized = cv2.resize(
            crop,
            (
                new_width,
                new_height,
            ),
            interpolation=cv2.INTER_LINEAR,
        )

        resized_height, resized_width = resized.shape[:2]

        x1 = max(
            0,
            (resized_width - self.IMAGE_SIZE) // 2,
        )

        y1 = max(
            0,
            (resized_height - self.IMAGE_SIZE) // 2,
        )

        image = resized[
            y1 : y1 + self.IMAGE_SIZE,
            x1 : x1 + self.IMAGE_SIZE,
        ]

        if image.shape[0] != self.IMAGE_SIZE or image.shape[1] != self.IMAGE_SIZE:
            image = cv2.resize(
                image,
                (
                    self.IMAGE_SIZE,
                    self.IMAGE_SIZE,
                ),
                interpolation=cv2.INTER_LINEAR,
            )

        return self._normalize(image)

    def _prepare_full_object(self, crop):
        """
        Keeps the ENTIRE visible phone crop.

        This is important for:
        - partial phones
        - phones near frame edges
        - unusual aspect ratios

        Instead of center-cropping parts away,
        we place the whole crop inside a square.
        """

        height, width = crop.shape[:2]

        if height <= 0 or width <= 0:
            return None

        square_size = max(
            height,
            width,
        )

        canvas = np.full(
            (
                square_size,
                square_size,
                3,
            ),
            114,
            dtype=np.uint8,
        )

        offset_x = (square_size - width) // 2

        offset_y = (square_size - height) // 2

        canvas[
            offset_y : offset_y + height,
            offset_x : offset_x + width,
        ] = crop

        image = cv2.resize(
            canvas,
            (
                self.IMAGE_SIZE,
                self.IMAGE_SIZE,
            ),
            interpolation=cv2.INTER_LINEAR,
        )

        return self._normalize(image)

    @staticmethod
    def _softmax(logits):
        logits = np.asarray(
            logits,
            dtype=np.float32,
        ).reshape(-1)

        logits = logits - np.max(logits)

        exp_values = np.exp(logits)

        denominator = np.sum(exp_values)

        if denominator <= 0.0:
            return np.zeros_like(
                logits,
                dtype=np.float32,
            )

        return exp_values / denominator

    def _run_blob(self, blob):
        output = self.session.run(
            [self.output_name],
            {
                self.input_name: blob,
            },
        )[0]

        probabilities = self._softmax(output)

        if self.CELL_PHONE_CLASS_ID >= len(probabilities):
            raise RuntimeError("Unexpected MobileNet output shape.")

        phone_probability = float(probabilities[self.CELL_PHONE_CLASS_ID])

        phone_rank = int(1 + np.sum(probabilities > phone_probability))

        top1_class_id = int(np.argmax(probabilities))

        top1_probability = float(probabilities[top1_class_id])

        return {
            "phone_probability": (phone_probability),
            "phone_rank": (phone_rank),
            "top1_class_id": (top1_class_id),
            "top1_probability": (top1_probability),
        }

    def classify_crop(self, crop):
        if self.closed:
            raise RuntimeError("Phone verifier is closed.")

        if crop is None:
            return {
                "is_phone": False,
                "phone_probability": 0.0,
                "phone_rank": 1000,
                "mode": "invalid",
            }

        if not isinstance(
            crop,
            np.ndarray,
        ):
            return {
                "is_phone": False,
                "phone_probability": 0.0,
                "phone_rank": 1000,
                "mode": "invalid",
            }

        if crop.size == 0:
            return {
                "is_phone": False,
                "phone_probability": 0.0,
                "phone_rank": 1000,
                "mode": "invalid",
            }

        standard_blob = self._prepare_standard(crop)

        full_object_blob = self._prepare_full_object(crop)

        results = []

        if standard_blob is not None:
            standard_result = self._run_blob(standard_blob)

            standard_result["mode"] = "standard"

            results.append(standard_result)

        if full_object_blob is not None:
            full_result = self._run_blob(full_object_blob)

            full_result["mode"] = "full_object"

            results.append(full_result)

        if not results:
            return {
                "is_phone": False,
                "phone_probability": 0.0,
                "phone_rank": 1000,
                "mode": "invalid",
            }

        best_result = min(
            results,
            key=lambda result: (
                result["phone_rank"],
                -result["phone_probability"],
            ),
        )

        is_phone = best_result["phone_rank"] <= self.PHONE_MAX_RANK

        return {
            "is_phone": bool(is_phone),
            "phone_probability": float(best_result["phone_probability"]),
            "phone_rank": int(best_result["phone_rank"]),
            "top1_class_id": int(best_result["top1_class_id"]),
            "top1_probability": float(best_result["top1_probability"]),
            "mode": best_result["mode"],
        }

    def close(self):
        if self.closed:
            return

        self.session = None
        self.closed = True

        print("[PHONE VERIFIER] Closed.")
