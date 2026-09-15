import time

from src.config.settings import settings


class AnomalyManager:

    DEFAULT_RULE = {
        "duration": 0.0,
        "cooldown": 12.0,
        "recovery_grace": 0.0,
    }

    def __init__(self, evidence_store):
        if evidence_store is None:
            raise ValueError("AnomalyManager requires an evidence_store.")

        self.evidence_store = evidence_store

        self.rules = {
            "NO_FACE": {
                "duration": 0.0,
                "cooldown": settings.EVIDENCE_COOLDOWN_NO_FACE,
                "recovery_grace": 0.0,
            },
            "MULTIPLE_FACES": {
                "duration": 0.0,
                "cooldown": settings.EVIDENCE_COOLDOWN_MULTIPLE_FACES,
                "recovery_grace": 0.5,
            },
            "GAZE_AWAY": {
                "duration": 3.0,
                "cooldown": settings.EVIDENCE_COOLDOWN_GAZE_AWAY,
                "recovery_grace": 0.8,
            },
            "HEAD_AWAY": {
                "duration": 1.0,
                "cooldown": settings.EVIDENCE_COOLDOWN_HEAD_AWAY,
                "recovery_grace": 0.8,
            },
            "PHONE_DETECTED": {
                "duration": 1.0,
                "cooldown": settings.EVIDENCE_COOLDOWN_PHONE_DETECTED,
                "recovery_grace": 1.0,
            },
            "BOOK_DETECTED": {
                "duration": 1.0,
                "cooldown": settings.EVIDENCE_COOLDOWN_BOOK_DETECTED,
                "recovery_grace": 1.0,
            },
            "EXTRA_PERSON": {
                "duration": 1.0,
                "cooldown": settings.EVIDENCE_COOLDOWN_EXTRA_PERSON,
                "recovery_grace": 1.0,
            },
            "BODY_LEAN_LEFT": {
                "duration": 2.0,
                "cooldown": settings.EVIDENCE_COOLDOWN_BODY_LEAN_LEFT,
                "recovery_grace": 0.8,
            },
            "BODY_LEAN_RIGHT": {
                "duration": 2.0,
                "cooldown": settings.EVIDENCE_COOLDOWN_BODY_LEAN_RIGHT,
                "recovery_grace": 0.8,
            },
            "LEFT_ARM_RAISED": {
                "duration": 2.0,
                "cooldown": settings.EVIDENCE_COOLDOWN_LEFT_ARM_RAISED,
                "recovery_grace": 0.8,
            },
            "RIGHT_ARM_RAISED": {
                "duration": 2.0,
                "cooldown": settings.EVIDENCE_COOLDOWN_RIGHT_ARM_RAISED,
                "recovery_grace": 0.8,
            },
            "UNUSUAL_ARM_MOVEMENT": {
                "duration": 1.5,
                "cooldown": settings.EVIDENCE_COOLDOWN_UNUSUAL_ARM_MOVEMENT,
                "recovery_grace": 1.0,
            },
            "UPPER_BODY_NOT_VISIBLE": {
                "duration": 2.0,
                "cooldown": settings.EVIDENCE_COOLDOWN_UPPER_BODY_NOT_VISIBLE,
                "recovery_grace": 0.8,
            },
            "CAMERA_OFF": {
                "duration": 0.0,
                "cooldown": settings.EVIDENCE_COOLDOWN_CAMERA_OFF,
                "recovery_grace": 0.0,
            },
            "MIC_OFF": {
                "duration": 0.0,
                "cooldown": settings.EVIDENCE_COOLDOWN_MIC_OFF,
                "recovery_grace": 0.0,
            },
            "CAMERA_ERROR": {
                "duration": 0.0,
                "cooldown": settings.EVIDENCE_COOLDOWN_CAMERA_ERROR,
                "recovery_grace": 0.0,
            },
            "MIC_ERROR": {
                "duration": 0.0,
                "cooldown": settings.EVIDENCE_COOLDOWN_MIC_ERROR,
                "recovery_grace": 0.0,
            },
        }

        self.states = {}

        print("[ANOMALY] Manager initialized.")
        print(f"[ANOMALY] {len(self.rules)} anomaly rules loaded.")

    def _get_rule(self, event_type):
        return self.rules.get(
            event_type,
            self.DEFAULT_RULE,
        )

    def _get_state(self, event_type):
        if event_type not in self.states:
            self.states[event_type] = {
                "started_at": None,
                "last_active_at": None,
                "last_capture_at": None,
                "confirmed": False,
            }

        return self.states[event_type]

    def _reset_state(
        self,
        event_type,
        state,
    ):
        if state.get("confirmed"):
            print(f"[ANOMALY] RECOVERED {event_type}")

        state["started_at"] = None
        state["last_active_at"] = None
        state["confirmed"] = False

    def get_cooldown(
        self,
        event_type,
    ):
        event_type = str(event_type).upper().strip()

        rule = self._get_rule(event_type)

        try:
            cooldown = float(
                rule.get(
                    "cooldown",
                    12.0,
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            cooldown = 12.0

        return max(
            0.0,
            cooldown,
        )

    def get_required_duration(
        self,
        event_type,
    ):
        event_type = str(event_type).upper().strip()

        rule = self._get_rule(event_type)

        try:
            duration = float(
                rule.get(
                    "duration",
                    0.0,
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            duration = 0.0

        return max(
            0.0,
            duration,
        )

    def _get_cooldown_remaining(
        self,
        state,
        now,
        cooldown,
    ):
        last_capture_at = state.get("last_capture_at")

        if last_capture_at is None:
            return 0.0

        elapsed = now - last_capture_at

        return max(
            0.0,
            cooldown - elapsed,
        )

    def _build_api_violation(
        self,
        event_type,
        evidence,
        event_metadata,
    ):
        if not evidence:
            return None

        file_path = evidence.get("file_path")

        if not file_path:
            file_path = evidence.get("image_path")

        metadata_path = evidence.get("metadata_path")

        event_payload = evidence.get("event")

        client_captured_at = None

        if isinstance(
            event_payload,
            dict,
        ):
            client_captured_at = event_payload.get("captured_at")

        if not client_captured_at:
            client_captured_at = evidence.get("client_captured_at")

        violation_metadata = dict(event_metadata or {})

        if metadata_path:
            violation_metadata["evidence_metadata_path"] = metadata_path

        return {
            "violation_type": event_type,
            "client_captured_at": client_captured_at,
            "metadata": violation_metadata,
            "file_path": file_path,
        }

    def update(
        self,
        event_type,
        active,
        frame,
        metadata=None,
    ):
        event_type = str(event_type).upper().strip()

        if not event_type:
            return {
                "event_type": "",
                "active": False,
                "confirmed": False,
                "captured": False,
                "duration": 0.0,
                "cooldown": 0.0,
                "cooldown_remaining": 0.0,
                "evidence": None,
                "api_violation": None,
            }

        active = bool(active)

        rule = self._get_rule(event_type)

        required_duration = self.get_required_duration(event_type)

        cooldown = self.get_cooldown(event_type)

        try:
            recovery_grace = float(
                rule.get(
                    "recovery_grace",
                    0.0,
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            recovery_grace = 0.0

        recovery_grace = max(
            0.0,
            recovery_grace,
        )

        state = self._get_state(event_type)

        now = time.monotonic()

        if active:
            state["last_active_at"] = now

            if state["started_at"] is None:
                state["started_at"] = now

        else:
            if state["started_at"] is None:
                return {
                    "event_type": event_type,
                    "active": False,
                    "confirmed": False,
                    "captured": False,
                    "duration": 0.0,
                    "cooldown": cooldown,
                    "cooldown_remaining": (
                        self._get_cooldown_remaining(
                            state,
                            now,
                            cooldown,
                        )
                    ),
                    "evidence": None,
                    "api_violation": None,
                }

            last_active_at = state.get("last_active_at")

            if last_active_at is not None and (now - last_active_at < recovery_grace):
                active = True

            else:
                self._reset_state(
                    event_type,
                    state,
                )

                return {
                    "event_type": event_type,
                    "active": False,
                    "confirmed": False,
                    "captured": False,
                    "duration": 0.0,
                    "cooldown": cooldown,
                    "cooldown_remaining": (
                        self._get_cooldown_remaining(
                            state,
                            now,
                            cooldown,
                        )
                    ),
                    "evidence": None,
                    "api_violation": None,
                }

        started_at = state.get("started_at")

        if started_at is None:
            duration = 0.0
        else:
            duration = max(
                0.0,
                now - started_at,
            )

        if duration < required_duration:
            return {
                "event_type": event_type,
                "active": True,
                "confirmed": False,
                "captured": False,
                "duration": duration,
                "required_duration": required_duration,
                "cooldown": cooldown,
                "cooldown_remaining": (
                    self._get_cooldown_remaining(
                        state,
                        now,
                        cooldown,
                    )
                ),
                "evidence": None,
                "api_violation": None,
            }

        if not state["confirmed"]:
            state["confirmed"] = True

            print(f"[ANOMALY] DETECTED " f"{event_type} " f"| duration={duration:.2f}s")

        cooldown_remaining = self._get_cooldown_remaining(
            state,
            now,
            cooldown,
        )

        if cooldown_remaining > 0.0:
            return {
                "event_type": event_type,
                "active": True,
                "confirmed": True,
                "captured": False,
                "duration": duration,
                "required_duration": required_duration,
                "cooldown": cooldown,
                "cooldown_remaining": cooldown_remaining,
                "evidence": None,
                "api_violation": None,
            }

        event_metadata = dict(metadata or {})

        event_metadata["event_duration_seconds"] = round(
            duration,
            2,
        )

        event_metadata["required_duration_seconds"] = round(
            required_duration,
            2,
        )

        event_metadata["evidence_cooldown_seconds"] = round(
            cooldown,
            2,
        )

        event_metadata["recovery_grace_seconds"] = round(
            recovery_grace,
            2,
        )

        try:
            evidence = self.evidence_store.capture(
                frame=frame,
                event_type=event_type,
                metadata=event_metadata,
            )

        except Exception as error:
            print(
                f"[ANOMALY] Evidence capture " f"failed for {event_type}: " f"{error}"
            )

            return {
                "event_type": event_type,
                "active": True,
                "confirmed": True,
                "captured": False,
                "duration": duration,
                "required_duration": required_duration,
                "cooldown": cooldown,
                "cooldown_remaining": cooldown,
                "evidence": None,
                "api_violation": None,
                "error": str(error),
            }

        if evidence is not None:
            state["last_capture_at"] = now

            api_violation = self._build_api_violation(
                event_type=event_type,
                evidence=evidence,
                event_metadata=event_metadata,
            )

            print(f"[ANOMALY] EVIDENCE CAPTURED " f"{event_type}")

            return {
                "event_type": event_type,
                "active": True,
                "confirmed": True,
                "captured": True,
                "duration": duration,
                "required_duration": required_duration,
                "cooldown": cooldown,
                "cooldown_remaining": 0.0,
                "evidence": evidence,
                "api_violation": api_violation,
            }

        return {
            "event_type": event_type,
            "active": True,
            "confirmed": True,
            "captured": False,
            "duration": duration,
            "required_duration": required_duration,
            "cooldown": cooldown,
            "cooldown_remaining": cooldown,
            "evidence": None,
            "api_violation": None,
        }

    def get_cooldown_remaining(
        self,
        event_type,
    ):
        event_type = str(event_type).upper().strip()

        state = self.states.get(event_type)

        if state is None:
            return 0.0

        now = time.monotonic()

        cooldown = self.get_cooldown(event_type)

        return self._get_cooldown_remaining(
            state,
            now,
            cooldown,
        )

    def update_many(
        self,
        anomalies,
        frame,
        metadata=None,
    ):
        results = {}

        shared_metadata = dict(metadata or {})

        if not isinstance(
            anomalies,
            dict,
        ):
            return results

        for (
            event_type,
            active,
        ) in anomalies.items():

            event_metadata = {}

            possible_event_metadata = shared_metadata.get(event_type)

            if isinstance(
                possible_event_metadata,
                dict,
            ):
                event_metadata.update(possible_event_metadata)
            else:
                event_metadata.update(shared_metadata)

            normalized_event_type = str(event_type).upper().strip()

            results[normalized_event_type] = self.update(
                event_type=event_type,
                active=active,
                frame=frame,
                metadata=event_metadata,
            )

        return results

    def reset_event(
        self,
        event_type,
    ):
        event_type = str(event_type).upper().strip()

        state = self.states.get(event_type)

        if state is None:
            return

        self._reset_state(
            event_type,
            state,
        )

    def reset_all(
        self,
    ):
        for (
            event_type,
            state,
        ) in list(self.states.items()):
            self._reset_state(
                event_type,
                state,
            )

        self.states.clear()

        print("[ANOMALY] All anomaly states reset.")

    def get_state(
        self,
        event_type,
    ):
        event_type = str(event_type).upper().strip()

        state = self.states.get(event_type)

        if state is None:
            return {
                "started_at": None,
                "last_active_at": None,
                "last_capture_at": None,
                "confirmed": False,
            }

        return dict(state)

    def get_all_states(
        self,
    ):
        return {event_type: dict(state) for (event_type, state) in self.states.items()}

    def close(
        self,
    ):
        self.reset_all()

        print("[ANOMALY] Manager closed.")
