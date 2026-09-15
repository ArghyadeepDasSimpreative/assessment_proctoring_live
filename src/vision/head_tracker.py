import math
import time

from datetime import datetime


class HeadTracker:
    """
    Head orientation tracker based on MediaPipe Face Landmarker
    landmarks.

    IMPORTANT:
        This class does NOT run MediaPipe itself.

    FaceLandmarker is responsible for:
        frame -> MediaPipe -> face landmarks

    HeadTracker is responsible for:
        face landmarks -> head orientation

    Supported directions:

        CENTER
        LEFT
        RIGHT
        UP
        DOWN
        UNKNOWN

    The class is intentionally kept compatible with the old POC
    architecture.
    """

    # ============================================================
    # FACE LANDMARKS
    # ============================================================

    NOSE_TIP = 1

    FOREHEAD = 10

    CHIN = 152

    LEFT_CHEEK = 234

    RIGHT_CHEEK = 454

    LEFT_EYE_OUTER = 33

    RIGHT_EYE_OUTER = 263

    LEFT_EYE_INNER = 133

    RIGHT_EYE_INNER = 362

    # ============================================================
    # CONSTRUCTOR
    # ============================================================

    def __init__(
        self,
        yaw_threshold=12.0,
        pitch_threshold=10.0,
        roll_threshold=15.0,
        smoothing_factor=0.35,
        hysteresis=2.5,
    ):
        # --------------------------------------------------------
        # Direction thresholds
        # --------------------------------------------------------

        self.yaw_threshold = float(yaw_threshold)

        self.pitch_threshold = float(pitch_threshold)

        self.roll_threshold = float(roll_threshold)

        # --------------------------------------------------------
        # Smoothing
        # --------------------------------------------------------

        self.smoothing_factor = max(
            0.01,
            min(
                1.0,
                float(smoothing_factor),
            ),
        )

        # --------------------------------------------------------
        # Hysteresis prevents:
        #
        # CENTER -> LEFT -> CENTER -> LEFT
        #
        # when the head is sitting near a threshold.
        # --------------------------------------------------------

        self.hysteresis = max(
            0.0,
            float(hysteresis),
        )

        # --------------------------------------------------------
        # Smoothed orientation
        # --------------------------------------------------------

        self.smoothed_yaw = None

        self.smoothed_pitch = None

        self.smoothed_roll = None

        # --------------------------------------------------------
        # Current state
        # --------------------------------------------------------

        self.last_direction = "UNKNOWN"

        self.last_valid = False

        self.last_yaw = None

        self.last_pitch = None

        self.last_roll = None

        # --------------------------------------------------------
        # Away tracking
        # --------------------------------------------------------

        self.away_started_at = None

        self.last_active_at = None

    # ============================================================
    # TIMESTAMP
    # ============================================================

    def _timestamp(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ============================================================
    # SAFE LANDMARK ACCESS
    # ============================================================

    def _get_landmark(
        self,
        landmarks,
        index,
    ):
        """
        Safely retrieve one MediaPipe landmark.
        """

        try:
            landmark = landmarks[index]

            x = float(landmark.x)
            y = float(landmark.y)
            z = float(
                getattr(
                    landmark,
                    "z",
                    0.0,
                )
            )

            if not (math.isfinite(x) and math.isfinite(y) and math.isfinite(z)):
                return None

            return (
                x,
                y,
                z,
            )

        except (
            IndexError,
            KeyError,
            TypeError,
            AttributeError,
            ValueError,
        ):
            return None

    # ============================================================
    # DISTANCE
    # ============================================================

    def _distance(
        self,
        point_a,
        point_b,
    ):
        if point_a is None or point_b is None:
            return None

        dx = point_a[0] - point_b[0]

        dy = point_a[1] - point_b[1]

        dz = point_a[2] - point_b[2]

        return math.sqrt(dx * dx + dy * dy + dz * dz)

    # ============================================================
    # MIDPOINT
    # ============================================================

    def _midpoint(
        self,
        point_a,
        point_b,
    ):
        if point_a is None or point_b is None:
            return None

        return (
            (point_a[0] + point_b[0]) / 2.0,
            (point_a[1] + point_b[1]) / 2.0,
            (point_a[2] + point_b[2]) / 2.0,
        )

    # ============================================================
    # SMOOTH VALUE
    # ============================================================

    def _smooth_value(
        self,
        current,
        previous,
    ):
        if previous is None:
            return current

        alpha = self.smoothing_factor

        return alpha * current + (1.0 - alpha) * previous

    # ============================================================
    # CALCULATE ROLL
    # ============================================================

    def _calculate_roll(
        self,
        landmarks,
    ):
        """
        Estimate roll using the line between the outer eye
        corners.

        Positive/negative orientation depends on the camera
        coordinate system; classification only cares about the
        magnitude here.
        """

        left_eye = self._get_landmark(
            landmarks,
            self.LEFT_EYE_OUTER,
        )

        right_eye = self._get_landmark(
            landmarks,
            self.RIGHT_EYE_OUTER,
        )

        if left_eye is None or right_eye is None:
            return None

        dx = right_eye[0] - left_eye[0]

        dy = right_eye[1] - left_eye[1]

        if abs(dx) < 0.0001:
            return None

        return math.degrees(
            math.atan2(
                dy,
                dx,
            )
        )

    # ============================================================
    # CALCULATE YAW
    # ============================================================

    def _calculate_yaw(
        self,
        landmarks,
    ):
        """
        Estimate left/right head rotation from the relative
        position of the nose against the cheek/face width.

        This is a normalized landmark-based estimate and does not
        require a separate camera calibration matrix.

        It is intentionally compatible with the lightweight POC
        approach.
        """

        nose = self._get_landmark(
            landmarks,
            self.NOSE_TIP,
        )

        left_cheek = self._get_landmark(
            landmarks,
            self.LEFT_CHEEK,
        )

        right_cheek = self._get_landmark(
            landmarks,
            self.RIGHT_CHEEK,
        )

        if nose is None or left_cheek is None or right_cheek is None:
            return None

        left_x = left_cheek[0]

        right_x = right_cheek[0]

        face_width = right_x - left_x

        if abs(face_width) < 0.001:
            return None

        face_center_x = (left_x + right_x) / 2.0

        normalized_offset = (nose[0] - face_center_x) / abs(face_width)

        # --------------------------------------------------------
        # Convert normalized horizontal offset into an approximate
        # yaw angle.
        #
        # The exact camera geometry is not required for direction
        # classification; the value is primarily used consistently
        # across frames and during calibration.
        # --------------------------------------------------------

        yaw = math.degrees(math.atan(normalized_offset * 2.0))

        return yaw

    # ============================================================
    # CALCULATE PITCH
    # ============================================================

    def _calculate_pitch(
        self,
        landmarks,
    ):
        """
        Estimate up/down head movement using nose position
        relative to the forehead/chin axis.

        This is designed for directional classification rather
        than exact physical head-angle measurement.
        """

        nose = self._get_landmark(
            landmarks,
            self.NOSE_TIP,
        )

        forehead = self._get_landmark(
            landmarks,
            self.FOREHEAD,
        )

        chin = self._get_landmark(
            landmarks,
            self.CHIN,
        )

        if nose is None or forehead is None or chin is None:
            return None

        face_height = chin[1] - forehead[1]

        if abs(face_height) < 0.001:
            return None

        face_vertical_center = (forehead[1] + chin[1]) / 2.0

        normalized_offset = (nose[1] - face_vertical_center) / abs(face_height)

        # --------------------------------------------------------
        # Convert into an approximate angle.
        # --------------------------------------------------------

        pitch = math.degrees(math.atan(normalized_offset * 2.0))

        return pitch

    # ============================================================
    # ORIENTATION
    # ============================================================

    def _calculate_orientation(
        self,
        landmarks,
    ):
        """
        Calculate yaw, pitch and roll.
        """

        if landmarks is None:
            return None

        try:
            if len(landmarks) < 478:
                return None
        except TypeError:
            return None

        yaw = self._calculate_yaw(landmarks)

        pitch = self._calculate_pitch(landmarks)

        roll = self._calculate_roll(landmarks)

        if yaw is None or pitch is None or roll is None:
            return None

        return {
            "yaw": float(yaw),
            "pitch": float(pitch),
            "roll": float(roll),
        }

    # ============================================================
    # DIRECTION WITH HYSTERESIS
    # ============================================================

    def _direction_with_hysteresis(
        self,
        yaw,
        pitch,
    ):
        """
        Determine primary head direction.

        LEFT/RIGHT are based on yaw.

        UP/DOWN are based on pitch.

        When horizontal and vertical movement are both present,
        the strongest normalized movement wins.
        """

        yaw_threshold = self.yaw_threshold

        pitch_threshold = self.pitch_threshold

        # --------------------------------------------------------
        # Normalize movement by thresholds.
        # --------------------------------------------------------

        yaw_strength = abs(yaw) / max(
            yaw_threshold,
            0.001,
        )

        pitch_strength = abs(pitch) / max(
            pitch_threshold,
            0.001,
        )

        # --------------------------------------------------------
        # Candidate direction.
        # --------------------------------------------------------

        candidate = "CENTER"

        if yaw_strength >= 1.0 and yaw_strength >= pitch_strength:
            if yaw < 0:
                candidate = "LEFT"
            else:
                candidate = "RIGHT"

        elif pitch_strength >= 1.0:
            if pitch < 0:
                candidate = "UP"
            else:
                candidate = "DOWN"

        # --------------------------------------------------------
        # Hysteresis:
        #
        # Once LEFT/RIGHT/UP/DOWN has been established, require a
        # slightly stronger movement in the opposite direction
        # before switching.
        # --------------------------------------------------------

        previous = self.last_direction

        if previous == "LEFT":
            if candidate == "CENTER" and yaw < (yaw_threshold + self.hysteresis) * -1:
                return "LEFT"

        elif previous == "RIGHT":
            if candidate == "CENTER" and yaw > (yaw_threshold + self.hysteresis):
                return "RIGHT"

        elif previous == "UP":
            if (
                candidate == "CENTER"
                and pitch < (pitch_threshold + self.hysteresis) * -1
            ):
                return "UP"

        elif previous == "DOWN":
            if candidate == "CENTER" and pitch > (pitch_threshold + self.hysteresis):
                return "DOWN"

        return candidate

    # ============================================================
    # MAIN PROCESS
    # ============================================================

    def process(
        self,
        landmarks,
        frame_shape=None,
    ):
        """
        Process MediaPipe Face Landmarker output.

        frame_shape is retained for backward compatibility.

        Returns:

            {
                "direction": "CENTER",
                "valid": True,
                "yaw": ...,
                "pitch": ...,
                "roll": ...,
                "away": False,
                "away_duration": 0.0
            }
        """

        if landmarks is None:
            self.last_valid = False

            return {
                "direction": "UNKNOWN",
                "valid": False,
                "yaw": None,
                "pitch": None,
                "roll": None,
                "away": False,
                "away_duration": 0.0,
            }

        orientation = self._calculate_orientation(landmarks)

        if orientation is None:
            self.last_valid = False

            return {
                "direction": "UNKNOWN",
                "valid": False,
                "yaw": None,
                "pitch": None,
                "roll": None,
                "away": False,
                "away_duration": 0.0,
            }

        yaw = orientation["yaw"]

        pitch = orientation["pitch"]

        roll = orientation["roll"]

        # --------------------------------------------------------
        # Smooth orientation.
        # --------------------------------------------------------

        yaw = self._smooth_value(
            yaw,
            self.smoothed_yaw,
        )

        pitch = self._smooth_value(
            pitch,
            self.smoothed_pitch,
        )

        roll = self._smooth_value(
            roll,
            self.smoothed_roll,
        )

        self.smoothed_yaw = yaw

        self.smoothed_pitch = pitch

        self.smoothed_roll = roll

        self.last_yaw = yaw

        self.last_pitch = pitch

        self.last_roll = roll

        self.last_valid = True

        # --------------------------------------------------------
        # Determine direction.
        # --------------------------------------------------------

        direction = self._direction_with_hysteresis(
            yaw,
            pitch,
        )

        self.last_direction = direction

        # --------------------------------------------------------
        # Away timing.
        # --------------------------------------------------------

        now = time.monotonic()

        away = direction != "CENTER"

        if away:

            if self.away_started_at is None:
                self.away_started_at = now

            self.last_active_at = now

            away_duration = now - self.away_started_at

        else:

            self.away_started_at = None

            self.last_active_at = None

            away_duration = 0.0

        return {
            "direction": direction,
            "valid": True,
            "yaw": yaw,
            "pitch": pitch,
            "roll": roll,
            "away": away,
            "away_duration": away_duration,
        }

    # ============================================================
    # RESET PENDING STATE
    # ============================================================

    def reset_pending(self):
        """
        Reset only temporary away tracking.
        """

        self.away_started_at = None

        self.last_active_at = None

    # ============================================================
    # RESET
    # ============================================================

    def reset(self):
        """
        Reset runtime state while keeping configuration.
        """

        self.smoothed_yaw = None

        self.smoothed_pitch = None

        self.smoothed_roll = None

        self.last_direction = "UNKNOWN"

        self.last_valid = False

        self.last_yaw = None

        self.last_pitch = None

        self.last_roll = None

        self.away_started_at = None

        self.last_active_at = None

    # ============================================================
    # CLOSE
    # ============================================================

    def close(self):
        """
        Compatibility method.

        HeadTracker does not own an external model.
        """

        self.reset()
