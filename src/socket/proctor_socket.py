import socketio
import threading
from datetime import datetime, timezone


class ProctorSocketClient:
    """
    Socket.IO client used by the native Skolariq Proctor application.

    Existing responsibilities preserved:
    - Connect to Node Socket.IO server.
    - Authenticate using the proctor JWT.
    - Join the proctor session room.
    - Receive exam-completed events.
    - Notify Node when the proctor process terminates.
    - Emit confirmed proctor violations.

    Diagnostic additions:
    - Log connection attempt.
    - Log successful connection.
    - Log room join emission.
    - Log successful room join acknowledgement.
    - Log room join failure.
    - Log violation emit attempt.
    - Log exact outgoing violation payload.
    - Log acknowledgement from Node.
    """

    VIOLATION_MESSAGES = {
        "NO_FACE": (
            "Your face is not clearly visible. " "Please stay in front of the camera."
        ),
        "MULTIPLE_FACES": (
            "Multiple faces were detected. " "Please make sure only you are visible."
        ),
        "GAZE_AWAY": ("Please keep your attention on the assessment screen."),
        "HEAD_AWAY": ("Please keep your face directed toward the assessment screen."),
        "PHONE_DETECTED": (
            "A mobile phone was detected. "
            "Please keep phones away during the assessment."
        ),
        "BOOK_DETECTED": (
            "A book or study material was detected. "
            "Please remove unauthorized materials."
        ),
        "EXTRA_PERSON": (
            "Another person appears to be present. "
            "Please make sure you are alone during the assessment."
        ),
        "BODY_LEAN_LEFT": ("Please remain properly positioned in front of the camera."),
        "BODY_LEAN_RIGHT": (
            "Please remain properly positioned in front of the camera."
        ),
        "LEFT_ARM_RAISED": (
            "Unusual movement was detected. "
            "Please remain properly positioned during the assessment."
        ),
        "RIGHT_ARM_RAISED": (
            "Unusual movement was detected. "
            "Please remain properly positioned during the assessment."
        ),
        "UNUSUAL_ARM_MOVEMENT": (
            "Unusual movement was detected. " "Please remain focused on the assessment."
        ),
        "UPPER_BODY_NOT_VISIBLE": (
            "Please adjust your position so that you remain clearly "
            "visible to the camera."
        ),
        "CAMERA_OFF": (
            "Your camera appears to be unavailable. "
            "Please keep the camera active during the assessment."
        ),
        "MIC_OFF": (
            "Your microphone appears to be unavailable. "
            "Please keep the microphone active during the assessment."
        ),
        "CAMERA_ERROR": (
            "There is a problem with your camera. " "Please check it immediately."
        ),
        "MIC_ERROR": (
            "There is a problem with your microphone. " "Please check it immediately."
        ),
    }

    VIOLATION_SEVERITIES = {
        "NO_FACE": "warning",
        "MULTIPLE_FACES": "violation",
        "GAZE_AWAY": "warning",
        "HEAD_AWAY": "warning",
        "PHONE_DETECTED": "violation",
        "BOOK_DETECTED": "violation",
        "EXTRA_PERSON": "violation",
        "BODY_LEAN_LEFT": "warning",
        "BODY_LEAN_RIGHT": "warning",
        "LEFT_ARM_RAISED": "warning",
        "RIGHT_ARM_RAISED": "warning",
        "UNUSUAL_ARM_MOVEMENT": "warning",
        "UPPER_BODY_NOT_VISIBLE": "warning",
        "CAMERA_OFF": "violation",
        "MIC_OFF": "warning",
        "CAMERA_ERROR": "violation",
        "MIC_ERROR": "warning",
    }

    def __init__(
        self,
        server_url,
        token,
        proctor_session_id,
        test_id,
        schedule_id,
    ):
        self.server_url = server_url
        self.token = token

        self.proctor_session_id = str(proctor_session_id)

        self.test_id = int(test_id)

        self.schedule_id = int(schedule_id)

        self.connected = False
        self.joined_room = False

        self.exam_completed_callback = None
        self.connection_thread = None

        self.sio = socketio.Client(
            reconnection=True,
            reconnection_attempts=5,
            reconnection_delay=3,
            request_timeout=10,
        )

        self._register_events()

    # ============================================================
    # DEBUG LOG HELPER
    # ============================================================

    def _log(
        self,
        message,
        data=None,
    ):
        """
        Centralized flushed logging.

        flush=True is intentional so logs appear immediately
        in the native application's terminal/debug console.
        """

        if data is None:
            print(
                message,
                flush=True,
            )
        else:
            print(
                message,
                data,
                flush=True,
            )

    # ============================================================
    # SOCKET EVENT REGISTRATION
    # ============================================================

    def _register_events(
        self,
    ):

        # ========================================================
        # CONNECTED
        # ========================================================

        @self.sio.event
        def connect():

            self.connected = True
            self.joined_room = False

            self._log(
                "[SOCKET][CONNECTED] Successfully connected to Node Socket.IO server.",
                {
                    "server_url": self.server_url,
                    "socket_id": self.sio.sid,
                    "proctor_session_id": self.proctor_session_id,
                    "test_id": self.test_id,
                    "schedule_id": self.schedule_id,
                },
            )

            join_payload = {
                "proctor_session_id": str(self.proctor_session_id),
                "test_id": int(self.test_id),
                "schedule_id": int(self.schedule_id),
            }

            self._log(
                "[SOCKET][JOIN EMIT] Emitting join-proctor-session:",
                join_payload,
            )

            try:

                self.sio.emit(
                    "join-proctor-session",
                    join_payload,
                )

                self._log(
                    "[SOCKET][JOIN EMIT QUEUED] join-proctor-session was sent to Socket.IO."
                )

            except Exception as error:

                self._log(
                    "[SOCKET][JOIN EMIT FAILED]",
                    {
                        "error": str(error),
                        "payload": join_payload,
                    },
                )

        # ========================================================
        # CONNECTION ERROR
        # ========================================================

        @self.sio.event
        def connect_error(
            data,
        ):

            self.connected = False
            self.joined_room = False

            self._log(
                "[SOCKET][CONNECT ERROR] Node Socket.IO connection failed/rejected:",
                data,
            )

        # ========================================================
        # DISCONNECT
        # ========================================================

        @self.sio.event
        def disconnect():

            self.connected = False
            self.joined_room = False

            self._log("[SOCKET][DISCONNECTED] Socket disconnected from Node server.")

        # ========================================================
        # ROOM JOIN SUCCESS
        # ========================================================

        @self.sio.on("proctor-session-joined")
        def session_joined(
            data,
        ):

            self.joined_room = True

            self._log(
                "[SOCKET][ROOM JOINED] Node confirmed proctor session room join:",
                data,
            )

            self._log(
                "[SOCKET][READY] Python proctor is now connected and joined to the proctor room.",
                {
                    "socket_connected": self.sio.connected,
                    "connected_flag": self.connected,
                    "joined_room": self.joined_room,
                    "proctor_session_id": self.proctor_session_id,
                    "test_id": self.test_id,
                    "schedule_id": self.schedule_id,
                },
            )

        # ========================================================
        # ROOM JOIN ERROR
        # ========================================================

        @self.sio.on("proctor-session-error")
        def session_error(
            data,
        ):

            self.joined_room = False

            self._log(
                "[SOCKET][ROOM JOIN ERROR] Node rejected proctor session room join:",
                data,
            )

        # ========================================================
        # VIOLATION ACKNOWLEDGEMENT
        # ========================================================
        #
        # Node sends this AFTER:
        #
        # socket.on("proctor-violation")
        #
        # has received and processed the Python event.
        #
        # Seeing this is strong confirmation that:
        #
        # Python -> Node
        #
        # worked successfully.
        # ========================================================

        @self.sio.on("proctor-violation-received")
        def violation_received(
            data,
        ):

            self._log(
                "[SOCKET][VIOLATION ACKNOWLEDGED] Node received the violation:",
                data,
            )

        # ========================================================
        # VIOLATION ERROR
        # ========================================================

        @self.sio.on("proctor-violation-error")
        def violation_error(
            data,
        ):

            self._log(
                "[SOCKET][VIOLATION REJECTED] Node rejected the violation:",
                data,
            )

        # ========================================================
        # ROOM-WIDE VIOLATION BROADCAST
        # ========================================================
        #
        # Node broadcasts proctor-violation to every socket in
        # the room, including Python itself.
        #
        # Therefore, after Node broadcasts successfully, Python
        # can receive its own normalized event back here.
        #
        # Seeing this confirms:
        #
        # Python
        #   ->
        # Node listener
        #   ->
        # Node room broadcast
        #   ->
        # room clients
        # ========================================================

        @self.sio.on("proctor-violation")
        def violation_broadcast(
            data,
        ):

            self._log(
                "[SOCKET][VIOLATION BROADCAST RECEIVED] Node broadcast the violation to the proctor room:",
                data,
            )

        # ========================================================
        # EXAM COMPLETED
        # ========================================================

        @self.sio.on("exam-completed")
        def exam_completed(
            data,
        ):

            self._log(
                "[SOCKET][EXAM COMPLETED] Event received:",
                data,
            )

            if self.exam_completed_callback:

                try:

                    self.exam_completed_callback(data)

                except Exception as error:

                    self._log(
                        "[SOCKET][EXAM COMPLETED CALLBACK ERROR]",
                        str(error),
                    )

    # ============================================================
    # CONNECTION
    # ============================================================

    def connect(
        self,
    ):

        self._log(
            "[SOCKET][CONNECT ATTEMPT] Attempting Node Socket.IO connection:",
            {
                "server_url": self.server_url,
                "proctor_session_id": self.proctor_session_id,
                "test_id": self.test_id,
                "schedule_id": self.schedule_id,
                "has_token": bool(self.token),
                "token_length": len(str(self.token)) if self.token else 0,
            },
        )

        try:

            self.sio.connect(
                self.server_url,
                auth={
                    "token": self.token,
                },
                transports=["websocket"],
                wait_timeout=10,
            )

            self._log(
                "[SOCKET][CONNECT CALL COMPLETE]",
                {
                    "sio_connected": self.sio.connected,
                    "connected_flag": self.connected,
                    "socket_id": self.sio.sid,
                },
            )

        except Exception as error:

            self.connected = False
            self.joined_room = False

            self._log(
                "[SOCKET][CONNECTION FAILED]",
                {
                    "server_url": self.server_url,
                    "error_type": type(error).__name__,
                    "error": str(error),
                },
            )

    # ============================================================
    # BACKGROUND CONNECTION
    # ============================================================

    def start_background(
        self,
    ):

        if self.connection_thread and self.connection_thread.is_alive():

            self._log("[SOCKET][BACKGROUND] Connection thread is already running.")

            return

        self._log("[SOCKET][BACKGROUND] Starting Socket.IO connection thread.")

        self.connection_thread = threading.Thread(
            target=self.connect,
            daemon=True,
        )

        self.connection_thread.start()

    # ============================================================
    # VIOLATION HELPERS
    # ============================================================

    def _normalize_event_type(
        self,
        event_type,
    ):

        return str(event_type or "").upper().strip()

    def _get_violation_message(
        self,
        event_type,
    ):

        normalized = self._normalize_event_type(event_type)

        return self.VIOLATION_MESSAGES.get(
            normalized,
            (
                "A proctoring issue was detected. "
                "Please remain properly positioned and focused "
                "on the assessment."
            ),
        )

    def _get_violation_severity(
        self,
        event_type,
    ):

        normalized = self._normalize_event_type(event_type)

        return self.VIOLATION_SEVERITIES.get(
            normalized,
            "warning",
        )

    # ============================================================
    # SEND PROCTOR VIOLATION
    # ============================================================

    def notify_proctor_violation(
        self,
        violation,
        message=None,
        severity=None,
    ):
        """
        Sends a confirmed/recorded anomaly to Node.

        This method provides detailed diagnostic output so we
        know whether:

        1. the method was reached;
        2. the socket was connected;
        3. the room had been joined;
        4. a valid violation existed;
        5. the Socket.IO emit was executed;
        6. Node acknowledged the event.
        """

        self._log(
            "[SOCKET][VIOLATION METHOD CALLED]",
            {
                "socket_connected": self.sio.connected,
                "connected_flag": self.connected,
                "joined_room": self.joined_room,
                "proctor_session_id": self.proctor_session_id,
            },
        )

        try:

            if not isinstance(
                violation,
                dict,
            ):

                self._log(
                    "[SOCKET][VIOLATION NOT SENT] Invalid violation payload:",
                    violation,
                )

                return False

            if not self.sio.connected:

                self._log(
                    "[SOCKET][VIOLATION NOT SENT] Socket.IO client is not connected.",
                    {
                        "connected_flag": self.connected,
                        "sio_connected": self.sio.connected,
                        "joined_room": self.joined_room,
                    },
                )

                return False

            event_type = self._normalize_event_type(
                violation.get("violation_type")
                or violation.get("event_type")
                or violation.get("type")
            )

            if not event_type:

                self._log(
                    "[SOCKET][VIOLATION NOT SENT] Violation type is missing.",
                    violation,
                )

                return False

            violation_metadata = violation.get("metadata")

            if not isinstance(
                violation_metadata,
                dict,
            ):

                violation_metadata = {}

            violation_metadata = dict(violation_metadata)

            file_path = violation.get("file_path")

            if file_path:

                violation_metadata["evidence_file_path"] = file_path

            client_captured_at = violation.get("client_captured_at")

            if not client_captured_at:

                client_captured_at = datetime.now(timezone.utc).isoformat()

            outgoing_message = message or self._get_violation_message(event_type)

            outgoing_severity = severity or self._get_violation_severity(event_type)

            confidence = violation_metadata.get("confidence")

            if confidence is None:

                confidence = violation_metadata.get("detection_confidence")

            payload = {
                "proctor_session_id": str(self.proctor_session_id),
                "test_id": int(self.test_id),
                "schedule_id": int(self.schedule_id),
                "event_type": event_type,
                "violation_type": event_type,
                "severity": str(outgoing_severity),
                "message": str(outgoing_message),
                "confidence": confidence,
                "timestamp": client_captured_at,
                "metadata": violation_metadata,
            }

            self._log(
                "[SOCKET][VIOLATION EMIT ATTEMPT] About to emit proctor-violation:",
                payload,
            )

            self.sio.emit(
                "proctor-violation",
                payload,
            )

            self._log(
                "[SOCKET][VIOLATION EMIT QUEUED] proctor-violation emitted through Socket.IO.",
                {
                    "event_type": event_type,
                    "proctor_session_id": self.proctor_session_id,
                    "test_id": self.test_id,
                    "schedule_id": self.schedule_id,
                    "joined_room": self.joined_room,
                },
            )

            return True

        except Exception as error:

            self._log(
                "[SOCKET][VIOLATION EMIT FAILED]",
                {
                    "error_type": type(error).__name__,
                    "error": str(error),
                },
            )

            return False

    # ============================================================
    # SEND ANOMALY MANAGER RESULT
    # ============================================================

    def notify_anomaly_result(
        self,
        anomaly_result,
    ):
        """
        Convenience method for AnomalyManager.update(...).

        Emits only when:

            captured == True

        and:

            api_violation exists.
        """

        self._log(
            "[SOCKET][ANOMALY RESULT RECEIVED]",
            {
                "is_dict": isinstance(anomaly_result, dict),
                "event_type": (
                    anomaly_result.get("event_type")
                    if isinstance(anomaly_result, dict)
                    else None
                ),
                "captured": (
                    anomaly_result.get("captured")
                    if isinstance(anomaly_result, dict)
                    else None
                ),
                "has_api_violation": (
                    isinstance(
                        anomaly_result.get("api_violation"),
                        dict,
                    )
                    if isinstance(anomaly_result, dict)
                    else False
                ),
            },
        )

        try:

            if not isinstance(
                anomaly_result,
                dict,
            ):

                return False

            if not anomaly_result.get("captured"):

                self._log("[SOCKET][ANOMALY NOT EMITTED] captured=False.")

                return False

            api_violation = anomaly_result.get("api_violation")

            if not isinstance(
                api_violation,
                dict,
            ):

                self._log("[SOCKET][ANOMALY NOT EMITTED] api_violation missing.")

                return False

            self._log(
                "[SOCKET][ANOMALY READY FOR SOCKET]",
                {
                    "violation_type": api_violation.get("violation_type"),
                    "client_captured_at": api_violation.get("client_captured_at"),
                },
            )

            return self.notify_proctor_violation(api_violation)

        except Exception as error:

            self._log(
                "[SOCKET][ANOMALY PROCESSING FAILED]",
                {
                    "error": str(error),
                },
            )

            return False

    # ============================================================
    # PROCTOR PROCESS TERMINATED
    # ============================================================

    def notify_proctor_terminated(
        self,
    ):

        try:

            if not self.sio.connected:

                self._log("[SOCKET][TERMINATION NOT SENT] Socket is not connected.")

                return False

            payload = {
                "proctor_session_id": str(self.proctor_session_id),
                "test_id": int(self.test_id),
                "schedule_id": int(self.schedule_id),
            }

            self.sio.emit(
                "proctor-process-terminated",
                payload,
            )

            self._log(
                "[SOCKET][TERMINATION SENT]",
                payload,
            )

            return True

        except Exception as error:

            self._log(
                "[SOCKET][TERMINATION FAILED]",
                str(error),
            )

            return False

    # ============================================================
    # DISCONNECT
    # ============================================================

    def disconnect(
        self,
    ):

        try:

            if self.sio.connected:

                self._log(
                    "[SOCKET][DISCONNECT REQUEST] Disconnecting Socket.IO client."
                )

                self.sio.disconnect()

        except Exception as error:

            self._log(
                "[SOCKET][DISCONNECT ERROR]",
                str(error),
            )
