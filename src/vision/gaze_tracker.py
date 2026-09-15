import time

from datetime import datetime


class GazeTracker:
    """
    Gaze tracking based on MediaPipe Face Landmarker landmarks.

    IMPORTANT:
        This class does NOT run MediaPipe.

    FaceLandmarker is responsible for:
        frame -> MediaPipe -> 478 face landmarks

    GazeTracker is responsible for:
        478 landmarks -> iris position -> gaze direction

    Supported directions:

        CENTER
        LEFT
        RIGHT
        UP
        DOWN
        UNKNOWN
        CALIBRATING
    """

    # ============================================================
    # MEDIA PIPE IRIS LANDMARKS
    # ============================================================

    RIGHT_IRIS = [
        468,
        469,
        470,
        471,
        472,
    ]

    LEFT_IRIS = [
        473,
        474,
        475,
        476,
        477,
    ]

    # ============================================================
    # RIGHT EYE
    # ============================================================

    RIGHT_EYE_LEFT = 33
    RIGHT_EYE_RIGHT = 133

    RIGHT_EYE_TOP = 159
    RIGHT_EYE_BOTTOM = 145

    # ============================================================
    # LEFT EYE
    # ============================================================

    LEFT_EYE_LEFT = 362
    LEFT_EYE_RIGHT = 263

    LEFT_EYE_TOP = 386
    LEFT_EYE_BOTTOM = 374

    # ============================================================
    # CONSTRUCTOR
    # ============================================================

    def __init__(
        self,
        away_threshold_seconds=3.0,
        return_confirmation_seconds=0.4,
        calibration_seconds=3.0,
        horizontal_threshold=0.08,
        vertical_threshold=0.09,
        up_threshold=0.16,
        down_threshold=None,
    ):
        # --------------------------------------------------------
        # Anomaly timing
        # --------------------------------------------------------

        self.away_threshold_seconds = float(away_threshold_seconds)

        self.return_confirmation_seconds = float(return_confirmation_seconds)

        # --------------------------------------------------------
        # Calibration
        # --------------------------------------------------------

        self.calibration_seconds = float(calibration_seconds)

        self.calibration_started_at = None

        self.calibration_samples = []

        self.calibrated = False

        self.center_horizontal = None
        self.center_vertical = None

        # --------------------------------------------------------
        # Direction thresholds
        # --------------------------------------------------------

        self.horizontal_threshold = float(horizontal_threshold)

        self.vertical_threshold = float(vertical_threshold)

        self.up_threshold = float(
            up_threshold if up_threshold is not None else vertical_threshold
        )

        self.down_threshold = float(
            down_threshold if down_threshold is not None else vertical_threshold
        )

        # --------------------------------------------------------
        # Smoothing
        # --------------------------------------------------------

        self.smoothed_horizontal = None
        self.smoothed_vertical = None

        self.smoothing_factor = 0.35

        # --------------------------------------------------------
        # Runtime anomaly state
        # --------------------------------------------------------

        self.away_started_at = None

        self.away_logged = False

        self.center_started_at = None

        self.last_direction = "UNKNOWN"

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
        Safely retrieve a MediaPipe landmark.

        Returns None when the landmark is unavailable or malformed.
        """

        try:
            landmark = landmarks[index]

            x = float(landmark.x)
            y = float(landmark.y)

            if not (-1.0 <= x <= 2.0 and -1.0 <= y <= 2.0):
                return None

            return landmark

        except (
            IndexError,
            KeyError,
            TypeError,
            AttributeError,
            ValueError,
        ):
            return None

    # ============================================================
    # IRIS CENTER
    # ============================================================

    def _iris_center(
        self,
        landmarks,
        indexes,
    ):
        """
        Calculate the center of an iris using its five MediaPipe
        iris landmarks.
        """

        points = []

        for index in indexes:
            landmark = self._get_landmark(
                landmarks,
                index,
            )

            if landmark is None:
                return None

            points.append(
                (
                    float(landmark.x),
                    float(landmark.y),
                )
            )

        if not points:
            return None

        x = sum(point[0] for point in points) / len(points)

        y = sum(point[1] for point in points) / len(points)

        return (
            x,
            y,
        )

    # ============================================================
    # SINGLE EYE RATIO
    # ============================================================

    def _eye_ratio(
        self,
        landmarks,
        iris_indexes,
        left_corner,
        right_corner,
        top_point,
        bottom_point,
    ):
        """
        Calculate normalized iris position inside one eye.

        horizontal_ratio:
            approximately 0.0 -> left side
            approximately 0.5 -> center
            approximately 1.0 -> right side

        vertical_ratio:
            approximately 0.0 -> top
            approximately 0.5 -> center
            approximately 1.0 -> bottom
        """

        iris = self._iris_center(
            landmarks,
            iris_indexes,
        )

        if iris is None:
            return None

        left = self._get_landmark(
            landmarks,
            left_corner,
        )

        right = self._get_landmark(
            landmarks,
            right_corner,
        )

        top = self._get_landmark(
            landmarks,
            top_point,
        )

        bottom = self._get_landmark(
            landmarks,
            bottom_point,
        )

        if left is None or right is None or top is None or bottom is None:
            return None

        iris_x, iris_y = iris

        left_x = float(left.x)
        right_x = float(right.x)

        minimum_x = min(
            left_x,
            right_x,
        )

        maximum_x = max(
            left_x,
            right_x,
        )

        eye_width = maximum_x - minimum_x

        top_y = float(top.y)
        bottom_y = float(bottom.y)

        minimum_y = min(
            top_y,
            bottom_y,
        )

        maximum_y = max(
            top_y,
            bottom_y,
        )

        eye_height = maximum_y - minimum_y

        # --------------------------------------------------------
        # Prevent division by very small values.
        # --------------------------------------------------------

        if eye_width <= 0.001:
            return None

        if eye_height <= 0.001:
            return None

        horizontal_ratio = (iris_x - minimum_x) / eye_width

        vertical_ratio = (iris_y - minimum_y) / eye_height

        # --------------------------------------------------------
        # Defensive bounds.
        #
        # Small overshoots can occur because of landmark noise.
        # We don't reject the measurement; we clamp it.
        # --------------------------------------------------------

        horizontal_ratio = max(
            0.0,
            min(
                1.0,
                horizontal_ratio,
            ),
        )

        vertical_ratio = max(
            0.0,
            min(
                1.0,
                vertical_ratio,
            ),
        )

        return (
            horizontal_ratio,
            vertical_ratio,
        )

    # ============================================================
    # BOTH EYES
    # ============================================================

    def _calculate_eye_position(
        self,
        landmarks,
    ):
        """
        Calculate the average normalized eye position using both
        eyes.

        This is deliberately independent of head orientation.
        Head orientation will be handled separately by HeadTracker.
        """

        if landmarks is None:
            return None

        try:
            if len(landmarks) < 478:
                return None
        except TypeError:
            return None

        # --------------------------------------------------------
        # Right eye
        # --------------------------------------------------------

        right_eye = self._eye_ratio(
            landmarks,
            self.RIGHT_IRIS,
            self.RIGHT_EYE_LEFT,
            self.RIGHT_EYE_RIGHT,
            self.RIGHT_EYE_TOP,
            self.RIGHT_EYE_BOTTOM,
        )

        # --------------------------------------------------------
        # Left eye
        # --------------------------------------------------------

        left_eye = self._eye_ratio(
            landmarks,
            self.LEFT_IRIS,
            self.LEFT_EYE_LEFT,
            self.LEFT_EYE_RIGHT,
            self.LEFT_EYE_TOP,
            self.LEFT_EYE_BOTTOM,
        )

        # --------------------------------------------------------
        # We require BOTH eyes.
        #
        # This preserves the behavior of the old POC and avoids
        # making a gaze decision from a partially visible face.
        # --------------------------------------------------------

        if right_eye is None or left_eye is None:
            return None

        horizontal = (right_eye[0] + left_eye[0]) / 2.0

        vertical = (right_eye[1] + left_eye[1]) / 2.0

        return (
            horizontal,
            vertical,
        )

    # ============================================================
    # SMOOTHING
    # ============================================================

    def _smooth(
        self,
        horizontal,
        vertical,
    ):
        """
        Exponential smoothing to reduce frame-to-frame jitter.
        """

        if self.smoothed_horizontal is None or self.smoothed_vertical is None:
            self.smoothed_horizontal = horizontal

            self.smoothed_vertical = vertical

            return (
                horizontal,
                vertical,
            )

        alpha = self.smoothing_factor

        self.smoothed_horizontal = (
            alpha * horizontal + (1.0 - alpha) * self.smoothed_horizontal
        )

        self.smoothed_vertical = (
            alpha * vertical + (1.0 - alpha) * self.smoothed_vertical
        )

        return (
            self.smoothed_horizontal,
            self.smoothed_vertical,
        )

    # ============================================================
    # MEDIAN
    # ============================================================

    def _median(
        self,
        values,
    ):
        if not values:
            return 0.0

        values = sorted(values)

        count = len(values)

        middle = count // 2

        if count % 2 == 0:
            return (values[middle - 1] + values[middle]) / 2.0

        return values[middle]

    # ============================================================
    # CALIBRATION
    # ============================================================

    def _handle_calibration(
        self,
        horizontal,
        vertical,
    ):
        """
        Perform the original POC-style center calibration.

        The candidate looks naturally at the center for the
        configured calibration duration.
        """

        now = time.monotonic()

        if self.calibration_started_at is None:
            self.calibration_started_at = now

            print(
                "[GAZE] Calibration started. "
                "Look normally at the center "
                "of the laptop screen."
            )

        self.calibration_samples.append(
            (
                horizontal,
                vertical,
            )
        )

        elapsed = now - self.calibration_started_at

        if elapsed < self.calibration_seconds:
            return False

        if len(self.calibration_samples) < 5:
            return False

        horizontal_values = [sample[0] for sample in self.calibration_samples]

        vertical_values = [sample[1] for sample in self.calibration_samples]

        self.center_horizontal = self._median(horizontal_values)

        self.center_vertical = self._median(vertical_values)

        self.calibrated = True

        print(
            "[GAZE] Calibration completed "
            f"| center_x="
            f"{self.center_horizontal:.3f} "
            f"| center_y="
            f"{self.center_vertical:.3f}"
        )

        return True

    # ============================================================
    # DIRECTION
    # ============================================================

    def _calculate_direction(
        self,
        horizontal,
        vertical,
    ):
        """
        Convert calibrated eye ratios into a gaze direction.
        """

        if self.center_horizontal is None or self.center_vertical is None:
            return (
                "UNKNOWN",
                0.0,
                0.0,
            )

        horizontal_delta = horizontal - self.center_horizontal

        vertical_delta = vertical - self.center_vertical

        left_strength = 0.0
        right_strength = 0.0

        up_strength = 0.0
        down_strength = 0.0

        # --------------------------------------------------------
        # Horizontal
        # --------------------------------------------------------

        if horizontal_delta < 0:
            left_strength = abs(horizontal_delta) / max(
                self.horizontal_threshold,
                0.001,
            )

        elif horizontal_delta > 0:
            right_strength = horizontal_delta / max(
                self.horizontal_threshold,
                0.001,
            )

        # --------------------------------------------------------
        # Vertical
        # --------------------------------------------------------

        if vertical_delta < 0:
            up_strength = abs(vertical_delta) / max(
                self.up_threshold,
                0.001,
            )

        elif vertical_delta > 0:
            down_strength = vertical_delta / max(
                self.down_threshold,
                0.001,
            )

        strengths = {
            "LEFT": left_strength,
            "RIGHT": right_strength,
            "UP": up_strength,
            "DOWN": down_strength,
        }

        direction = max(
            strengths,
            key=strengths.get,
        )

        # --------------------------------------------------------
        # Below threshold = CENTER.
        # --------------------------------------------------------

        if strengths[direction] < 1.0:
            direction = "CENTER"

        return (
            direction,
            horizontal_delta,
            vertical_delta,
        )

    # ============================================================
    # ANOMALY STATE
    # ============================================================

    def _update_anomaly(
        self,
        direction,
    ):
        """
        Maintain sustained gaze-away state.

        GAZE_AWAY is only logged after the configured duration.

        Returning to CENTER must remain stable for the configured
        return confirmation period before GAZE_RETURNED is logged.
        """

        now = time.monotonic()

        away = direction != "CENTER"

        # --------------------------------------------------------
        # Candidate is looking away.
        # --------------------------------------------------------

        if away:

            self.center_started_at = None

            if self.away_started_at is None:
                self.away_started_at = now

            duration = now - self.away_started_at

            if duration >= self.away_threshold_seconds and not self.away_logged:
                self.away_logged = True

                print(
                    "[GAZE] "
                    f"[{self._timestamp()}] "
                    "GAZE_AWAY > "
                    f"{self.away_threshold_seconds:.0f}s "
                    "| Direction: "
                    f"{direction}"
                )

            return duration

        # --------------------------------------------------------
        # Candidate is back at CENTER.
        # --------------------------------------------------------

        if self.away_logged:

            if self.center_started_at is None:
                self.center_started_at = now

            return_duration = now - self.center_started_at

            if return_duration >= self.return_confirmation_seconds:
                print("[GAZE] " f"[{self._timestamp()}] " "GAZE_RETURNED_TO_SCREEN")

                self.away_logged = False

                self.away_started_at = None

                self.center_started_at = None

                return 0.0

            return return_duration

        # --------------------------------------------------------
        # No active anomaly.
        # --------------------------------------------------------

        self.away_started_at = None

        self.center_started_at = None

        return 0.0

    # ============================================================
    # MAIN PROCESS METHOD
    # ============================================================

    def process(
        self,
        landmarks,
        frame_shape=None,
    ):
        """
        Process already-generated MediaPipe face landmarks.

        Parameters
        ----------
        landmarks:
            MediaPipe face landmarks from FaceLandmarker.

        frame_shape:
            Kept for backward compatibility. The current gaze
            calculation uses normalized MediaPipe coordinates and
            therefore does not require frame dimensions.

        Returns
        -------
        dict
            Backward-compatible gaze state.
        """

        # --------------------------------------------------------
        # No landmarks.
        # --------------------------------------------------------

        if landmarks is None:
            return {
                "direction": "UNKNOWN",
                "away": False,
                "away_duration": 0.0,
                "valid": False,
                "calibrated": self.calibrated,
                "horizontal_ratio": None,
                "vertical_ratio": None,
            }

        # --------------------------------------------------------
        # Validate landmark count.
        # --------------------------------------------------------

        try:
            if len(landmarks) < 478:
                return {
                    "direction": "UNKNOWN",
                    "away": False,
                    "away_duration": 0.0,
                    "valid": False,
                    "calibrated": self.calibrated,
                    "horizontal_ratio": None,
                    "vertical_ratio": None,
                }
        except TypeError:
            return {
                "direction": "UNKNOWN",
                "away": False,
                "away_duration": 0.0,
                "valid": False,
                "calibrated": self.calibrated,
                "horizontal_ratio": None,
                "vertical_ratio": None,
            }

        # --------------------------------------------------------
        # Calculate eye position.
        # --------------------------------------------------------

        eye_position = self._calculate_eye_position(landmarks)

        if eye_position is None:
            return {
                "direction": "UNKNOWN",
                "away": False,
                "away_duration": 0.0,
                "valid": False,
                "calibrated": self.calibrated,
                "horizontal_ratio": None,
                "vertical_ratio": None,
            }

        horizontal, vertical = eye_position

        # --------------------------------------------------------
        # Smooth movement.
        # --------------------------------------------------------

        horizontal, vertical = self._smooth(
            horizontal,
            vertical,
        )

        # --------------------------------------------------------
        # Initial center calibration.
        #
        # This remains here for backward compatibility with the
        # old GazeTracker POC.
        # --------------------------------------------------------

        if not self.calibrated:

            self._handle_calibration(
                horizontal,
                vertical,
            )

            return {
                "direction": "CALIBRATING",
                "away": False,
                "away_duration": 0.0,
                "valid": True,
                "calibrated": self.calibrated,
                "horizontal_ratio": horizontal,
                "vertical_ratio": vertical,
                "horizontal_delta": 0.0,
                "vertical_delta": 0.0,
            }

        # --------------------------------------------------------
        # Calculate gaze direction.
        # --------------------------------------------------------

        (
            direction,
            horizontal_delta,
            vertical_delta,
        ) = self._calculate_direction(
            horizontal,
            vertical,
        )

        self.last_direction = direction

        # --------------------------------------------------------
        # Update sustained gaze anomaly.
        # --------------------------------------------------------

        duration = self._update_anomaly(direction)

        return {
            "direction": direction,
            "away": (direction != "CENTER"),
            "away_duration": duration,
            "valid": True,
            "calibrated": True,
            "horizontal_ratio": horizontal,
            "vertical_ratio": vertical,
            "horizontal_delta": horizontal_delta,
            "vertical_delta": vertical_delta,
        }

    # ============================================================
    # RESET PENDING STATE
    # ============================================================

    def reset_pending(self):
        """
        Reset pending away/return timing without destroying
        calibration.
        """

        if not self.away_logged:
            self.away_started_at = None

        self.center_started_at = None

    # ============================================================
    # RECALIBRATE
    # ============================================================

    def recalibrate(self):
        """
        Clear current center calibration while keeping the object
        reusable.
        """

        self.calibrated = False

        self.calibration_started_at = None

        self.calibration_samples = []

        self.center_horizontal = None
        self.center_vertical = None

        self.smoothed_horizontal = None
        self.smoothed_vertical = None

        self.away_started_at = None

        self.away_logged = False

        self.center_started_at = None

        self.last_direction = "UNKNOWN"

        print("[GAZE] Calibration reset")

    # ============================================================
    # CLOSE
    # ============================================================

    def close(self):
        """
        Kept for compatibility with the rest of the proctoring
        architecture.

        GazeTracker itself owns no external model/resource.
        """

        pass
