import socketio
import threading


class ProctorSocketClient:

    def __init__(self, server_url, token, proctor_session_id, test_id, schedule_id):
        self.server_url = server_url
        self.token = token

        self.proctor_session_id = str(proctor_session_id)

        self.test_id = int(test_id)
        self.schedule_id = int(schedule_id)

        self.connected = False

        self.exam_completed_callback = None

        self.connection_thread = None

        self.sio = socketio.Client(
            reconnection=True,
            reconnection_attempts=5,
            reconnection_delay=3,
            request_timeout=10,
        )

        self._register_events()

    def _register_events(self):

        @self.sio.event
        def connect():

            self.connected = True

            print("[SOCKET] Connected to assessment server.")

            self.sio.emit(
                "join-proctor-session",
                {
                    "proctor_session_id": str(self.proctor_session_id),
                    "test_id": int(self.test_id),
                    "schedule_id": int(self.schedule_id),
                },
            )

        @self.sio.event
        def disconnect():

            self.connected = False

            print("[SOCKET] Disconnected.")

        @self.sio.on("proctor-session-joined")
        def session_joined(data):

            print("[SOCKET] Joined room:", data)

        @self.sio.on("proctor-session-error")
        def session_error(data):

            print("[SOCKET ERROR]", data)

        @self.sio.on("exam-completed")
        def exam_completed(data):

            print("[SOCKET] Exam completed event received:", data)

            if self.exam_completed_callback:

                try:

                    self.exam_completed_callback(data)

                except Exception as error:

                    print("[SOCKET] Completion callback error:", error)

    def connect(self):

        try:

            self.sio.connect(
                self.server_url,
                auth={"token": self.token},
                transports=["websocket"],
                wait_timeout=10,
            )

        except Exception as error:

            print("[SOCKET] Connection failed:", error)

    def start_background(self):

        if self.connection_thread and self.connection_thread.is_alive():
            return

        self.connection_thread = threading.Thread(target=self.connect, daemon=True)

        self.connection_thread.start()

    def notify_proctor_terminated(self):

        try:

            if not self.sio.connected:

                print(
                    "[SOCKET] Cannot send termination event. "
                    "Socket is not connected."
                )

                return False

            self.sio.emit(
                "proctor-process-terminated",
                {
                    "proctor_session_id": str(self.proctor_session_id),
                    "test_id": int(self.test_id),
                    "schedule_id": int(self.schedule_id),
                },
            )

            print("[SOCKET] Proctor termination event sent.")

            return True

        except Exception as error:

            print("[SOCKET] Failed to send termination event:", error)

            return False

    def disconnect(self):

        try:

            if self.sio.connected:

                self.sio.disconnect()

        except Exception as error:

            print("[SOCKET] Disconnect error:", error)
