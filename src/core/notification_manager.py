import platform
import shutil
import subprocess
import ctypes


class NotificationManager:

    def __init__(self):

        self.system = platform.system()

    def send(self, title, message):

        try:

            print("[NOTIFICATION] OS detected:", self.system)

            if self.system == "Windows":

                return self._windows_notification(title, message)

            elif self.system == "Darwin":

                return self._mac_notification(title, message)

            elif self.system == "Linux":

                return self._linux_notification(title, message)

            else:

                print("[NOTIFICATION] Unsupported OS:", self.system)

                return False

        except Exception as error:

            print("[NOTIFICATION ERROR]", error)

            return False

    def _windows_notification(self, title, message):

        try:

            print("[WINDOWS NOTIFICATION] Trying toast...")

            try:

                from plyer import notification

                notification.notify(
                    title=str(title),
                    message=str(message),
                    timeout=8,
                )

                print("[WINDOWS NOTIFICATION] Toast call completed.")

                return True

            except Exception as toast_error:

                print("[WINDOWS NOTIFICATION] Toast failed:", toast_error)

            print("[WINDOWS NOTIFICATION] Using native popup fallback...")

            ctypes.windll.user32.MessageBoxW(0, str(message), str(title), 0x40)

            print("[WINDOWS NOTIFICATION] Native popup completed.")

            return True

        except Exception as error:

            print("[WINDOWS NOTIFICATION ERROR]", error)

            return False

    def _mac_notification(self, title, message):

        try:

            safe_title = str(title).replace('"', '\\"')

            safe_message = str(message).replace('"', '\\"')

            script = (
                f'display notification "{safe_message}" ' f'with title "{safe_title}"'
            )

            result = subprocess.run(
                [
                    "osascript",
                    "-e",
                    script,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )

            print("[MAC NOTIFICATION] Exit code:", result.returncode)

            return result.returncode == 0

        except Exception as error:

            print("[MAC NOTIFICATION ERROR]", error)

            return False

    def _linux_notification(self, title, message):

        try:

            if not shutil.which("notify-send"):

                print("[LINUX NOTIFICATION] notify-send missing.")

                return False

            result = subprocess.run(
                [
                    "notify-send",
                    str(title),
                    str(message),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )

            print("[LINUX NOTIFICATION] Exit code:", result.returncode)

            return result.returncode == 0

        except Exception as error:

            print("[LINUX NOTIFICATION ERROR]", error)

            return False
