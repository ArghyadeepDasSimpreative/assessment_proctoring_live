import math
import time
from collections import deque


class PostureMonitor:

    def __init__(
        self,
        minimum_visibility=0.50,
        lean_left_boundary=0.30,
        lean_right_boundary=0.70,
        arm_raise_margin=0.04,
        movement_window_seconds=2.0,
        excessive_movement_threshold=2.8,
    ):
        self.minimum_visibility = float(minimum_visibility)

        self.lean_left_boundary = float(lean_left_boundary)

        self.lean_right_boundary = float(lean_right_boundary)

        self.arm_raise_margin = float(arm_raise_margin)

        self.movement_window_seconds = float(movement_window_seconds)

        self.excessive_movement_threshold = float(excessive_movement_threshold)

        self._left_wrist_history = deque()

        self._right_wrist_history = deque()

        self._last_process_time = None

    @staticmethod
    def _empty_state():
        return {
            "valid": False,
            "upper_body_visible": False,
            "leaning_left": False,
            "leaning_right": False,
            "left_arm_raised": False,
            "right_arm_raised": False,
            "unusual_arm_movement": False,
            "left_arm_movement": 0.0,
            "right_arm_movement": 0.0,
            "shoulder_center_x": None,
            "shoulder_width": None,
            "left_shoulder_visibility": 0.0,
            "right_shoulder_visibility": 0.0,
            "left_elbow_visible": False,
            "right_elbow_visible": False,
            "left_wrist_visible": False,
            "right_wrist_visible": False,
        }

    def _visible(
        self,
        landmark,
    ):
        if landmark is None:
            return False

        visibility = getattr(
            landmark,
            "visibility",
            0.0,
        )

        try:
            visibility = float(visibility)
        except (
            TypeError,
            ValueError,
        ):
            return False

        return visibility >= self.minimum_visibility

    @staticmethod
    def _distance(
        point_a,
        point_b,
    ):
        if point_a is None or point_b is None:
            return 0.0

        dx = float(point_a.x) - float(point_b.x)

        dy = float(point_a.y) - float(point_b.y)

        return math.sqrt((dx * dx) + (dy * dy))

    def _cleanup_history(
        self,
        history,
        current_time,
    ):
        cutoff = current_time - self.movement_window_seconds

        while history and history[0][0] < cutoff:
            history.popleft()

    def _calculate_movement(
        self,
        history,
        current_time,
    ):
        self._cleanup_history(
            history,
            current_time,
        )

        if len(history) < 2:
            return 0.0

        total_distance = 0.0

        previous_point = None

        for _, point in history:

            if previous_point is not None:
                total_distance += self._distance(
                    previous_point,
                    point,
                )

            previous_point = point

        return float(total_distance)

    def process(
        self,
        pose_result,
        frame_shape,
    ):
        state = self._empty_state()

        if not pose_result:
            self._clear_history()
            return state

        if not pose_result.get(
            "valid",
            False,
        ):
            self._clear_history()
            return state

        landmarks = pose_result.get("landmarks")

        if landmarks is None or len(landmarks) < 17:
            self._clear_history()
            return state

        current_time = time.monotonic()

        self._last_process_time = current_time

        left_shoulder = landmarks[11]
        right_shoulder = landmarks[12]

        left_elbow = landmarks[13]
        right_elbow = landmarks[14]

        left_wrist = landmarks[15]
        right_wrist = landmarks[16]

        left_shoulder_visible = self._visible(left_shoulder)

        right_shoulder_visible = self._visible(right_shoulder)

        left_elbow_visible = self._visible(left_elbow)

        right_elbow_visible = self._visible(right_elbow)

        left_wrist_visible = self._visible(left_wrist)

        right_wrist_visible = self._visible(right_wrist)

        state["left_shoulder_visibility"] = float(
            getattr(
                left_shoulder,
                "visibility",
                0.0,
            )
        )

        state["right_shoulder_visibility"] = float(
            getattr(
                right_shoulder,
                "visibility",
                0.0,
            )
        )

        state["left_elbow_visible"] = left_elbow_visible

        state["right_elbow_visible"] = right_elbow_visible

        state["left_wrist_visible"] = left_wrist_visible

        state["right_wrist_visible"] = right_wrist_visible

        if not left_shoulder_visible or not right_shoulder_visible:
            self._clear_history()

            state["valid"] = True

            state["upper_body_visible"] = False

            return state

        shoulder_center_x = (float(left_shoulder.x) + float(right_shoulder.x)) / 2.0

        shoulder_width = abs(float(left_shoulder.x) - float(right_shoulder.x))

        state["valid"] = True

        state["upper_body_visible"] = shoulder_width > 0.05

        state["shoulder_center_x"] = float(shoulder_center_x)

        state["shoulder_width"] = float(shoulder_width)

        if not state["upper_body_visible"]:
            self._clear_history()
            return state

        if shoulder_center_x < self.lean_left_boundary:
            state["leaning_left"] = True

        elif shoulder_center_x > self.lean_right_boundary:
            state["leaning_right"] = True

        if left_elbow_visible and left_wrist_visible:
            if float(left_wrist.y) < float(left_shoulder.y) - self.arm_raise_margin:
                state["left_arm_raised"] = True

        if right_elbow_visible and right_wrist_visible:
            if float(right_wrist.y) < float(right_shoulder.y) - self.arm_raise_margin:
                state["right_arm_raised"] = True

        if left_wrist_visible:
            self._left_wrist_history.append(
                (
                    current_time,
                    left_wrist,
                )
            )

        if right_wrist_visible:
            self._right_wrist_history.append(
                (
                    current_time,
                    right_wrist,
                )
            )

        left_movement = self._calculate_movement(
            self._left_wrist_history,
            current_time,
        )

        right_movement = self._calculate_movement(
            self._right_wrist_history,
            current_time,
        )

        state["left_arm_movement"] = left_movement

        state["right_arm_movement"] = right_movement

        state["unusual_arm_movement"] = (
            left_movement >= self.excessive_movement_threshold
            or right_movement >= self.excessive_movement_threshold
        )

        return state

    def _clear_history(self):
        self._left_wrist_history.clear()

        self._right_wrist_history.clear()

    def reset(self):
        self._clear_history()

        self._last_process_time = None
