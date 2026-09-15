import json
import time

from datetime import datetime
from numbers import Real
from pathlib import Path
from statistics import median


class CalibrationManager:
    """
    Handles guided calibration for:

        CENTER
        GAZE_LEFT
        GAZE_RIGHT
        GAZE_UP
        GAZE_DOWN
        HEAD_LEFT
        HEAD_RIGHT
        HEAD_UP
        HEAD_DOWN

    The manager is intentionally independent from:

        - FaceLandmarker
        - GazeTracker
        - HeadTracker

    Those components provide measurements.

    This class only:
        1. Guides calibration.
        2. Stores calibration measurements.
        3. Persists the calibration profile.
        4. Classifies calibrated gaze/head direction.
        5. Maintains runtime away-duration state.
    """

    # ============================================================
    # CALIBRATION STEPS
    # ============================================================

    STEPS = [
        {
            "key": "CENTER",
            "instruction": "Look naturally at the CENTER of the screen",
            "duration": 2.0,
        },
        {
            "key": "GAZE_LEFT",
            "instruction": (
                "Keep your head straight and look LEFT using only your eyes"
            ),
            "duration": 1.2,
        },
        {
            "key": "GAZE_RIGHT",
            "instruction": (
                "Keep your head straight and look RIGHT using only your eyes"
            ),
            "duration": 1.2,
        },
        {
            "key": "GAZE_UP",
            "instruction": ("Keep your head straight and look UP using only your eyes"),
            "duration": 1.2,
        },
        {
            "key": "GAZE_DOWN",
            "instruction": (
                "Keep your head straight and look DOWN using only your eyes"
            ),
            "duration": 1.2,
        },
        {
            "key": "HEAD_LEFT",
            "instruction": "Turn your HEAD LEFT",
            "duration": 1.2,
        },
        {
            "key": "HEAD_RIGHT",
            "instruction": "Turn your HEAD RIGHT",
            "duration": 1.2,
        },
        {
            "key": "HEAD_UP",
            "instruction": "Tilt your HEAD UP",
            "duration": 1.2,
        },
        {
            "key": "HEAD_DOWN",
            "instruction": "Tilt your HEAD DOWN",
            "duration": 1.2,
        },
    ]

    # ============================================================
    # REQUIRED SAVED CALIBRATION STAGES
    # ============================================================

    REQUIRED_STAGES = {
        "CENTER",
        "GAZE_LEFT",
        "GAZE_RIGHT",
        "GAZE_UP",
        "GAZE_DOWN",
        "HEAD_LEFT",
        "HEAD_RIGHT",
        "HEAD_UP",
        "HEAD_DOWN",
    }

    # ============================================================
    # CONSTRUCTOR
    # ============================================================

    def __init__(
        self,
        student_id="local_test",
        exam_id="local_test",
        schedule_id="local_test",
        session_id="local_test",
        base_directory="data/calibration",
        force_recalibration=False,
        stage_timeout_seconds=10.0,
        recovery_grace_seconds=0.6,
    ):
        project_root = Path(__file__).resolve().parents[2]

        self.student_id = str(student_id)
        self.exam_id = str(exam_id)
        self.schedule_id = str(schedule_id)
        self.session_id = str(session_id)

        self.base_directory = project_root / base_directory

        self.student_directory = self.base_directory / f"student_{self.student_id}"

        self.profile_path = self.student_directory / (
            f"exam_{self.exam_id}"
            f"__schedule_{self.schedule_id}"
            f"__session_{self.session_id}.json"
        )

        self.stage_timeout_seconds = float(stage_timeout_seconds)

        self.recovery_grace_seconds = float(recovery_grace_seconds)

        # --------------------------------------------------------
        # Saved calibration profile
        # --------------------------------------------------------

        self.profile = None
        self.completed = False

        # --------------------------------------------------------
        # Current calibration stage
        # --------------------------------------------------------

        self.stage_index = 0
        self.stage_started_at = time.monotonic()

        self.valid_started_at = None
        self.samples = []

        self.retry_count = 0
        self.retry_notice_until = 0.0

        # --------------------------------------------------------
        # Runtime gaze/head states
        # --------------------------------------------------------

        self.runtime_states = {
            "gaze": {
                "started_at": None,
                "last_active_at": None,
                "last_direction": "CENTER",
            },
            "head": {
                "started_at": None,
                "last_active_at": None,
                "last_direction": "CENTER",
            },
        }

        # --------------------------------------------------------
        # Try to load an existing calibration profile.
        # --------------------------------------------------------

        if not force_recalibration:
            self._load_profile()

    # ============================================================
    # PROFILE LOADING
    # ============================================================

    def _load_profile(self):
        """
        Load an existing calibration profile.

        A profile is accepted only when all required calibration
        stages are present.
        """

        if not self.profile_path.exists():
            return False

        try:
            with open(
                self.profile_path,
                "r",
                encoding="utf-8",
            ) as file:
                profile = json.load(file)

            if not isinstance(profile, dict):
                print("[CALIBRATION LOAD ERROR] " "Invalid profile format.")
                return False

            samples = profile.get(
                "samples",
                {},
            )

            if not isinstance(samples, dict):
                print("[CALIBRATION LOAD ERROR] " "Invalid samples format.")
                return False

            if not self.REQUIRED_STAGES.issubset(samples.keys()):
                print("[CALIBRATION] Existing profile is incomplete.")
                return False

            self.profile = profile
            self.completed = True

            print("[CALIBRATION] Loaded: " f"{self.profile_path}")

            return True

        except Exception as error:
            print("[CALIBRATION LOAD ERROR] " f"{error}")

            return False

    # ============================================================
    # PROFILE SAVING
    # ============================================================

    def _save_profile(self):
        """
        Persist calibration profile as JSON.
        """

        self.student_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_path = self.profile_path.with_suffix(".tmp")

        try:
            with open(
                temporary_path,
                "w",
                encoding="utf-8",
            ) as file:
                json.dump(
                    self.profile,
                    file,
                    indent=2,
                    ensure_ascii=False,
                )

            temporary_path.replace(self.profile_path)

            print("[CALIBRATION] Saved: " f"{self.profile_path}")

        except Exception:
            try:
                if temporary_path.exists():
                    temporary_path.unlink()
            except Exception:
                pass

            raise

    # ============================================================
    # NUMBER VALIDATION
    # ============================================================

    def _is_number(
        self,
        value,
    ):
        """
        Accept normal Python numbers as well as numeric values
        returned by libraries such as NumPy.
        """

        return isinstance(
            value,
            Real,
        ) and not isinstance(
            value,
            bool,
        )

    # ============================================================
    # BUILD MEASUREMENT
    # ============================================================

    def _measurement(
        self,
        gaze_state,
        head_state,
    ):
        """
        Combine GazeTracker and HeadTracker output into one
        calibration measurement.

        Expected gaze_state fields:

            valid
            horizontal_ratio
            vertical_ratio

        Expected head_state fields:

            valid
            yaw
            pitch
            roll
        """

        if not isinstance(
            gaze_state,
            dict,
        ):
            return None

        if not isinstance(
            head_state,
            dict,
        ):
            return None

        if not gaze_state.get(
            "valid",
            False,
        ):
            return None

        if not head_state.get(
            "valid",
            False,
        ):
            return None

        values = {
            "gaze_x": gaze_state.get("horizontal_ratio"),
            "gaze_y": gaze_state.get("vertical_ratio"),
            "yaw": head_state.get("yaw"),
            "pitch": head_state.get("pitch"),
            "roll": head_state.get("roll"),
        }

        if not all(self._is_number(value) for value in values.values()):
            return None

        return {key: float(value) for key, value in values.items()}

    # ============================================================
    # CENTER SAMPLE
    # ============================================================

    def _center_sample(self):
        if self.profile is None:
            return None

        samples = self.profile.get(
            "samples",
            {},
        )

        return samples.get("CENTER")

    # ============================================================
    # CENTER STABILITY
    # ============================================================

    def _center_is_stable(
        self,
        measurement,
    ):
        """
        During CENTER calibration, require measurements to remain
        reasonably stable instead of accepting random movement.
        """

        if not self.samples:
            return True

        reference = {
            "gaze_x": median([item["gaze_x"] for item in self.samples]),
            "gaze_y": median([item["gaze_y"] for item in self.samples]),
            "yaw": median([item["yaw"] for item in self.samples]),
            "pitch": median([item["pitch"] for item in self.samples]),
        }

        return (
            abs(measurement["gaze_x"] - reference["gaze_x"]) <= 0.035
            and abs(measurement["gaze_y"] - reference["gaze_y"]) <= 0.045
            and abs(measurement["yaw"] - reference["yaw"]) <= 7.0
            and abs(measurement["pitch"] - reference["pitch"]) <= 7.0
        )

    # ============================================================
    # MATCH CURRENT CALIBRATION STAGE
    # ============================================================

    def _matches_stage(
        self,
        stage_key,
        measurement,
    ):
        """
        Determine whether the current measurement satisfies the
        requested calibration stage.
        """

        if stage_key == "CENTER":
            return self._center_is_stable(measurement)

        center = self._center_sample()

        if center is None:
            return False

        gaze_x = measurement["gaze_x"]
        gaze_y = measurement["gaze_y"]

        yaw = measurement["yaw"]
        pitch = measurement["pitch"]

        center_gaze_x = center["gaze_x"]
        center_gaze_y = center["gaze_y"]

        center_yaw = center["yaw"]
        center_pitch = center["pitch"]

        # --------------------------------------------------------
        # During gaze calibration, head must remain approximately
        # centered so we are measuring eye movement rather than
        # head movement.
        # --------------------------------------------------------

        head_near_center = (
            abs(yaw - center_yaw) <= 11.0 and abs(pitch - center_pitch) <= 9.0
        )

        if stage_key == "GAZE_LEFT":
            return head_near_center and gaze_x <= center_gaze_x - 0.025

        if stage_key == "GAZE_RIGHT":
            return head_near_center and gaze_x >= center_gaze_x + 0.025

        if stage_key == "GAZE_UP":
            return head_near_center and gaze_y <= center_gaze_y - 0.035

        if stage_key == "GAZE_DOWN":
            return head_near_center and gaze_y >= center_gaze_y + 0.035

        # --------------------------------------------------------
        # Head calibration
        # --------------------------------------------------------

        if stage_key == "HEAD_LEFT":
            return yaw <= center_yaw - 12.0

        if stage_key == "HEAD_RIGHT":
            return yaw >= center_yaw + 12.0

        if stage_key == "HEAD_UP":
            return pitch <= center_pitch - 9.0

        if stage_key == "HEAD_DOWN":
            return pitch >= center_pitch + 9.0

        return False

    # ============================================================
    # MEDIAN SAMPLE
    # ============================================================

    def _median_sample(
        self,
        samples,
    ):
        """
        Convert multiple valid measurements into one stable
        calibration point using median values.
        """

        if not samples:
            raise ValueError(
                "Cannot create calibration sample " "from empty sample list."
            )

        return {
            "gaze_x": round(
                median([item["gaze_x"] for item in samples]),
                6,
            ),
            "gaze_y": round(
                median([item["gaze_y"] for item in samples]),
                6,
            ),
            "yaw": round(
                median([item["yaw"] for item in samples]),
                4,
            ),
            "pitch": round(
                median([item["pitch"] for item in samples]),
                4,
            ),
            "roll": round(
                median([item["roll"] for item in samples]),
                4,
            ),
            "sample_count": len(samples),
        }

    # ============================================================
    # FINISH CURRENT STAGE
    # ============================================================

    def _finish_stage(
        self,
        stage_key,
    ):
        """
        Save the median measurement for the completed stage.
        """

        if self.profile is None:
            self.profile = {
                "version": 1,
                "student_id": self.student_id,
                "exam_id": self.exam_id,
                "schedule_id": self.schedule_id,
                "session_id": self.session_id,
                "created_at": (datetime.now().astimezone().isoformat()),
                "samples": {},
            }

        self.profile.setdefault(
            "samples",
            {},
        )

        self.profile["samples"][stage_key] = self._median_sample(self.samples)

        print("[CALIBRATION] Recorded " f"{stage_key}")

        self.stage_index += 1

        self.stage_started_at = time.monotonic()

        self.valid_started_at = None
        self.samples = []
        self.retry_count = 0
        self.retry_notice_until = 0.0

        # --------------------------------------------------------
        # All calibration stages completed.
        # --------------------------------------------------------

        if self.stage_index >= len(self.STEPS):
            self.profile["completed_at"] = datetime.now().astimezone().isoformat()

            self.completed = True

            self._save_profile()

            print("[CALIBRATION] Complete. " "Proctoring is starting.")

    # ============================================================
    # CALIBRATION UPDATE
    # ============================================================

    def update(
        self,
        gaze_state,
        head_state,
    ):
        """
        Feed the latest GazeTracker and HeadTracker states into
        the calibration process.

        Returns a backward-compatible state dictionary.
        """

        if self.completed:
            return {
                "completed": True,
                "instruction": ("Calibration complete"),
            }

        # --------------------------------------------------------
        # Safety guard.
        # --------------------------------------------------------

        if self.stage_index >= len(self.STEPS):
            self.completed = True

            return {
                "completed": True,
                "instruction": ("Calibration complete"),
            }

        now = time.monotonic()

        stage = self.STEPS[self.stage_index]

        stage_key = stage["key"]

        measurement = self._measurement(
            gaze_state,
            head_state,
        )

        # --------------------------------------------------------
        # Stage timeout.
        # --------------------------------------------------------

        if now - self.stage_started_at >= self.stage_timeout_seconds:
            self.stage_started_at = now

            self.valid_started_at = None
            self.samples = []

            self.retry_count += 1

            self.retry_notice_until = now + 2.0

            print(
                "[CALIBRATION] Could not " f"confirm {stage_key}. " "Please try again."
            )

        # --------------------------------------------------------
        # Invalid measurement.
        # --------------------------------------------------------

        if measurement is None:
            self.valid_started_at = None
            self.samples = []

            return {
                "completed": False,
                "stage": stage_key,
                "instruction": (self.current_instruction()),
                "valid": False,
                "progress": self.progress(),
            }

        # --------------------------------------------------------
        # Measurement doesn't match requested movement.
        # --------------------------------------------------------

        if not self._matches_stage(
            stage_key,
            measurement,
        ):
            self.valid_started_at = None
            self.samples = []

            return {
                "completed": False,
                "stage": stage_key,
                "instruction": (self.current_instruction()),
                "valid": False,
                "progress": self.progress(),
            }

        # --------------------------------------------------------
        # Start continuous valid period.
        # --------------------------------------------------------

        if self.valid_started_at is None:
            self.valid_started_at = now
            self.samples = []

        self.samples.append(measurement)

        valid_duration = now - self.valid_started_at

        # --------------------------------------------------------
        # Require both duration and minimum number of samples.
        # --------------------------------------------------------

        if valid_duration >= float(stage["duration"]) and len(self.samples) >= 4:
            self._finish_stage(stage_key)

        # --------------------------------------------------------
        # Completion may have happened inside _finish_stage().
        # --------------------------------------------------------

        return {
            "completed": self.completed,
            "stage": (None if self.completed else self.STEPS[self.stage_index]["key"]),
            "instruction": (self.current_instruction()),
            "valid": True,
            "progress": self.progress(),
        }

    # ============================================================
    # CURRENT INSTRUCTION
    # ============================================================

    def current_instruction(self):
        if self.completed:
            return "Calibration complete. " "Proctoring is starting."

        if self.stage_index >= len(self.STEPS):
            return "Calibration complete. " "Proctoring is starting."

        stage = self.STEPS[self.stage_index]

        prefix = ""

        if time.monotonic() < self.retry_notice_until:
            prefix = "Try again - "

        return prefix + stage["instruction"]

    # ============================================================
    # PROGRESS
    # ============================================================

    def progress(self):
        return {
            "current": min(
                self.stage_index + 1,
                len(self.STEPS),
            ),
            "total": len(self.STEPS),
        }

    # ============================================================
    # GAZE CLASSIFICATION
    # ============================================================

    def _classify_gaze(
        self,
        gaze_state,
    ):
        """
        Classify gaze using the student's own calibration
        profile.
        """

        if not self.completed or self.profile is None:
            return "UNKNOWN"

        if not isinstance(
            gaze_state,
            dict,
        ):
            return "UNKNOWN"

        if not gaze_state.get(
            "valid",
            False,
        ):
            return "UNKNOWN"

        gaze_x = gaze_state.get("horizontal_ratio")

        gaze_y = gaze_state.get("vertical_ratio")

        if not self._is_number(gaze_x) or not self._is_number(gaze_y):
            return "UNKNOWN"

        samples = self.profile.get(
            "samples",
            {},
        )

        try:
            center = samples["CENTER"]
            left = samples["GAZE_LEFT"]
            right = samples["GAZE_RIGHT"]
            up = samples["GAZE_UP"]
            down = samples["GAZE_DOWN"]
        except KeyError:
            return "UNKNOWN"

        # --------------------------------------------------------
        # Boundaries are halfway between CENTER and each
        # calibrated direction.
        # --------------------------------------------------------

        left_boundary = (center["gaze_x"] + left["gaze_x"]) / 2.0

        right_boundary = (center["gaze_x"] + right["gaze_x"]) / 2.0

        up_boundary = (center["gaze_y"] + up["gaze_y"]) / 2.0

        down_boundary = (center["gaze_y"] + down["gaze_y"]) / 2.0

        scores = {}

        if gaze_x <= left_boundary:
            scores["LEFT"] = (left_boundary - gaze_x) / max(
                abs(center["gaze_x"] - left["gaze_x"]),
                0.01,
            )

        if gaze_x >= right_boundary:
            scores["RIGHT"] = (gaze_x - right_boundary) / max(
                abs(right["gaze_x"] - center["gaze_x"]),
                0.01,
            )

        if gaze_y <= up_boundary:
            scores["UP"] = (up_boundary - gaze_y) / max(
                abs(center["gaze_y"] - up["gaze_y"]),
                0.01,
            )

        if gaze_y >= down_boundary:
            scores["DOWN"] = (gaze_y - down_boundary) / max(
                abs(down["gaze_y"] - center["gaze_y"]),
                0.01,
            )

        if not scores:
            return "CENTER"

        return max(
            scores,
            key=scores.get,
        )

    # ============================================================
    # HEAD CLASSIFICATION
    # ============================================================

    def _classify_head(
        self,
        head_state,
    ):
        """
        Classify head orientation using the student's calibration
        profile.
        """

        if not self.completed or self.profile is None:
            return "UNKNOWN"

        if not isinstance(
            head_state,
            dict,
        ):
            return "UNKNOWN"

        if not head_state.get(
            "valid",
            False,
        ):
            return "UNKNOWN"

        yaw = head_state.get("yaw")

        pitch = head_state.get("pitch")

        if not self._is_number(yaw) or not self._is_number(pitch):
            return "UNKNOWN"

        samples = self.profile.get(
            "samples",
            {},
        )

        try:
            center = samples["CENTER"]
            left = samples["HEAD_LEFT"]
            right = samples["HEAD_RIGHT"]
            up = samples["HEAD_UP"]
            down = samples["HEAD_DOWN"]
        except KeyError:
            return "UNKNOWN"

        left_boundary = (center["yaw"] + left["yaw"]) / 2.0

        right_boundary = (center["yaw"] + right["yaw"]) / 2.0

        up_boundary = (center["pitch"] + up["pitch"]) / 2.0

        down_boundary = (center["pitch"] + down["pitch"]) / 2.0

        scores = {}

        if yaw <= left_boundary:
            scores["LEFT"] = (left_boundary - yaw) / max(
                abs(center["yaw"] - left["yaw"]),
                1.0,
            )

        if yaw >= right_boundary:
            scores["RIGHT"] = (yaw - right_boundary) / max(
                abs(right["yaw"] - center["yaw"]),
                1.0,
            )

        if pitch <= up_boundary:
            scores["UP"] = (up_boundary - pitch) / max(
                abs(center["pitch"] - up["pitch"]),
                1.0,
            )

        if pitch >= down_boundary:
            scores["DOWN"] = (pitch - down_boundary) / max(
                abs(down["pitch"] - center["pitch"]),
                1.0,
            )

        if not scores:
            return "CENTER"

        return max(
            scores,
            key=scores.get,
        )

    # ============================================================
    # RUNTIME DIRECTION STATE
    # ============================================================

    def _update_runtime_direction(
        self,
        key,
        direction,
    ):
        """
        Maintain sustained gaze/head-away timing.

        CENTER does not immediately cancel an active away state;
        recovery_grace_seconds is respected.
        """

        state = self.runtime_states[key]

        now = time.monotonic()

        if direction in {
            "LEFT",
            "RIGHT",
            "UP",
            "DOWN",
        }:
            state["last_active_at"] = now

            if state["started_at"] is None:
                state["started_at"] = now

            state["last_direction"] = direction

            return {
                "direction": direction,
                "away": True,
                "away_duration": (now - state["started_at"]),
            }

        if direction == "CENTER":
            if (
                state["started_at"] is not None
                and state["last_active_at"] is not None
                and (now - state["last_active_at"]) < self.recovery_grace_seconds
            ):
                return {
                    "direction": (state["last_direction"]),
                    "away": True,
                    "away_duration": (now - state["started_at"]),
                }

            state["started_at"] = None
            state["last_active_at"] = None
            state["last_direction"] = "CENTER"

            return {
                "direction": "CENTER",
                "away": False,
                "away_duration": 0.0,
            }

        return {
            "direction": "UNKNOWN",
            "away": False,
            "away_duration": 0.0,
        }

    # ============================================================
    # RUNTIME STATUS
    # ============================================================

    def runtime_status(
        self,
        gaze_state,
        head_state,
    ):
        """
        Produce the runtime gaze/head status after calibration.
        """

        gaze_direction = self._classify_gaze(gaze_state)

        head_direction = self._classify_head(head_state)

        gaze = self._update_runtime_direction(
            "gaze",
            gaze_direction,
        )

        head = self._update_runtime_direction(
            "head",
            head_direction,
        )

        return {
            "gaze_direction": (gaze["direction"]),
            "gaze_away": (gaze["away"]),
            "gaze_away_duration": (gaze["away_duration"]),
            "head_direction": (head["direction"]),
            "head_away": (head["away"]),
            "head_away_duration": (head["away_duration"]),
        }

    # ============================================================
    # RESET RUNTIME STATE
    # ============================================================

    def reset_runtime(self):
        """
        Reset only runtime direction tracking.

        Calibration profile remains intact.
        """

        for state in self.runtime_states.values():
            state["started_at"] = None
            state["last_active_at"] = None
            state["last_direction"] = "CENTER"

    # ============================================================
    # COMPLETE CALIBRATION RESET
    # ============================================================

    def reset(
        self,
        delete_file=True,
    ):
        """
        Completely reset calibration.

        By default the saved JSON profile is also deleted.
        """

        if delete_file and self.profile_path.exists():
            try:
                self.profile_path.unlink()
            except Exception as error:
                print("[CALIBRATION RESET ERROR] " f"{error}")

        self.profile = None
        self.completed = False

        self.stage_index = 0

        self.stage_started_at = time.monotonic()

        self.valid_started_at = None
        self.samples = []

        self.retry_count = 0
        self.retry_notice_until = 0.0

        self.reset_runtime()

        print("[CALIBRATION] Reset")
