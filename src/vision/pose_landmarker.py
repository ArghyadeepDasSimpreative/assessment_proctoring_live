import time

from pathlib import Path

import cv2

import mediapipe as mp


class PoseLandmarker:

    def __init__(
        self,
        model_path="models/pose_landmarker.task",
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    ):
        project_root = Path(__file__).resolve().parents[2]

        self.model_path = project_root / model_path

        if not self.model_path.exists():
            raise FileNotFoundError(f"Pose model not found: {self.model_path}")

        base_options = mp.tasks.BaseOptions(model_asset_path=str(self.model_path))

        options = mp.tasks.vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=(min_pose_detection_confidence),
            min_pose_presence_confidence=(min_pose_presence_confidence),
            min_tracking_confidence=(min_tracking_confidence),
            output_segmentation_masks=False,
        )

        self.landmarker = mp.tasks.vision.PoseLandmarker.create_from_options(options)

        self.start_time = time.monotonic()

        self.last_timestamp_ms = -1

    def _timestamp_ms(self):
        timestamp_ms = int((time.monotonic() - self.start_time) * 1000)

        if timestamp_ms <= self.last_timestamp_ms:
            timestamp_ms = self.last_timestamp_ms + 1

        self.last_timestamp_ms = timestamp_ms

        return timestamp_ms

    def process(self, frame):

        if frame is None:
            return {
                "valid": False,
                "pose_count": 0,
                "landmarks": None,
                "world_landmarks": None,
            }

        rgb_frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB,
        )

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb_frame,
        )

        timestamp_ms = self._timestamp_ms()

        result = self.landmarker.detect_for_video(
            mp_image,
            timestamp_ms,
        )

        if not result.pose_landmarks or len(result.pose_landmarks) == 0:
            return {
                "valid": False,
                "pose_count": 0,
                "landmarks": None,
                "world_landmarks": None,
            }

        landmarks = result.pose_landmarks[0]

        world_landmarks = None

        if result.pose_world_landmarks and len(result.pose_world_landmarks) > 0:
            world_landmarks = result.pose_world_landmarks[0]

        return {
            "valid": True,
            "pose_count": len(result.pose_landmarks),
            "landmarks": landmarks,
            "world_landmarks": world_landmarks,
        }

    def close(self):

        if self.landmarker is not None:
            self.landmarker.close()

            self.landmarker = None
