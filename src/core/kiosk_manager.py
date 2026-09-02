import os
import shutil
import subprocess
import tempfile
import threading
import time
import ctypes

from pathlib import Path
from ctypes import wintypes

from src.core.notification_manager import NotificationManager

DESKTOP_READOBJECTS = 0x0001
UOI_NAME = 2


class KioskManager:

    def __init__(self):

        self.process = None

        self.profile_path = None

        self.security_violation_detected = False

        self.security_violation_reason = None

        self.monitor_thread = None

        self.monitor_stop_event = threading.Event()

        self.notification_manager = NotificationManager()

        self.user32 = None

        if os.name == "nt":

            self.user32 = ctypes.WinDLL("user32", use_last_error=True)

            self.user32.OpenInputDesktop.argtypes = [
                wintypes.DWORD,
                wintypes.BOOL,
                wintypes.DWORD,
            ]

            self.user32.OpenInputDesktop.restype = wintypes.HANDLE

            self.user32.GetUserObjectInformationW.argtypes = [
                wintypes.HANDLE,
                ctypes.c_int,
                wintypes.LPVOID,
                wintypes.DWORD,
                ctypes.POINTER(wintypes.DWORD),
            ]

            self.user32.GetUserObjectInformationW.restype = wintypes.BOOL

            self.user32.CloseDesktop.argtypes = [wintypes.HANDLE]

            self.user32.CloseDesktop.restype = wintypes.BOOL

    def _find_edge(self):

        possible_paths = [
            Path(os.environ.get("PROGRAMFILES(X86)", ""))
            / "Microsoft"
            / "Edge"
            / "Application"
            / "msedge.exe",
            Path(os.environ.get("PROGRAMFILES", ""))
            / "Microsoft"
            / "Edge"
            / "Application"
            / "msedge.exe",
            Path(os.environ.get("LOCALAPPDATA", ""))
            / "Microsoft"
            / "Edge"
            / "Application"
            / "msedge.exe",
        ]

        for path in possible_paths:

            if path.exists():

                return str(path)

        return None

    def _create_session_profile(self):

        base_path = (
            Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir()))
            / "SkolariqProctor"
            / "Sessions"
        )

        base_path.mkdir(parents=True, exist_ok=True)

        self.profile_path = tempfile.mkdtemp(prefix="session_", dir=str(base_path))

        print("[PROCTOR] Browser profile:", self.profile_path)

        return self.profile_path

    def _destroy_session_profile(self):

        if not self.profile_path:

            return

        print("[PROCTOR] Destroying browser profile...")

        try:

            shutil.rmtree(self.profile_path, ignore_errors=True)

        except Exception as error:

            print("[PROCTOR] Profile cleanup error:", error)

        finally:

            self.profile_path = None

    def _show_security_notification(self):

        print("[PROCTOR] Triggering security notification...")

        try:

            self.notification_manager.send(
                title="Skolariq Secure Exam",
                message=(
                    "Your exam session was interrupted. "
                    "Please resume your exam soon."
                ),
            )

            print("[PROCTOR] Notification triggered.")

        except Exception as error:

            print("[PROCTOR] Notification failed:", error)

    def _get_input_desktop_name(self):

        if os.name != "nt":

            return None

        if not self.user32:

            return None

        desktop = self.user32.OpenInputDesktop(0, False, DESKTOP_READOBJECTS)

        if not desktop:

            return None

        try:

            buffer = ctypes.create_unicode_buffer(256)

            required_size = wintypes.DWORD(0)

            success = self.user32.GetUserObjectInformationW(
                desktop,
                UOI_NAME,
                buffer,
                ctypes.sizeof(buffer),
                ctypes.byref(required_size),
            )

            if not success:

                return None

            return buffer.value

        finally:

            self.user32.CloseDesktop(desktop)

    def _is_default_desktop_active(self):

        if os.name != "nt":

            return True

        try:

            desktop_name = self._get_input_desktop_name()

            if not desktop_name:

                return False

            return desktop_name.lower() == "default"

        except Exception as error:

            print("[PROCTOR] Desktop check error:", error)

            return False

    def _kill_edge_process_tree(self):

        if not self.process:

            return

        print("[PROCTOR] Killing kiosk browser...")

        try:

            subprocess.run(
                [
                    "taskkill",
                    "/PID",
                    str(self.process.pid),
                    "/T",
                    "/F",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                creationflags=(subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0),
            )

        except Exception as error:

            print("[PROCTOR] Browser kill error:", error)

    def _security_monitor(self):

        time.sleep(2)

        failed_checks = 0

        print("[PROCTOR] Security monitor started.")

        while not self.monitor_stop_event.is_set():

            if self.process and self.process.poll() is not None:

                return

            if self._is_default_desktop_active():

                failed_checks = 0

            else:

                failed_checks += 1

                print("[PROCTOR] Non-default desktop detected:", failed_checks)

                if failed_checks >= 2:

                    self.security_violation_detected = True

                    self.security_violation_reason = "Secure desktop detected"

                    print("[PROCTOR] Secure desktop detected.")

                    print("[PROCTOR] Waiting for user to return...")

                    while not self._is_default_desktop_active():

                        time.sleep(1)

                    print("[PROCTOR] User returned to desktop.")

                    self._show_security_notification()

                    time.sleep(5)

                    self._kill_edge_process_tree()

                    self._destroy_session_profile()

                    self.monitor_stop_event.set()

                    return

            time.sleep(0.5)

    def _start_security_monitor(self):

        self.monitor_stop_event.clear()

        self.monitor_thread = threading.Thread(
            target=self._security_monitor, daemon=True
        )

        self.monitor_thread.start()

    def start(self, url):

        edge_path = self._find_edge()

        if not edge_path:

            raise RuntimeError("Microsoft Edge was not found.")

        self.security_violation_detected = False

        self.security_violation_reason = None

        profile_path = self._create_session_profile()

        command = [
            edge_path,
            f"--user-data-dir={profile_path}",
            "--kiosk",
            url,
            "--edge-kiosk-type=fullscreen",
            "--no-first-run",
            "--no-default-browser-check",
        ]

        print("[PROCTOR] Starting kiosk...")

        self.process = subprocess.Popen(command)

        self._start_security_monitor()

        return self.process

    def stop(self):

        print("[PROCTOR] Stopping kiosk manager...")

        self.monitor_stop_event.set()

        self._kill_edge_process_tree()

        if self.monitor_thread and self.monitor_thread.is_alive():

            self.monitor_thread.join(timeout=2)

        self.monitor_thread = None

        self.process = None

        self._destroy_session_profile()
