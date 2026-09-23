import os
import platform
import threading
from datetime import datetime, timezone

import psutil


class ProcessMonitor:
    WINDOWS = "Windows"
    MACOS = "Darwin"
    LINUX = "Linux"

    OS_BROWSER_PROCESS_NAMES = {
        WINDOWS: {
            "chrome.exe",
            "comet.exe",
            "msedge.exe",
            "firefox.exe",
            "brave.exe",
            "vivaldi.exe",
            "opera.exe",
            "opera_gx.exe",
            "chromium.exe",
            "iexplore.exe",
            "arc.exe",
            "duckduckgo.exe",
        },
        MACOS: {
            "safari",
            "google chrome",
            "microsoft edge",
            "firefox",
            "brave browser",
            "vivaldi",
            "opera",
            "chromium",
            "comet",
            "arc",
            "duckduckgo",
        },
        LINUX: {
            "chrome",
            "google-chrome",
            "google-chrome-stable",
            "chromium",
            "chromium-browser",
            "firefox",
            "firefox-esr",
            "brave",
            "brave-browser",
            "vivaldi",
            "vivaldi-bin",
            "opera",
            "opera-developer",
            "microsoft-edge",
            "microsoft-edge-stable",
            "comet",
        },
    }

    OS_REMOTE_ACCESS_PROCESS_NAMES = {
        WINDOWS: {
            "anydesk.exe",
            "teamviewer.exe",
            "teamviewer_desktop.exe",
            "teamviewer_remote_control.exe",
            "teamviewer_service.exe",
            "rustdesk.exe",
            "rustdesk_service.exe",
            "remoting_host.exe",
            "chrome_remote_desktop.exe",
            "mstsc.exe",
            "msrdc.exe",
            "rdclient.exe",
            "msra.exe",
            "quickassist.exe",
            "parsec.exe",
            "parsecd.exe",
            "logmein.exe",
            "logmein123.exe",
            "logmeinrescue.exe",
            "lmi_rescue.exe",
            "gotoassist.exe",
            "g2a-rs_customer.exe",
            "g2a-rs_support.exe",
            "screenconnect.clientservice.exe",
            "screenconnect.windowsclient.exe",
            "connectwisecontrol.client.exe",
            "splashtopremote.exe",
            "srmanager.exe",
            "strwinclt.exe",
            "tightvnc.exe",
            "tvnserver.exe",
            "tvnviewer.exe",
            "winvnc.exe",
            "vncserver.exe",
            "vncviewer.exe",
            "ultravnc.exe",
            "uvnc_service.exe",
            "remotepc.exe",
            "dwagent.exe",
            "dwservice.exe",
            "meshagent.exe",
            "aeroadmin.exe",
            "supremo.exe",
            "supremosystem.exe",
            "zohoassist.exe",
            "bomgar-scc.exe",
            "rutserver.exe",
            "rutview.exe",
        },
        MACOS: {
            "anydesk",
            "teamviewer",
            "teamviewer_desktop",
            "teamviewer_service",
            "rustdesk",
            "remoting_host",
            "chrome remote desktop host",
            "microsoft remote desktop",
            "windows app",
            "parsec",
            "splashtop business",
            "splashtop streamer",
            "vnc viewer",
            "vnc server",
            "jump desktop",
            "jump desktop connect",
            "dwagent",
            "meshagent",
            "screenconnect client",
            "connectwise control",
        },
        LINUX: {
            "anydesk",
            "teamviewer",
            "teamviewerd",
            "rustdesk",
            "remoting_host",
            "chrome-remote-desktop",
            "remmina",
            "xfreerdp",
            "wlfreerdp",
            "freerdp",
            "krdc",
            "vinagre",
            "x11vnc",
            "tightvncserver",
            "xtigervnc",
            "tigervncserver",
            "vncserver",
            "vncviewer",
            "xrdp",
            "xrdp-sesman",
            "parsec",
            "parsecd",
            "dwagent",
            "meshagent",
            "sunshine",
        },
    }

    OS_SCREEN_SHARING_PROCESS_NAMES = {
        WINDOWS: {
            "cpthost.exe",
            "zoomsharingservice.exe",
            "zoomshare.exe",
            "screenshare.exe",
            "screen_share.exe",
            "sharingservice.exe",
        },
        MACOS: {
            "screen sharing",
            "zoomsharingservice",
            "zoomshare",
            "screenshare",
            "screen_share",
            "sharingservice",
        },
        LINUX: {
            "zoomsharingservice",
            "zoomshare",
            "screenshare",
            "screen_share",
            "sharingservice",
        },
    }

    OS_PROTECTED_SYSTEM_PROCESS_NAMES = {
        WINDOWS: {
            "system",
            "system idle process",
            "registry",
            "memory compression",
            "secure system",
            "smss.exe",
            "csrss.exe",
            "wininit.exe",
            "winlogon.exe",
            "services.exe",
            "lsass.exe",
            "svchost.exe",
            "fontdrvhost.exe",
            "dwm.exe",
            "explorer.exe",
            "sihost.exe",
            "taskhostw.exe",
            "ctfmon.exe",
            "spoolsv.exe",
            "audiodg.exe",
            "wudfhost.exe",
            "searchhost.exe",
            "startmenuexperiencehost.exe",
            "shellexperiencehost.exe",
        },
        MACOS: {
            "kernel_task",
            "launchd",
            "windowserver",
            "loginwindow",
            "systemuiserver",
            "controlcenter",
            "dock",
            "finder",
            "cfprefsd",
            "coreaudiod",
            "securityd",
            "opendirectoryd",
        },
        LINUX: {
            "systemd",
            "init",
            "kthreadd",
            "dbus-daemon",
            "networkmanager",
            "xorg",
            "xwayland",
            "gnome-shell",
            "plasmashell",
            "pipewire",
            "wireplumber",
            "pulseaudio",
        },
    }

    OS_REMOTE_ACCESS_PATH_KEYWORDS = {
        WINDOWS: {
            "\\anydesk\\",
            "\\teamviewer\\",
            "\\rustdesk\\",
            "\\parsec\\",
            "\\splashtop\\",
            "\\screenconnect\\",
            "\\connectwise control\\",
            "\\chrome remote desktop\\",
            "\\dwagent\\",
        },
        MACOS: {
            "/anydesk.app/",
            "/teamviewer.app/",
            "/rustdesk.app/",
            "/parsec.app/",
            "/splashtop",
            "/chrome remote desktop",
            "/jump desktop",
            "/connectwise control",
            "/dwagent",
        },
        LINUX: {
            "/anydesk",
            "/teamviewer",
            "/rustdesk",
            "/parsec",
            "/remmina",
            "/xrdp",
            "/tigervnc",
            "/tightvnc",
            "/x11vnc",
            "/dwagent",
        },
    }

    OS_SCREEN_SHARING_PATH_KEYWORDS = {
        WINDOWS: {"zoomsharing", "\\screenshare", "\\screen_share"},
        MACOS: {"/screen sharing.app/", "zoomsharing", "/screenshare", "/screen_share"},
        LINUX: {"zoomsharing", "/screenshare", "/screen_share"},
    }

    BROWSER_PROCESS_NAMES = set().union(*OS_BROWSER_PROCESS_NAMES.values())
    REMOTE_ACCESS_PROCESS_NAMES = set().union(*OS_REMOTE_ACCESS_PROCESS_NAMES.values())
    SCREEN_SHARING_PROCESS_NAMES = set().union(
        *OS_SCREEN_SHARING_PROCESS_NAMES.values()
    )
    PROTECTED_SYSTEM_PROCESS_NAMES = set().union(
        *OS_PROTECTED_SYSTEM_PROCESS_NAMES.values()
    )

    def __init__(
        self,
        kiosk_root_pid=None,
        check_interval=2.0,
        block_external_browsers=True,
        terminate_remote_access=True,
        terminate_screen_sharing=True,
        event_callback=None,
    ):
        self.current_pid = os.getpid()
        self.operating_system = platform.system()
        self.supported_os = self.operating_system in {
            self.WINDOWS,
            self.MACOS,
            self.LINUX,
        }

        self.check_interval = max(1.0, float(check_interval))
        self.block_external_browsers = bool(block_external_browsers)
        self.terminate_remote_access = bool(terminate_remote_access)
        self.terminate_screen_sharing = bool(terminate_screen_sharing)
        self.event_callback = event_callback

        self.kiosk_root_pid = None
        self.pre_kiosk_browser_root_pids = set()
        self._stop_event = threading.Event()
        self._thread = None
        self._lock = threading.RLock()
        self._warned_missing_kiosk_pid = False

        self.browser_process_names = set(
            self.OS_BROWSER_PROCESS_NAMES.get(self.operating_system, set())
        )
        self.remote_access_process_names = set(
            self.OS_REMOTE_ACCESS_PROCESS_NAMES.get(self.operating_system, set())
        )
        self.screen_sharing_process_names = set(
            self.OS_SCREEN_SHARING_PROCESS_NAMES.get(self.operating_system, set())
        )
        self.protected_system_process_names = set(
            self.OS_PROTECTED_SYSTEM_PROCESS_NAMES.get(self.operating_system, set())
        )
        self.remote_access_path_keywords = set(
            self.OS_REMOTE_ACCESS_PATH_KEYWORDS.get(self.operating_system, set())
        )
        self.screen_sharing_path_keywords = set(
            self.OS_SCREEN_SHARING_PATH_KEYWORDS.get(self.operating_system, set())
        )

        try:
            self.current_username = self._normalize(
                psutil.Process(self.current_pid).username()
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            self.current_username = ""

        print(
            f"[PROCESS MONITOR] Operating system detected: "
            f"{self.operating_system or 'Unknown'}."
        )

        if not self.supported_os:
            print(
                "[PROCESS MONITOR] Unsupported operating system. "
                "Automatic process termination is disabled."
            )

        if kiosk_root_pid is not None:
            self.set_kiosk_root_pid(kiosk_root_pid)

    def _normalize(self, value):
        return str(value or "").strip().lower()

    def _safe_process_name(self, process):
        try:
            return self._normalize(process.name())
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return ""

    def _path_matches(self, executable, keywords):
        executable = self._normalize(executable)

        if not executable:
            return False

        for keyword in keywords:
            keyword = self._normalize(keyword)

            if keyword and keyword in executable:
                return True

        return False

    def _is_browser(self, process_name):
        return self._normalize(process_name) in self.browser_process_names

    def _is_remote_access(self, process_name, executable=""):
        process_name = self._normalize(process_name)

        if process_name in self.remote_access_process_names:
            return True

        return self._path_matches(
            executable,
            self.remote_access_path_keywords,
        )

    def _is_screen_sharing(self, process_name, executable=""):
        process_name = self._normalize(process_name)

        if process_name in self.screen_sharing_process_names:
            return True

        return self._path_matches(
            executable,
            self.screen_sharing_path_keywords,
        )

    def _is_current_user_process(self, process):
        if not self.current_username:
            return False

        try:
            process_username = self._normalize(process.username())
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return False

        return process_username == self.current_username

    def _is_system_owned_process(self, process):
        try:
            username = self._normalize(process.username())
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return True

        if self.operating_system == self.WINDOWS:
            system_accounts = {
                "system",
                "local service",
                "network service",
                "nt authority\\system",
                "nt authority\\local service",
                "nt authority\\network service",
            }

            return (
                username in system_accounts
                or username.endswith("\\system")
                or username.endswith("\\local service")
                or username.endswith("\\network service")
            )

        try:
            uids = process.uids()

            if uids is not None and int(uids.real) == 0:
                return True
        except (
            AttributeError,
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
            TypeError,
            ValueError,
        ):
            pass

        if username == "root":
            return True

        if self.operating_system == self.MACOS and username.startswith("_"):
            return True

        return False

    def _is_protected_system_process(self, process):
        protected_pids = {0, 1, self.current_pid}

        if self.operating_system == self.WINDOWS:
            protected_pids.add(4)

        if process.pid in protected_pids:
            return True

        if self._safe_process_name(process) in self.protected_system_process_names:
            return True

        if self._is_system_owned_process(process):
            return True

        if not self._is_current_user_process(process):
            return True

        return False

    def _is_descendant_of(self, process, ancestor_pid):
        if not ancestor_pid:
            return False

        try:
            ancestor_pid = int(ancestor_pid)
            current = process
            visited = set()

            while current is not None:
                if current.pid in visited:
                    return False

                visited.add(current.pid)

                if current.pid == ancestor_pid:
                    return True

                current = current.parent()

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
            ValueError,
            TypeError,
        ):
            return False

        return False

    def _is_kiosk_process(self, process):
        with self._lock:
            kiosk_root_pid = self.kiosk_root_pid

        if not kiosk_root_pid:
            return False

        return self._is_descendant_of(
            process,
            kiosk_root_pid,
        )

    def _process_tree_contains_kiosk(self, process):
        with self._lock:
            kiosk_root_pid = self.kiosk_root_pid

        if not kiosk_root_pid:
            return False

        try:
            kiosk_process = psutil.Process(int(kiosk_root_pid))
        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
            ValueError,
            TypeError,
        ):
            return False

        return self._is_descendant_of(
            kiosk_process,
            process.pid,
        )

    def _get_browser_root(self, process):
        current = process
        root = process
        visited = set()

        while current is not None:
            if current.pid in visited:
                break

            visited.add(current.pid)

            try:
                current_name = current.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                break

            if not self._is_browser(current_name):
                break

            root = current

            try:
                parent = current.parent()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                break

            if parent is None:
                break

            try:
                parent_name = parent.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                break

            if not self._is_browser(parent_name):
                break

            current = parent

        return root

    def _build_event(self, event_type, process, action, reason=None):
        try:
            process_name = process.name()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            process_name = ""

        try:
            executable = process.exe()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            executable = ""

        payload = {
            "event_type": event_type,
            "process_name": process_name,
            "pid": process.pid,
            "executable": executable,
            "action": action,
            "operating_system": self.operating_system,
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }

        if reason:
            payload["reason"] = str(reason)

        return payload

    def _emit_event(self, payload):
        print(
            "[PROCESS MONITOR] "
            f"{payload.get('event_type')} "
            f"| process={payload.get('process_name')} "
            f"| pid={payload.get('pid')} "
            f"| action={payload.get('action')} "
            f"| os={payload.get('operating_system')}"
        )

        if not callable(self.event_callback):
            return

        try:
            self.event_callback(dict(payload))
        except Exception as error:
            print(f"[PROCESS MONITOR] Callback error: {error}")

    def _terminate_process_tree(
        self,
        process,
        event_type,
        require_current_user=False,
    ):
        if not self.supported_os:
            return False

        try:
            process = psutil.Process(int(process.pid))
        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
            ValueError,
            TypeError,
        ):
            return False

        if self._is_protected_system_process(process):
            return False

        if self._is_kiosk_process(process):
            return False

        if self._process_tree_contains_kiosk(process):
            print(
                "[PROCESS MONITOR] Termination skipped because "
                "the target process tree contains the secure kiosk."
            )
            return False

        if require_current_user and not self._is_current_user_process(process):
            return False

        event_payload = self._build_event(
            event_type=event_type,
            process=process,
            action="termination_requested",
        )

        try:
            children = process.children(recursive=True)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            children = []

        targets = []

        for child in reversed(children):
            if self._is_protected_system_process(child):
                continue

            if self._is_kiosk_process(child):
                continue

            if self._process_tree_contains_kiosk(child):
                continue

            if require_current_user and not self._is_current_user_process(child):
                continue

            targets.append(child)

        targets.append(process)

        terminated_any = False
        denied_any = False

        for target in targets:
            try:
                target.terminate()
                terminated_any = True
            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                continue
            except psutil.AccessDenied:
                denied_any = True

                self._emit_event(
                    self._build_event(
                        event_type=event_type,
                        process=target,
                        action="terminate_denied",
                    )
                )

        try:
            _, alive = psutil.wait_procs(
                targets,
                timeout=1.5,
            )
        except Exception:
            alive = []

        for target in alive:
            if self._is_protected_system_process(target):
                continue

            if self._is_kiosk_process(target):
                continue

            if self._process_tree_contains_kiosk(target):
                continue

            if require_current_user and not self._is_current_user_process(target):
                continue

            try:
                target.kill()
                terminated_any = True
            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                continue
            except psutil.AccessDenied:
                denied_any = True

        if terminated_any:
            event_payload["action"] = "terminated"
        elif denied_any:
            event_payload["action"] = "terminate_denied"
        else:
            event_payload["action"] = "not_terminated"

        self._emit_event(event_payload)

        return terminated_any

    def set_kiosk_root_pid(self, kiosk_root_pid):
        if kiosk_root_pid is None:
            with self._lock:
                self.kiosk_root_pid = None

            return

        kiosk_root_pid = int(kiosk_root_pid)

        if kiosk_root_pid <= 0:
            raise ValueError("kiosk_root_pid must be positive.")

        with self._lock:
            self.kiosk_root_pid = kiosk_root_pid

        self._warned_missing_kiosk_pid = False

        print(f"[PROCESS MONITOR] Kiosk root PID set to {kiosk_root_pid}.")

    def capture_pre_kiosk_browser_processes(self):
        if not self.supported_os:
            return []

        browser_roots = set()

        for process in psutil.process_iter(
            attrs=[
                "pid",
                "name",
            ]
        ):
            try:
                if process.pid == self.current_pid:
                    continue

                process_name = process.info.get(
                    "name",
                    "",
                )

                if not self._is_browser(process_name):
                    continue

                if not self._is_current_user_process(process):
                    continue

                if self._is_protected_system_process(process):
                    continue

                root = self._get_browser_root(process)

                if root is None:
                    continue

                if self._is_kiosk_process(root):
                    continue

                browser_roots.add(root.pid)

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess,
            ):
                continue

        with self._lock:
            self.pre_kiosk_browser_root_pids = set(browser_roots)

        print(
            "[PROCESS MONITOR] Captured pre-kiosk browser roots: "
            f"{sorted(browser_roots)}"
        )

        return sorted(browser_roots)

    def terminate_pre_kiosk_browser_processes(self):
        if not self.supported_os:
            return []

        with self._lock:
            kiosk_root_pid = self.kiosk_root_pid
            browser_root_pids = list(self.pre_kiosk_browser_root_pids)

        if not kiosk_root_pid:
            print(
                "[PROCESS MONITOR] Pre-kiosk browser termination skipped "
                "because the kiosk root PID has not been registered."
            )
            return []

        terminated = []

        for pid in browser_root_pids:
            try:
                process = psutil.Process(pid)
            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess,
            ):
                continue

            if self._is_kiosk_process(process):
                continue

            if self._process_tree_contains_kiosk(process):
                continue

            success = self._terminate_process_tree(
                process=process,
                event_type="LAUNCH_BROWSER_TERMINATED",
                require_current_user=True,
            )

            if success:
                terminated.append(pid)

        return terminated

    def scan_once(self):
        if not self.supported_os:
            return

        browser_roots_handled = set()

        with self._lock:
            kiosk_root_pid = self.kiosk_root_pid

        for process in psutil.process_iter(
            attrs=[
                "pid",
                "name",
                "exe",
            ]
        ):
            if self._stop_event.is_set():
                return

            try:
                if process.pid == self.current_pid:
                    continue

                process_name = self._normalize(
                    process.info.get(
                        "name",
                        "",
                    )
                )

                executable = self._normalize(
                    process.info.get(
                        "exe",
                        "",
                    )
                )

                if not process_name:
                    continue

                if self._is_protected_system_process(process):
                    continue

                if self._is_kiosk_process(process):
                    continue

                if self.terminate_remote_access and self._is_remote_access(
                    process_name,
                    executable,
                ):
                    self._terminate_process_tree(
                        process=process,
                        event_type="REMOTE_ACCESS_DETECTED",
                        require_current_user=True,
                    )
                    continue

                if self.terminate_screen_sharing and self._is_screen_sharing(
                    process_name,
                    executable,
                ):
                    self._terminate_process_tree(
                        process=process,
                        event_type="SCREEN_SHARING_DETECTED",
                        require_current_user=True,
                    )
                    continue

                if self.block_external_browsers and self._is_browser(process_name):
                    if not kiosk_root_pid:
                        if not self._warned_missing_kiosk_pid:
                            print(
                                "[PROCESS MONITOR] External-browser termination "
                                "is waiting for the kiosk root PID."
                            )

                            self._warned_missing_kiosk_pid = True

                        continue

                    root = self._get_browser_root(process)

                    if root is None:
                        continue

                    if root.pid in browser_roots_handled:
                        continue

                    browser_roots_handled.add(root.pid)

                    if self._is_kiosk_process(root):
                        continue

                    if self._process_tree_contains_kiosk(root):
                        continue

                    self._terminate_process_tree(
                        process=root,
                        event_type="EXTERNAL_BROWSER_DETECTED",
                        require_current_user=True,
                    )

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess,
            ):
                continue
            except Exception as error:
                print(f"[PROCESS MONITOR] Scan error: {error}")

    def _run(self):
        print("[PROCESS MONITOR] Started.")

        while not self._stop_event.is_set():
            try:
                self.scan_once()
            except Exception as error:
                print(f"[PROCESS MONITOR] Scan failed: {error}")

            self._stop_event.wait(self.check_interval)

        print("[PROCESS MONITOR] Stopped.")

    def start(self):
        if not self.supported_os:
            print(
                "[PROCESS MONITOR] Monitor was not started because "
                "this operating system is not supported."
            )
            return False

        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return False

            self._stop_event.clear()

            self._thread = threading.Thread(
                target=self._run,
                name="SkolariqProcessMonitor",
                daemon=True,
            )

            self._thread.start()

        return True

    def stop(self, timeout=3.0):
        self._stop_event.set()

        thread = self._thread

        if (
            thread is not None
            and thread.is_alive()
            and thread is not threading.current_thread()
        ):
            thread.join(
                timeout=max(
                    0.0,
                    float(timeout),
                )
            )

        with self._lock:
            self._thread = None

        return True

    def close(self):
        return self.stop()
