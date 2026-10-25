# import os
# import platform
# import subprocess
# import threading
# import time
# from datetime import datetime, timezone
# from socket.proctor_socket import ProctorSocket

# import psutil


# class ProcessMonitor:
#     WINDOWS = "Windows"
#     MACOS = "Darwin"
#     LINUX = "Linux"

#     OS_BROWSER_PROCESS_NAMES = {
#         WINDOWS: {
#             "chrome.exe",
#             "comet.exe",
#             "msedge.exe",
#             "firefox.exe",
#             "brave.exe",
#             "vivaldi.exe",
#             "opera.exe",
#             "opera_gx.exe",
#             "chromium.exe",
#             "iexplore.exe",
#             "arc.exe",
#             "duckduckgo.exe",
#             "msedgewebview2.exe",
#         },
#         MACOS: {
#             "safari",
#             "google chrome",
#             "microsoft edge",
#             "firefox",
#             "brave browser",
#             "vivaldi",
#             "opera",
#             "chromium",
#             "comet",
#             "arc",
#             "duckduckgo",
#         },
#         LINUX: {
#             "chrome",
#             "google-chrome",
#             "google-chrome-stable",
#             "chromium",
#             "chromium-browser",
#             "firefox",
#             "firefox-esr",
#             "brave",
#             "brave-browser",
#             "vivaldi",
#             "vivaldi-bin",
#             "opera",
#             "opera-developer",
#             "microsoft-edge",
#             "microsoft-edge-stable",
#             "comet",
#         },
#     }

#     OS_REMOTE_ACCESS_PROCESS_NAMES = {
#         WINDOWS: {
#             "anydesk.exe",
#             "teamviewer.exe",
#             "teamviewer_desktop.exe",
#             "teamviewer_remote_control.exe",
#             "teamviewer_service.exe",
#             "rustdesk.exe",
#             "rustdesk_service.exe",
#             "remoting_host.exe",
#             "chrome_remote_desktop.exe",
#             "mstsc.exe",
#             "msrdc.exe",
#             "rdclient.exe",
#             "msra.exe",
#             "quickassist.exe",
#             "parsec.exe",
#             "parsecd.exe",
#             "logmein.exe",
#             "logmein123.exe",
#             "logmeinrescue.exe",
#             "lmi_rescue.exe",
#             "gotoassist.exe",
#             "g2a-rs_customer.exe",
#             "g2a-rs_support.exe",
#             "screenconnect.clientservice.exe",
#             "screenconnect.windowsclient.exe",
#             "connectwisecontrol.client.exe",
#             "splashtopremote.exe",
#             "srmanager.exe",
#             "strwinclt.exe",
#             "tightvnc.exe",
#             "tvnserver.exe",
#             "tvnviewer.exe",
#             "winvnc.exe",
#             "vncserver.exe",
#             "vncviewer.exe",
#             "ultravnc.exe",
#             "uvnc_service.exe",
#             "remotepc.exe",
#             "dwagent.exe",
#             "dwservice.exe",
#             "meshagent.exe",
#             "aeroadmin.exe",
#             "supremo.exe",
#             "supremosystem.exe",
#             "zohoassist.exe",
#             "bomgar-scc.exe",
#             "rutserver.exe",
#             "rutview.exe",
#         },
#         MACOS: {
#             "anydesk",
#             "teamviewer",
#             "teamviewer_desktop",
#             "teamviewer_service",
#             "rustdesk",
#             "remoting_host",
#             "chrome remote desktop host",
#             "microsoft remote desktop",
#             "windows app",
#             "parsec",
#             "splashtop business",
#             "splashtop streamer",
#             "vnc viewer",
#             "vnc server",
#             "jump desktop",
#             "jump desktop connect",
#             "dwagent",
#             "meshagent",
#             "screenconnect client",
#             "connectwise control",
#         },
#         LINUX: {
#             "anydesk",
#             "teamviewer",
#             "teamviewerd",
#             "rustdesk",
#             "remoting_host",
#             "chrome-remote-desktop",
#             "remmina",
#             "xfreerdp",
#             "wlfreerdp",
#             "freerdp",
#             "krdc",
#             "vinagre",
#             "x11vnc",
#             "tightvncserver",
#             "xtigervnc",
#             "tigervncserver",
#             "vncserver",
#             "vncviewer",
#             "xrdp",
#             "xrdp-sesman",
#             "parsec",
#             "parsecd",
#             "dwagent",
#             "meshagent",
#             "sunshine",
#         },
#     }

#     OS_SCREEN_SHARING_PROCESS_NAMES = {
#         WINDOWS: {
#             "cpthost.exe",
#             "zoomsharingservice.exe",
#             "zoomshare.exe",
#             "screenshare.exe",
#             "screen_share.exe",
#             "sharingservice.exe",
#         },
#         MACOS: {
#             "screen sharing",
#             "zoomsharingservice",
#             "zoomshare",
#             "screenshare",
#             "screen_share",
#             "sharingservice",
#         },
#         LINUX: {
#             "zoomsharingservice",
#             "zoomshare",
#             "screenshare",
#             "screen_share",
#             "sharingservice",
#         },
#     }

#     OS_PROTECTED_SYSTEM_PROCESS_NAMES = {
#         WINDOWS: {
#             "system",
#             "system idle process",
#             "registry",
#             "memory compression",
#             "secure system",
#             "smss.exe",
#             "csrss.exe",
#             "wininit.exe",
#             "winlogon.exe",
#             "services.exe",
#             "lsass.exe",
#             "svchost.exe",
#             "fontdrvhost.exe",
#             "dwm.exe",
#             "explorer.exe",
#             "sihost.exe",
#             "taskhostw.exe",
#             "ctfmon.exe",
#             "spoolsv.exe",
#             "audiodg.exe",
#             "wudfhost.exe",
#             "searchhost.exe",
#             "startmenuexperiencehost.exe",
#             "shellexperiencehost.exe",
#             "applicationframehost.exe",
#             "runtimebroker.exe",
#             "searchapp.exe",
#             "textinputhost.exe",
#             "lockapp.exe",
#             "shellhost.exe",
#             "securityhealthsystray.exe",
#             "widgets.exe",
#             "widgetservice.exe",
#             "dllhost.exe",
#         },
#         MACOS: {
#             "kernel_task",
#             "launchd",
#             "windowserver",
#             "loginwindow",
#             "systemuiserver",
#             "controlcenter",
#             "dock",
#             "finder",
#             "cfprefsd",
#             "coreaudiod",
#             "securityd",
#             "opendirectoryd",
#             "distnoted",
#             "usernoted",
#             "notificationcenter",
#             "spotlight",
#             "mds",
#             "mdworker",
#             "mdworker_shared",
#             "coreservicesuiagent",
#         },
#         LINUX: {
#             "systemd",
#             "init",
#             "kthreadd",
#             "dbus-daemon",
#             "networkmanager",
#             "xorg",
#             "xwayland",
#             "gnome-shell",
#             "plasmashell",
#             "pipewire",
#             "wireplumber",
#             "pulseaudio",
#             "xdg-desktop-portal",
#             "xdg-desktop-portal-gtk",
#             "xdg-desktop-portal-gnome",
#             "xdg-document-portal",
#             "gvfsd",
#             "gvfsd-fuse",
#             "at-spi-bus-launcher",
#             "gsettings-helper",
#         },
#     }

#     OS_REMOTE_ACCESS_PATH_KEYWORDS = {
#         WINDOWS: {
#             "\\anydesk\\",
#             "\\teamviewer\\",
#             "\\rustdesk\\",
#             "\\parsec\\",
#             "\\splashtop\\",
#             "\\screenconnect\\",
#             "\\connectwise control\\",
#             "\\chrome remote desktop\\",
#             "\\dwagent\\",
#         },
#         MACOS: {
#             "/anydesk.app/",
#             "/teamviewer.app/",
#             "/rustdesk.app/",
#             "/parsec.app/",
#             "/splashtop",
#             "/chrome remote desktop",
#             "/jump desktop",
#             "/connectwise control",
#             "/dwagent",
#         },
#         LINUX: {
#             "/anydesk",
#             "/teamviewer",
#             "/rustdesk",
#             "/parsec",
#             "/remmina",
#             "/xrdp",
#             "/tigervnc",
#             "/tightvnc",
#             "/x11vnc",
#             "/dwagent",
#         },
#     }

#     OS_SCREEN_SHARING_PATH_KEYWORDS = {
#         WINDOWS: {
#             "zoomsharing",
#             "\\screenshare",
#             "\\screen_share",
#         },
#         MACOS: {
#             "/screen sharing.app/",
#             "zoomsharing",
#             "/screenshare",
#             "/screen_share",
#         },
#         LINUX: {
#             "zoomsharing",
#             "/screenshare",
#             "/screen_share",
#         },
#     }

#     OS_MEDIA_PROCESS_NAMES = {
#         WINDOWS: {
#             "windowscamera.exe",
#             "camera.exe",
#             "microsoft.windows.camera.exe",
#             "soundrecorder.exe",
#             "voicerecorder.exe",
#             "audacity.exe",
#             "obs64.exe",
#             "obs32.exe",
#             "obs.exe",
#             "streamlabs.exe",
#             "streamlabs desktop.exe",
#             "zoom.exe",
#             "teams.exe",
#             "ms-teams.exe",
#             "skype.exe",
#             "skypeapp.exe",
#             "discord.exe",
#             "webex.exe",
#             "webexmta.exe",
#             "ciscowebexstart.exe",
#             "slack.exe",
#             "loom.exe",
#             "loom desktop.exe",
#             "snippingtool.exe",
#             "gamebar.exe",
#             "gamebarftserver.exe",
#             "vlc.exe",
#             "wmplayer.exe",
#             "spotify.exe",
#             "itunes.exe",
#             "musicbee.exe",
#             "foobar2000.exe",
#             "potplayermini.exe",
#             "potplayermini64.exe",
#             "mpv.exe",
#             "ffmpeg.exe",
#             "ffplay.exe",
#         },
#         MACOS: {
#             "photo booth",
#             "facetime",
#             "quicktime player",
#             "voice memos",
#             "audacity",
#             "obs",
#             "obs studio",
#             "streamlabs",
#             "zoom.us",
#             "zoom",
#             "microsoft teams",
#             "teams",
#             "discord",
#             "skype",
#             "webex",
#             "slack",
#             "loom",
#             "vlc",
#             "spotify",
#             "itunes",
#             "music",
#             "ffmpeg",
#             "ffplay",
#         },
#         LINUX: {
#             "cheese",
#             "guvcview",
#             "kamoso",
#             "audacity",
#             "obs",
#             "obs-studio",
#             "simplescreenrecorder",
#             "vokoscreenng",
#             "zoom",
#             "teams",
#             "teams-for-linux",
#             "discord",
#             "skypeforlinux",
#             "webex",
#             "slack",
#             "loom",
#             "vlc",
#             "spotify",
#             "mpv",
#             "ffmpeg",
#             "ffplay",
#             "arecord",
#             "aplay",
#             "parec",
#             "paplay",
#             "pw-record",
#             "pw-play",
#         },
#     }

#     OS_MEDIA_PATH_KEYWORDS = {
#         WINDOWS: {
#             "\\windowscamera\\",
#             "\\camera\\",
#             "\\soundrecorder\\",
#             "\\voicerecorder\\",
#             "\\audacity\\",
#             "\\obs studio\\",
#             "\\obs-studio\\",
#             "\\streamlabs\\",
#             "\\zoom\\",
#             "\\teams\\",
#             "\\microsoft teams\\",
#             "\\discord\\",
#             "\\skype\\",
#             "\\webex\\",
#             "\\slack\\",
#             "\\loom\\",
#             "\\vlc\\",
#             "\\spotify\\",
#             "\\foobar2000\\",
#             "\\potplayer\\",
#         },
#         MACOS: {
#             "/photo booth.app/",
#             "/facetime.app/",
#             "/quicktime player.app/",
#             "/voice memos.app/",
#             "/audacity.app/",
#             "/obs.app/",
#             "/streamlabs",
#             "/zoom.us.app/",
#             "/microsoft teams.app/",
#             "/discord.app/",
#             "/skype.app/",
#             "/webex.app/",
#             "/slack.app/",
#             "/loom.app/",
#             "/vlc.app/",
#             "/spotify.app/",
#         },
#         LINUX: {
#             "/cheese",
#             "/guvcview",
#             "/kamoso",
#             "/audacity",
#             "/obs",
#             "/obs-studio",
#             "/simplescreenrecorder",
#             "/vokoscreen",
#             "/zoom",
#             "/teams",
#             "/discord",
#             "/skype",
#             "/webex",
#             "/slack",
#             "/loom",
#             "/vlc",
#             "/spotify",
#             "/ffmpeg",
#             "/ffplay",
#         },
#     }

#     MEDIA_PROCESS_NAMES = set().union(*OS_MEDIA_PROCESS_NAMES.values())

#     BROWSER_PROCESS_NAMES = set().union(*OS_BROWSER_PROCESS_NAMES.values())

#     REMOTE_ACCESS_PROCESS_NAMES = set().union(*OS_REMOTE_ACCESS_PROCESS_NAMES.values())

#     SCREEN_SHARING_PROCESS_NAMES = set().union(
#         *OS_SCREEN_SHARING_PROCESS_NAMES.values()
#     )

#     PROTECTED_SYSTEM_PROCESS_NAMES = set().union(
#         *OS_PROTECTED_SYSTEM_PROCESS_NAMES.values()
#     )

#     def __init__(
#         self,
#         kiosk_root_pid=None,
#         check_interval=2.0,
#         block_external_browsers=True,
#         terminate_remote_access=True,
#         terminate_screen_sharing=True,
#         event_callback=None,
#         strict_user_process_lockdown=False,
#         terminate_media_processes=True,
#         terminate_duplicate_app_instances=True,
#     ):
#         self.current_pid = os.getpid()

#         self.operating_system = platform.system()

#         self.supported_os = self.operating_system in {
#             self.WINDOWS,
#             self.MACOS,
#             self.LINUX,
#         }

#         self.check_interval = max(
#             1.0,
#             float(check_interval),
#         )

#         self.block_external_browsers = bool(block_external_browsers)

#         self.terminate_remote_access = bool(terminate_remote_access)

#         self.terminate_screen_sharing = bool(terminate_screen_sharing)

#         self.strict_user_process_lockdown = bool(strict_user_process_lockdown)

#         self.terminate_media_processes = bool(terminate_media_processes)

#         self.terminate_duplicate_app_instances = bool(terminate_duplicate_app_instances)

#         self.event_callback = event_callback

#         self.kiosk_root_pid = None

#         self.pre_kiosk_browser_root_pids = set()

#         self._stop_event = threading.Event()

#         self._thread = None

#         self._lock = threading.RLock()

#         self._warned_missing_kiosk_pid = False

#         self.browser_process_names = set(
#             self.OS_BROWSER_PROCESS_NAMES.get(
#                 self.operating_system,
#                 set(),
#             )
#         )

#         self.remote_access_process_names = set(
#             self.OS_REMOTE_ACCESS_PROCESS_NAMES.get(
#                 self.operating_system,
#                 set(),
#             )
#         )

#         self.screen_sharing_process_names = set(
#             self.OS_SCREEN_SHARING_PROCESS_NAMES.get(
#                 self.operating_system,
#                 set(),
#             )
#         )

#         self.media_process_names = set(
#             self.OS_MEDIA_PROCESS_NAMES.get(
#                 self.operating_system,
#                 set(),
#             )
#         )

#         self.protected_system_process_names = set(
#             self.OS_PROTECTED_SYSTEM_PROCESS_NAMES.get(
#                 self.operating_system,
#                 set(),
#             )
#         )

#         self.remote_access_path_keywords = set(
#             self.OS_REMOTE_ACCESS_PATH_KEYWORDS.get(
#                 self.operating_system,
#                 set(),
#             )
#         )

#         self.screen_sharing_path_keywords = set(
#             self.OS_SCREEN_SHARING_PATH_KEYWORDS.get(
#                 self.operating_system,
#                 set(),
#             )
#         )

#         self.media_path_keywords = set(
#             self.OS_MEDIA_PATH_KEYWORDS.get(
#                 self.operating_system,
#                 set(),
#             )
#         )

#         self.current_username = ""

#         self.current_process_name = ""

#         self.current_executable = ""

#         self.current_cmdline = []

#         self.current_cwd = ""

#         self.current_python_entrypoint = None

#         try:
#             current_process = psutil.Process(self.current_pid)

#             self.current_username = self._normalize(current_process.username())

#             self.current_process_name = self._normalize(current_process.name())

#             self.current_executable = self._normalize_path(current_process.exe())

#             try:
#                 self.current_cmdline = list(current_process.cmdline() or [])

#             except (
#                 psutil.NoSuchProcess,
#                 psutil.AccessDenied,
#                 psutil.ZombieProcess,
#             ):
#                 self.current_cmdline = []

#             try:
#                 self.current_cwd = self._normalize_path(current_process.cwd())

#             except (
#                 psutil.NoSuchProcess,
#                 psutil.AccessDenied,
#                 psutil.ZombieProcess,
#             ):
#                 self.current_cwd = ""

#             self.current_python_entrypoint = self._extract_python_entrypoint(
#                 self.current_cmdline,
#                 self.current_cwd,
#             )

#         except (
#             psutil.NoSuchProcess,
#             psutil.AccessDenied,
#             psutil.ZombieProcess,
#         ):
#             self.current_username = ""

#         print(
#             "[PROCESS MONITOR] Operating system detected: "
#             f"{self.operating_system or 'Unknown'}."
#         )

#         if not self.supported_os:
#             print(
#                 "[PROCESS MONITOR] Unsupported operating system. "
#                 "Automatic process termination is disabled."
#             )

#         if kiosk_root_pid is not None:
#             self.set_kiosk_root_pid(kiosk_root_pid)

#     def _normalize(
#         self,
#         value,
#     ):
#         return str(value or "").strip().lower()

#     def _normalize_path(
#         self,
#         value,
#     ):
#         value = str(value or "").strip()

#         if not value:
#             return ""

#         try:
#             return os.path.normcase(os.path.abspath(value))

#         except Exception:
#             return os.path.normcase(value)

#     def _safe_process_executable(
#         self,
#         process,
#     ):
#         try:
#             return self._normalize_path(process.exe())

#         except (
#             psutil.NoSuchProcess,
#             psutil.AccessDenied,
#             psutil.ZombieProcess,
#         ):
#             return ""

#     def _safe_process_cmdline(
#         self,
#         process,
#     ):
#         try:
#             return list(process.cmdline() or [])

#         except (
#             psutil.NoSuchProcess,
#             psutil.AccessDenied,
#             psutil.ZombieProcess,
#         ):
#             return []

#     def _safe_process_cwd(
#         self,
#         process,
#     ):
#         try:
#             return self._normalize_path(process.cwd())

#         except (
#             psutil.NoSuchProcess,
#             psutil.AccessDenied,
#             psutil.ZombieProcess,
#         ):
#             return ""

#     def _is_python_runtime_name(
#         self,
#         process_name,
#     ):
#         process_name = self._normalize(process_name)

#         if not process_name:
#             return False

#         python_names = {
#             "python",
#             "python.exe",
#             "pythonw",
#             "pythonw.exe",
#             "python3",
#             "python3.exe",
#         }

#         if process_name in python_names:
#             return True

#         return process_name.startswith("python")

#     def _extract_python_entrypoint(
#         self,
#         cmdline,
#         cwd="",
#     ):
#         if not isinstance(
#             cmdline,
#             (
#                 list,
#                 tuple,
#             ),
#         ):
#             return None

#         tokens = [
#             str(item or "").strip() for item in cmdline if str(item or "").strip()
#         ]

#         if not tokens:
#             return None

#         for (
#             index,
#             token,
#         ) in enumerate(tokens):
#             normalized_token = self._normalize(token)

#             if normalized_token == "-m" and index + 1 < len(tokens):
#                 module_name = self._normalize(tokens[index + 1])

#                 if module_name:
#                     return (
#                         "module",
#                         module_name,
#                     )

#             if normalized_token.startswith("-m") and len(normalized_token) > 2:
#                 module_name = normalized_token[2:].strip()

#                 if module_name:
#                     return (
#                         "module",
#                         module_name,
#                     )

#         for token in tokens[1:]:
#             token_text = str(token).strip().strip('"').strip("'")

#             if not token_text.lower().endswith(".py"):
#                 continue

#             if os.path.isabs(token_text):
#                 script_path = self._normalize_path(token_text)

#             else:
#                 base_cwd = self._normalize_path(cwd)

#                 script_path = self._normalize_path(
#                     os.path.join(
#                         base_cwd or os.getcwd(),
#                         token_text,
#                     )
#                 )

#             if script_path:
#                 return (
#                     "script",
#                     script_path,
#                 )

#         return None

#     def _is_same_proctor_application(
#         self,
#         process,
#     ):
#         """
#         Return True only for another instance of this same proctor app.

#         Packaged builds are matched by executable identity. Development Python
#         launches are matched by entrypoint (for example, `python -m src.main`),
#         never by python.exe alone, so unrelated Python processes stay allowed.
#         """

#         if process is None:
#             return False

#         try:
#             candidate_pid = int(process.pid)

#         except (
#             TypeError,
#             ValueError,
#             AttributeError,
#         ):
#             return False

#         if candidate_pid == int(self.current_pid):
#             return False

#         if not self._is_current_user_process(process):
#             return False

#         candidate_name = self._safe_process_name(process)

#         candidate_executable = self._safe_process_executable(process)

#         candidate_cmdline = self._safe_process_cmdline(process)

#         candidate_cwd = self._safe_process_cwd(process)

#         candidate_entrypoint = self._extract_python_entrypoint(
#             candidate_cmdline,
#             candidate_cwd,
#         )

#         current_entrypoint = self.current_python_entrypoint

#         if current_entrypoint is not None and candidate_entrypoint is not None:
#             if candidate_entrypoint == current_entrypoint:
#                 return True

#             (
#                 current_kind,
#                 current_value,
#             ) = current_entrypoint

#             (
#                 candidate_kind,
#                 candidate_value,
#             ) = candidate_entrypoint

#             module_script_pairs = {
#                 (
#                     "src.main",
#                     "src/main.py",
#                 ),
#             }

#             if current_kind == "module" and candidate_kind == "script":
#                 candidate_script = (
#                     str(candidate_value)
#                     .replace(
#                         "\\",
#                         "/",
#                     )
#                     .lower()
#                 )

#                 if any(
#                     (
#                         current_value == module_name
#                         and candidate_script.endswith(script_suffix)
#                     )
#                     for (
#                         module_name,
#                         script_suffix,
#                     ) in module_script_pairs
#                 ):
#                     return True

#             if current_kind == "script" and candidate_kind == "module":
#                 current_script = (
#                     str(current_value)
#                     .replace(
#                         "\\",
#                         "/",
#                     )
#                     .lower()
#                 )

#                 if any(
#                     (
#                         candidate_value == module_name
#                         and current_script.endswith(script_suffix)
#                     )
#                     for (
#                         module_name,
#                         script_suffix,
#                     ) in module_script_pairs
#                 ):
#                     return True

#         current_name = self._normalize(self.current_process_name)

#         current_executable = self._normalize_path(self.current_executable)

#         if (
#             current_executable
#             and candidate_executable
#             and current_executable == candidate_executable
#             and not self._is_python_runtime_name(current_name)
#         ):
#             return True

#         if (
#             current_name
#             and candidate_name == current_name
#             and ("skolariq" in current_name or "proctor" in current_name)
#         ):
#             if (
#                 not current_executable
#                 or not candidate_executable
#                 or candidate_executable == current_executable
#             ):
#                 return True

#         return False

#     def _is_media_process(
#         self,
#         process_name,
#         executable="",
#     ):
#         process_name = self._normalize(process_name)

#         if process_name in self.media_process_names:
#             return True

#         if self._path_matches(
#             executable,
#             self.media_path_keywords,
#         ):
#             return True

#         generic_keywords = {
#             "camera",
#             "webcam",
#             "voice recorder",
#             "voicerecorder",
#             "sound recorder",
#             "soundrecorder",
#             "screen recorder",
#             "screenrecorder",
#             "audacity",
#             "obs",
#             "streamlabs",
#             "zoom",
#             "teams",
#             "skype",
#             "discord",
#             "webex",
#             "loom",
#             "vlc",
#             "spotify",
#         }

#         return any(keyword in process_name for keyword in generic_keywords)

#     def _safe_process_name(
#         self,
#         process,
#     ):
#         try:
#             return self._normalize(process.name())

#         except (
#             psutil.NoSuchProcess,
#             psutil.AccessDenied,
#             psutil.ZombieProcess,
#         ):
#             return ""

#     def _path_matches(
#         self,
#         executable,
#         keywords,
#     ):
#         executable = self._normalize(executable)

#         if not executable:
#             return False

#         for keyword in keywords:
#             keyword = self._normalize(keyword)

#             if keyword and keyword in executable:
#                 return True

#         return False

#     def _is_browser(
#         self,
#         process_name,
#     ):
#         return self._normalize(process_name) in self.browser_process_names

#     def _is_remote_access(
#         self,
#         process_name,
#         executable="",
#     ):
#         process_name = self._normalize(process_name)

#         if process_name in self.remote_access_process_names:
#             return True

#         return self._path_matches(
#             executable,
#             self.remote_access_path_keywords,
#         )

#     def _is_screen_sharing(
#         self,
#         process_name,
#         executable="",
#     ):
#         process_name = self._normalize(process_name)

#         if process_name in self.screen_sharing_process_names:
#             return True

#         return self._path_matches(
#             executable,
#             self.screen_sharing_path_keywords,
#         )

#     def _is_current_user_process(
#         self,
#         process,
#     ):
#         if not self.current_username:
#             return False

#         try:
#             process_username = self._normalize(process.username())

#         except (
#             psutil.NoSuchProcess,
#             psutil.AccessDenied,
#             psutil.ZombieProcess,
#         ):
#             return False

#         return process_username == self.current_username

#     def _is_system_owned_process(
#         self,
#         process,
#     ):
#         try:
#             username = self._normalize(process.username())

#         except (
#             psutil.NoSuchProcess,
#             psutil.AccessDenied,
#             psutil.ZombieProcess,
#         ):
#             return True

#         if self.operating_system == self.WINDOWS:
#             system_accounts = {
#                 "system",
#                 "local service",
#                 "network service",
#                 "nt authority\\system",
#                 "nt authority\\local service",
#                 "nt authority\\network service",
#             }

#             return (
#                 username in system_accounts
#                 or username.endswith("\\system")
#                 or username.endswith("\\local service")
#                 or username.endswith("\\network service")
#             )

#         try:
#             uids = process.uids()

#             if uids is not None and int(uids.real) == 0:
#                 return True

#         except (
#             AttributeError,
#             psutil.NoSuchProcess,
#             psutil.AccessDenied,
#             psutil.ZombieProcess,
#             TypeError,
#             ValueError,
#         ):
#             pass

#         if username == "root":
#             return True

#         if self.operating_system == self.MACOS and username.startswith("_"):
#             return True

#         return False

#     def _is_protected_system_process(
#         self,
#         process,
#     ):
#         protected_pids = {
#             0,
#             1,
#             self.current_pid,
#         }

#         if self.operating_system == self.WINDOWS:
#             protected_pids.add(4)

#         if process.pid in protected_pids:
#             return True

#         if self._safe_process_name(process) in self.protected_system_process_names:
#             return True

#         if self._is_system_owned_process(process):
#             return True

#         if not self._is_current_user_process(process):
#             return True

#         return False

#     def _is_descendant_of(
#         self,
#         process,
#         ancestor_pid,
#     ):
#         if not ancestor_pid:
#             return False

#         try:
#             ancestor_pid = int(ancestor_pid)

#             current = process

#             visited = set()

#             while current is not None:
#                 if current.pid in visited:
#                     return False

#                 visited.add(current.pid)

#                 if current.pid == ancestor_pid:
#                     return True

#                 current = current.parent()

#         except (
#             psutil.NoSuchProcess,
#             psutil.AccessDenied,
#             psutil.ZombieProcess,
#             ValueError,
#             TypeError,
#         ):
#             return False

#         return False

#     def _is_kiosk_process(
#         self,
#         process,
#     ):
#         with self._lock:
#             kiosk_root_pid = self.kiosk_root_pid

#         if not kiosk_root_pid:
#             return False

#         return self._is_descendant_of(
#             process,
#             kiosk_root_pid,
#         )

#     def _process_tree_contains_kiosk(
#         self,
#         process,
#     ):
#         with self._lock:
#             kiosk_root_pid = self.kiosk_root_pid

#         if not kiosk_root_pid:
#             return False

#         try:
#             kiosk_process = psutil.Process(int(kiosk_root_pid))

#         except (
#             psutil.NoSuchProcess,
#             psutil.AccessDenied,
#             psutil.ZombieProcess,
#             ValueError,
#             TypeError,
#         ):
#             return False

#         return self._is_descendant_of(
#             kiosk_process,
#             process.pid,
#         )

#     def _get_browser_root(
#         self,
#         process,
#     ):
#         current = process

#         root = process

#         visited = set()

#         while current is not None:
#             if current.pid in visited:
#                 break

#             visited.add(current.pid)

#             try:
#                 current_name = current.name()

#             except (
#                 psutil.NoSuchProcess,
#                 psutil.AccessDenied,
#                 psutil.ZombieProcess,
#             ):
#                 break

#             if not self._is_browser(current_name):
#                 break

#             root = current

#             try:
#                 parent = current.parent()

#             except (
#                 psutil.NoSuchProcess,
#                 psutil.AccessDenied,
#                 psutil.ZombieProcess,
#             ):
#                 break

#             if parent is None:
#                 break

#             try:
#                 parent_name = parent.name()

#             except (
#                 psutil.NoSuchProcess,
#                 psutil.AccessDenied,
#                 psutil.ZombieProcess,
#             ):
#                 break

#             if not self._is_browser(parent_name):
#                 break

#             current = parent

#         return root

#     def _build_event(
#         self,
#         event_type,
#         process,
#         action,
#         reason=None,
#     ):
#         try:
#             process_name = process.name()

#         except (
#             psutil.NoSuchProcess,
#             psutil.AccessDenied,
#             psutil.ZombieProcess,
#         ):
#             process_name = ""

#         try:
#             executable = process.exe()

#         except (
#             psutil.NoSuchProcess,
#             psutil.AccessDenied,
#             psutil.ZombieProcess,
#         ):
#             executable = ""

#         payload = {
#             "event_type": event_type,
#             "process_name": process_name,
#             "pid": process.pid,
#             "executable": executable,
#             "action": action,
#             "operating_system": self.operating_system,
#             "captured_at": datetime.now(timezone.utc).isoformat(),
#         }

#         if reason:
#             payload["reason"] = str(reason)

#         return payload

#     def _emit_event(
#         self,
#         payload,
#     ):
#         print(
#             "[PROCESS MONITOR] "
#             f"{payload.get('event_type')} "
#             f"| process={payload.get('process_name')} "
#             f"| pid={payload.get('pid')} "
#             f"| action={payload.get('action')} "
#             f"| os={payload.get('operating_system')}"
#         )

#         if not callable(self.event_callback):
#             return

#         try:
#             self.event_callback(dict(payload))

#         except Exception as error:
#             print(
#                 "[PROCESS MONITOR] Callback error:",
#                 error,
#             )

#     def _terminate_process_tree(
#         self,
#         process,
#         event_type,
#         require_current_user=False,
#     ):
#         if not self.supported_os:
#             return False

#         try:
#             process = psutil.Process(int(process.pid))

#         except (
#             psutil.NoSuchProcess,
#             psutil.AccessDenied,
#             psutil.ZombieProcess,
#             ValueError,
#             TypeError,
#         ):
#             return False

#         if self._is_protected_system_process(process):
#             return False

#         if self._is_kiosk_process(process):
#             return False

#         if self._process_tree_contains_kiosk(process):
#             print(
#                 "[PROCESS MONITOR] Termination skipped because "
#                 "the target process tree contains the secure kiosk."
#             )

#             return False

#         if require_current_user and not self._is_current_user_process(process):
#             return False

#         event_payload = self._build_event(
#             event_type=event_type,
#             process=process,
#             action="termination_requested",
#         )

#         try:
#             children = process.children(recursive=True)

#         except (
#             psutil.NoSuchProcess,
#             psutil.AccessDenied,
#             psutil.ZombieProcess,
#         ):
#             children = []

#         targets = []

#         for child in reversed(children):
#             if self._is_protected_system_process(child):
#                 continue

#             if self._is_kiosk_process(child):
#                 continue

#             if self._process_tree_contains_kiosk(child):
#                 continue

#             if require_current_user and not self._is_current_user_process(child):
#                 continue

#             targets.append(child)

#         targets.append(process)

#         terminated_any = False

#         denied_any = False

#         for target in targets:
#             try:
#                 target.terminate()

#                 terminated_any = True

#             except (
#                 psutil.NoSuchProcess,
#                 psutil.ZombieProcess,
#             ):
#                 continue

#             except psutil.AccessDenied:
#                 denied_any = True

#                 self._emit_event(
#                     self._build_event(
#                         event_type=event_type,
#                         process=target,
#                         action="terminate_denied",
#                     )
#                 )

#         try:
#             _, alive = psutil.wait_procs(
#                 targets,
#                 timeout=1.5,
#             )

#         except Exception:
#             alive = []

#         for target in alive:
#             if self._is_protected_system_process(target):
#                 continue

#             if self._is_kiosk_process(target):
#                 continue

#             if self._process_tree_contains_kiosk(target):
#                 continue

#             if require_current_user and not self._is_current_user_process(target):
#                 continue

#             try:
#                 target.kill()

#                 terminated_any = True

#             except (
#                 psutil.NoSuchProcess,
#                 psutil.ZombieProcess,
#             ):
#                 continue

#             except psutil.AccessDenied:
#                 denied_any = True

#         if terminated_any:
#             event_payload["action"] = "terminated"

#         elif denied_any:
#             event_payload["action"] = "terminate_denied"

#         else:
#             event_payload["action"] = "not_terminated"

#         self._emit_event(event_payload)

#         return terminated_any

#     def set_kiosk_root_pid(
#         self,
#         kiosk_root_pid,
#     ):
#         if kiosk_root_pid is None:
#             with self._lock:
#                 self.kiosk_root_pid = None

#             return

#         kiosk_root_pid = int(kiosk_root_pid)

#         if kiosk_root_pid <= 0:
#             raise ValueError("kiosk_root_pid must be positive.")

#         with self._lock:
#             self.kiosk_root_pid = kiosk_root_pid

#         self._warned_missing_kiosk_pid = False

#         print("[PROCESS MONITOR] " f"Kiosk root PID set to {kiosk_root_pid}.")

#     def _process_tree_contains_proctor(
#         self,
#         process,
#     ):
#         """
#         Return True when `process` is this proctor process or an ancestor of it.

#         This is critical on Windows because native `taskkill /T` kills an entire
#         descendant tree. We must never target cmd.exe / powershell.exe / a launcher
#         process when that tree currently contains this running proctor instance.
#         """

#         if process is None:
#             return True

#         try:
#             target_pid = int(process.pid)

#         except (
#             TypeError,
#             ValueError,
#             AttributeError,
#         ):
#             return True

#         if target_pid == int(self.current_pid):
#             return True

#         try:
#             current = psutil.Process(int(self.current_pid))

#             visited = set()

#             while current is not None:
#                 if current.pid in visited:
#                     break

#                 visited.add(current.pid)

#                 if int(current.pid) == target_pid:
#                     return True

#                 current = current.parent()

#         except (
#             psutil.NoSuchProcess,
#             psutil.AccessDenied,
#             psutil.ZombieProcess,
#         ):
#             return False

#         return False

#     def _windows_force_kill_process_tree(
#         self,
#         process,
#         event_type,
#         require_current_user=True,
#     ):
#         """
#         Force-close a Windows process tree using taskkill /F /T.

#         psutil terminate()/kill() is retained as the normal cross-platform path,
#         but Chromium/Electron/WebView trees can be more reliably closed by the
#         native Windows process-tree command.
#         """

#         if self.operating_system != self.WINDOWS:
#             return False

#         try:
#             process = psutil.Process(int(process.pid))

#         except (
#             psutil.NoSuchProcess,
#             psutil.AccessDenied,
#             psutil.ZombieProcess,
#             TypeError,
#             ValueError,
#         ):
#             return True

#         if self._is_protected_system_process(process):
#             return False

#         if self._process_tree_contains_proctor(process):
#             return False

#         if self._is_kiosk_process(process):
#             return False

#         if self._process_tree_contains_kiosk(process):
#             return False

#         if require_current_user and not self._is_current_user_process(process):
#             return False

#         pid = int(process.pid)

#         try:
#             process_name = process.name()

#         except (
#             psutil.NoSuchProcess,
#             psutil.AccessDenied,
#             psutil.ZombieProcess,
#         ):
#             process_name = ""

#         creationflags = getattr(
#             subprocess,
#             "CREATE_NO_WINDOW",
#             0,
#         )

#         try:
#             completed = subprocess.run(
#                 [
#                     "taskkill",
#                     "/PID",
#                     str(pid),
#                     "/T",
#                     "/F",
#                 ],
#                 stdout=subprocess.PIPE,
#                 stderr=subprocess.PIPE,
#                 text=True,
#                 timeout=6.0,
#                 creationflags=creationflags,
#                 check=False,
#             )

#         except Exception as error:
#             self._emit_event(
#                 {
#                     "event_type": event_type,
#                     "process_name": process_name,
#                     "pid": pid,
#                     "executable": "",
#                     "action": "native_force_kill_error",
#                     "operating_system": self.operating_system,
#                     "captured_at": datetime.now(timezone.utc).isoformat(),
#                     "reason": str(error),
#                 }
#             )

#             return False

#         deadline = time.monotonic() + 2.0

#         while time.monotonic() < deadline:
#             if not psutil.pid_exists(pid):
#                 break

#             time.sleep(0.05)

#         terminated = not psutil.pid_exists(pid)

#         self._emit_event(
#             {
#                 "event_type": event_type,
#                 "process_name": process_name,
#                 "pid": pid,
#                 "executable": "",
#                 "action": (
#                     "terminated_native" if terminated else "native_force_kill_failed"
#                 ),
#                 "operating_system": self.operating_system,
#                 "captured_at": datetime.now(timezone.utc).isoformat(),
#                 "reason": (
#                     (completed.stderr or completed.stdout or "").strip()
#                     if not terminated
#                     else None
#                 ),
#             }
#         )

#         return terminated

#     def _collect_browser_roots_for_forced_cleanup(
#         self,
#     ):
#         """
#         Collect unique current-user browser roots before the exam.
#         """

#         roots = {}

#         for process in psutil.process_iter(
#             attrs=[
#                 "pid",
#                 "name",
#                 "exe",
#             ]
#         ):
#             try:
#                 if process.pid == self.current_pid:
#                     continue

#                 process_name = self._normalize(
#                     process.info.get(
#                         "name",
#                         "",
#                     )
#                 )

#                 if not process_name:
#                     continue

#                 if not self._is_browser(process_name):
#                     continue

#                 if not self._is_current_user_process(process):
#                     continue

#                 if self._is_protected_system_process(process):
#                     continue

#                 root = self._get_browser_root(process)

#                 if root is None:
#                     root = process

#                 if self._process_tree_contains_proctor(root):
#                     continue

#                 if self._is_kiosk_process(root):
#                     continue

#                 if self._process_tree_contains_kiosk(root):
#                     continue

#                 roots[int(root.pid)] = root

#             except (
#                 psutil.NoSuchProcess,
#                 psutil.AccessDenied,
#                 psutil.ZombieProcess,
#             ):
#                 continue

#         return list(roots.values())

#     def terminate_all_browsers_before_exam(
#         self,
#         max_passes=4,
#         settle_delay=0.20,
#     ):
#         """
#         Force-close every current-user browser process tree before hardware opens.

#         On Windows this uses taskkill /F /T first. This is intentionally stronger
#         than psutil-only termination and closes renderer/audio processes belonging
#         to YouTube, Spotify Web, Meet, web cameras, etc.
#         """

#         result = {
#             "detected": [],
#             "terminated": [],
#             "failed": [],
#         }

#         seen = set()

#         for _ in range(
#             max(
#                 1,
#                 int(max_passes),
#             )
#         ):
#             roots = self._collect_browser_roots_for_forced_cleanup()

#             if not roots:
#                 break

#             terminated_this_pass = 0

#             for root in roots:
#                 try:
#                     name = root.name()

#                 except (
#                     psutil.NoSuchProcess,
#                     psutil.AccessDenied,
#                     psutil.ZombieProcess,
#                 ):
#                     name = ""

#                 item = {
#                     "pid": int(root.pid),
#                     "process_name": name,
#                     "category": "browser",
#                 }

#                 key = (
#                     item["pid"],
#                     self._normalize(name),
#                 )

#                 if key not in seen:
#                     seen.add(key)

#                     result["detected"].append(dict(item))

#                 if self.operating_system == self.WINDOWS:
#                     success = self._windows_force_kill_process_tree(
#                         process=root,
#                         event_type="PRE_EXAM_BROWSER_FORCE_TERMINATED",
#                         require_current_user=True,
#                     )

#                 else:
#                     success = self._terminate_process_tree(
#                         process=root,
#                         event_type="PRE_EXAM_BROWSER_FORCE_TERMINATED",
#                         require_current_user=True,
#                     )

#                 if success or not psutil.pid_exists(int(root.pid)):
#                     terminated_this_pass += 1

#                     result["terminated"].append(dict(item))

#             if settle_delay > 0:
#                 time.sleep(float(settle_delay))

#             if terminated_this_pass == 0:
#                 break

#         remaining = self._collect_browser_roots_for_forced_cleanup()

#         for root in remaining:
#             try:
#                 name = root.name()

#             except (
#                 psutil.NoSuchProcess,
#                 psutil.AccessDenied,
#                 psutil.ZombieProcess,
#             ):
#                 name = ""

#             result["failed"].append(
#                 {
#                     "pid": int(root.pid),
#                     "process_name": name,
#                     "category": "browser",
#                 }
#             )

#         return result

#     def _is_strict_lockdown_exempt(
#         self,
#         process,
#     ):
#         """
#         Return True when a process must never be terminated by strict lockdown.

#         Protected:
#         - this Python proctor process,
#         - protected/system-owned processes,
#         - the active secure kiosk process tree,
#         - any process tree that contains the secure kiosk.
#         """

#         if process is None:
#             return True

#         try:
#             if int(process.pid) == int(self.current_pid):
#                 return True

#         except (
#             TypeError,
#             ValueError,
#             AttributeError,
#         ):
#             return True

#         if self._is_protected_system_process(process):
#             return True

#         if self._process_tree_contains_proctor(process):
#             return True

#         if self._is_kiosk_process(process):
#             return True

#         if self._process_tree_contains_kiosk(process):
#             return True

#         return False

#     def _classify_restricted_process(
#         self,
#         process,
#         include_browsers=True,
#         include_media=True,
#         include_remote_access=True,
#         include_screen_sharing=True,
#         include_duplicate_application=True,
#     ):
#         if process is None:
#             return None

#         try:
#             if int(process.pid) == int(self.current_pid):
#                 return None

#         except (
#             TypeError,
#             ValueError,
#             AttributeError,
#         ):
#             return None

#         if not self._is_current_user_process(process):
#             return None

#         if self._is_strict_lockdown_exempt(process):
#             return None

#         process_name = self._safe_process_name(process)

#         executable = self._safe_process_executable(process)

#         if not process_name:
#             return None

#         if (
#             include_duplicate_application
#             and self.terminate_duplicate_app_instances
#             and self._is_same_proctor_application(process)
#         ):
#             return "duplicate_proctor"

#         if (
#             include_remote_access
#             and self.terminate_remote_access
#             and self._is_remote_access(
#                 process_name,
#                 executable,
#             )
#         ):
#             return "remote_access"

#         if (
#             include_screen_sharing
#             and self.terminate_screen_sharing
#             and self._is_screen_sharing(
#                 process_name,
#                 executable,
#             )
#         ):
#             return "screen_sharing"

#         if (
#             include_media
#             and self.terminate_media_processes
#             and self._is_media_process(
#                 process_name,
#                 executable,
#             )
#         ):
#             return "media"

#         if (
#             include_browsers
#             and self.block_external_browsers
#             and self._is_browser(process_name)
#         ):
#             return "browser"

#         return None

#     def _collect_targeted_user_process_roots(
#         self,
#         include_browsers=True,
#         include_media=True,
#         include_remote_access=True,
#         include_screen_sharing=True,
#         include_duplicate_application=True,
#     ):
#         candidates = {}

#         for process in psutil.process_iter(
#             attrs=[
#                 "pid",
#                 "ppid",
#                 "name",
#                 "exe",
#             ]
#         ):
#             try:
#                 category = self._classify_restricted_process(
#                     process=process,
#                     include_browsers=include_browsers,
#                     include_media=include_media,
#                     include_remote_access=include_remote_access,
#                     include_screen_sharing=include_screen_sharing,
#                     include_duplicate_application=include_duplicate_application,
#                 )

#                 if category is None:
#                     continue

#                 target = process

#                 if category == "browser":
#                     root = self._get_browser_root(process)

#                     if root is not None:
#                         target = root

#                 if self._is_strict_lockdown_exempt(target):
#                     continue

#                 if self._process_tree_contains_proctor(target):
#                     continue

#                 if self._is_kiosk_process(target):
#                     continue

#                 if self._process_tree_contains_kiosk(target):
#                     continue

#                 target_pid = int(target.pid)

#                 existing = candidates.get(target_pid)

#                 if existing is None:
#                     candidates[target_pid] = (
#                         target,
#                         category,
#                     )

#                 else:
#                     priority = {
#                         "duplicate_proctor": 5,
#                         "remote_access": 4,
#                         "screen_sharing": 3,
#                         "media": 2,
#                         "browser": 1,
#                     }

#                     if priority.get(
#                         category,
#                         0,
#                     ) > priority.get(
#                         existing[1],
#                         0,
#                     ):
#                         candidates[target_pid] = (
#                             target,
#                             category,
#                         )

#             except (
#                 psutil.NoSuchProcess,
#                 psutil.AccessDenied,
#                 psutil.ZombieProcess,
#                 TypeError,
#                 ValueError,
#             ):
#                 continue

#         if not candidates:
#             return []

#         candidate_pids = set(candidates.keys())

#         roots = []

#         for (
#             _pid,
#             (
#                 process,
#                 category,
#             ),
#         ) in candidates.items():
#             try:
#                 parent_pid = int(process.ppid())

#             except (
#                 psutil.NoSuchProcess,
#                 psutil.AccessDenied,
#                 psutil.ZombieProcess,
#                 TypeError,
#                 ValueError,
#             ):
#                 parent_pid = None

#             if parent_pid in candidate_pids:
#                 parent_category = candidates[parent_pid][1]

#                 if parent_category == category:
#                     continue

#             roots.append(
#                 (
#                     process,
#                     category,
#                 )
#             )

#         return roots

#     def _collect_strict_user_process_roots(
#         self,
#     ):
#         """
#         Backward-compatible private helper.

#         Historically this returned every safe current-user application. It now
#         returns only browser, remote-access, screen-sharing, media/camera/audio,
#         and duplicate-proctor processes so backend/dev processes remain alive.
#         """

#         return [
#             process
#             for (
#                 process,
#                 _category,
#             ) in self._collect_targeted_user_process_roots()
#         ]

#     def _event_type_for_restricted_category(
#         self,
#         category,
#     ):
#         return {
#             "duplicate_proctor": "DUPLICATE_PROCTOR_INSTANCE_DETECTED",
#             "remote_access": "REMOTE_ACCESS_DETECTED",
#             "screen_sharing": "SCREEN_SHARING_DETECTED",
#             "media": "MEDIA_DEVICE_APPLICATION_DETECTED",
#             "browser": "EXTERNAL_BROWSER_DETECTED",
#         }.get(
#             category,
#             "RESTRICTED_PROCESS_DETECTED",
#         )

#     def _terminate_restricted_process(
#         self,
#         process,
#         category,
#     ):
#         event_type = self._event_type_for_restricted_category(category)

#         if self.operating_system == self.WINDOWS:
#             success = self._windows_force_kill_process_tree(
#                 process=process,
#                 event_type=event_type,
#                 require_current_user=True,
#             )

#             if not success and psutil.pid_exists(int(process.pid)):
#                 success = self._terminate_process_tree(
#                     process=process,
#                     event_type=event_type,
#                     require_current_user=True,
#                 )

#             return bool(success)

#         return bool(
#             self._terminate_process_tree(
#                 process=process,
#                 event_type=event_type,
#                 require_current_user=True,
#             )
#         )

#     def terminate_targeted_processes_before_exam(
#         self,
#         max_passes=4,
#         settle_delay=0.20,
#         include_browsers=True,
#         include_media=True,
#         include_remote_access=True,
#         include_screen_sharing=True,
#         include_duplicate_application=True,
#     ):
#         """
#         Close only processes that conflict with a secure proctored session.

#         Normal developer/backend processes such as Node.js, terminals, IDEs,
#         unrelated Python processes and ordinary desktop applications remain
#         untouched. Core operating-system media services also stay protected.
#         """

#         result = {
#             "detected": [],
#             "terminated": [],
#             "failed": [],
#             "passes": 0,
#         }

#         if not self.supported_os:
#             print(
#                 "[PROCESS MONITOR] Targeted pre-exam process cleanup skipped "
#                 "because this operating system is unsupported."
#             )

#             return result

#         try:
#             max_passes = max(
#                 1,
#                 int(max_passes),
#             )

#         except (
#             TypeError,
#             ValueError,
#         ):
#             max_passes = 4

#         try:
#             settle_delay = max(
#                 0.0,
#                 float(settle_delay),
#             )

#         except (
#             TypeError,
#             ValueError,
#         ):
#             settle_delay = 0.20

#         detected_keys = set()

#         terminated_keys = set()

#         print()

#         print(
#             "[PROCESS MONITOR] Targeted pre-exam cleanup started. "
#             "Normal developer/backend processes are preserved."
#         )

#         for pass_number in range(
#             1,
#             max_passes + 1,
#         ):
#             result["passes"] = pass_number

#             targets = self._collect_targeted_user_process_roots(
#                 include_browsers=include_browsers,
#                 include_media=include_media,
#                 include_remote_access=include_remote_access,
#                 include_screen_sharing=include_screen_sharing,
#                 include_duplicate_application=include_duplicate_application,
#             )

#             if not targets:
#                 break

#             print(
#                 "[PROCESS MONITOR] Targeted cleanup pass "
#                 f"{pass_number}/{max_passes} "
#                 f"| restricted_roots={len(targets)}"
#             )

#             terminated_this_pass = 0

#             for (
#                 process,
#                 category,
#             ) in targets:
#                 try:
#                     process_name = process.name()

#                 except (
#                     psutil.NoSuchProcess,
#                     psutil.AccessDenied,
#                     psutil.ZombieProcess,
#                 ):
#                     process_name = ""

#                 executable = self._safe_process_executable(process)

#                 item = {
#                     "pid": int(process.pid),
#                     "process_name": process_name,
#                     "executable": executable,
#                     "category": category,
#                 }

#                 item_key = (
#                     item["pid"],
#                     self._normalize(item["process_name"]),
#                     category,
#                 )

#                 if item_key not in detected_keys:
#                     detected_keys.add(item_key)

#                     result["detected"].append(dict(item))

#                 print(
#                     "[PROCESS MONITOR] Restricted process detected "
#                     f"| category={category} "
#                     f"| process={process_name or 'Unknown'} "
#                     f"| pid={process.pid}"
#                 )

#                 success = self._terminate_restricted_process(
#                     process=process,
#                     category=category,
#                 )

#                 if success or not psutil.pid_exists(int(process.pid)):
#                     terminated_this_pass += 1

#                     if item_key not in terminated_keys:
#                         terminated_keys.add(item_key)

#                         result["terminated"].append(dict(item))

#             if settle_delay > 0.0:
#                 time.sleep(settle_delay)

#             if terminated_this_pass == 0:
#                 break

#         remaining_targets = self._collect_targeted_user_process_roots(
#             include_browsers=include_browsers,
#             include_media=include_media,
#             include_remote_access=include_remote_access,
#             include_screen_sharing=include_screen_sharing,
#             include_duplicate_application=include_duplicate_application,
#         )

#         remaining = []

#         remaining_keys = set()

#         for (
#             process,
#             category,
#         ) in remaining_targets:
#             try:
#                 process_name = process.name()

#             except (
#                 psutil.NoSuchProcess,
#                 psutil.AccessDenied,
#                 psutil.ZombieProcess,
#             ):
#                 process_name = ""

#             item = {
#                 "pid": int(process.pid),
#                 "process_name": process_name,
#                 "executable": self._safe_process_executable(process),
#                 "category": category,
#             }

#             key = (
#                 item["pid"],
#                 self._normalize(item["process_name"]),
#                 category,
#             )

#             if key in remaining_keys:
#                 continue

#             remaining_keys.add(key)

#             remaining.append(item)

#         result["failed"] = remaining

#         print(
#             "[PROCESS MONITOR] Targeted pre-exam cleanup result "
#             f"| detected={len(result['detected'])} "
#             f"| terminated={len(result['terminated'])} "
#             f"| remaining={len(result['failed'])}"
#         )

#         if result["failed"]:
#             for item in result["failed"]:
#                 print(
#                     "[PROCESS MONITOR] Unable to terminate restricted process "
#                     f"| category={item.get('category')} "
#                     f"| process={item.get('process_name')} "
#                     f"| pid={item.get('pid')}"
#                 )

#         return result

#     def terminate_all_user_processes_before_exam(
#         self,
#         max_passes=3,
#         settle_delay=0.25,
#     ):
#         """
#         Backward-compatible legacy entry point.

#         The historical name is intentionally retained, but the implementation
#         now performs targeted lockdown rather than terminating every user app.
#         """

#         return self.terminate_targeted_processes_before_exam(
#             max_passes=max_passes,
#             settle_delay=settle_delay,
#             include_browsers=True,
#             include_media=True,
#             include_remote_access=True,
#             include_screen_sharing=True,
#             include_duplicate_application=True,
#         )

#     def terminate_pre_exam_media_processes(
#         self,
#         include_browsers=True,
#         include_camera_microphone=True,
#         include_audio_playback=True,
#     ):
#         """
#         Backward-compatible entry point used by main.py.

#         Browsers, remote-access/screen-sharing apps, duplicate proctor instances,
#         and user-space camera/microphone/audio applications are closed. Normal
#         backend/development applications such as Node.js remain running.
#         """

#         include_media = bool(include_camera_microphone or include_audio_playback)

#         return self.terminate_targeted_processes_before_exam(
#             max_passes=4,
#             settle_delay=0.20,
#             include_browsers=bool(include_browsers),
#             include_media=include_media,
#             include_remote_access=True,
#             include_screen_sharing=True,
#             include_duplicate_application=True,
#         )

#     def enable_strict_user_process_lockdown(
#         self,
#         enabled=True,
#     ):
#         """
#         Enable/disable continuous targeted lockdown after kiosk startup.

#         The method name remains unchanged for backward compatibility. When
#         enabled, scan_once() continuously removes only restricted categories:
#         external browsers, remote access, screen sharing, media/camera/audio
#         applications, and duplicate proctor instances.
#         """

#         self.strict_user_process_lockdown = bool(enabled)

#         print(
#             "[PROCESS MONITOR] Continuous targeted process lockdown "
#             f"{'enabled' if self.strict_user_process_lockdown else 'disabled'}."
#         )

#         return self.strict_user_process_lockdown

#     def capture_pre_kiosk_browser_processes(
#         self,
#     ):
#         if not self.supported_os:
#             return []

#         browser_roots = set()

#         for process in psutil.process_iter(
#             attrs=[
#                 "pid",
#                 "name",
#             ]
#         ):
#             try:
#                 if process.pid == self.current_pid:
#                     continue

#                 process_name = process.info.get(
#                     "name",
#                     "",
#                 )

#                 if not self._is_browser(process_name):
#                     continue

#                 if not self._is_current_user_process(process):
#                     continue

#                 if self._is_protected_system_process(process):
#                     continue

#                 root = self._get_browser_root(process)

#                 if root is None:
#                     continue

#                 if self._is_kiosk_process(root):
#                     continue

#                 browser_roots.add(root.pid)

#             except (
#                 psutil.NoSuchProcess,
#                 psutil.AccessDenied,
#                 psutil.ZombieProcess,
#             ):
#                 continue

#         with self._lock:
#             self.pre_kiosk_browser_root_pids = set(browser_roots)

#         print(
#             "[PROCESS MONITOR] "
#             "Captured pre-kiosk browser roots: "
#             f"{sorted(browser_roots)}"
#         )

#         return sorted(browser_roots)

#     def terminate_pre_kiosk_browser_processes(
#         self,
#     ):
#         if not self.supported_os:
#             return []

#         with self._lock:
#             kiosk_root_pid = self.kiosk_root_pid

#             browser_root_pids = list(self.pre_kiosk_browser_root_pids)

#         if not kiosk_root_pid:
#             print(
#                 "[PROCESS MONITOR] "
#                 "Pre-kiosk browser termination skipped "
#                 "because the kiosk root PID has not been registered."
#             )

#             return []

#         terminated = []

#         for pid in browser_root_pids:
#             try:
#                 process = psutil.Process(pid)

#             except (
#                 psutil.NoSuchProcess,
#                 psutil.AccessDenied,
#                 psutil.ZombieProcess,
#             ):
#                 continue

#             if self._is_kiosk_process(process):
#                 continue

#             if self._process_tree_contains_kiosk(process):
#                 continue

#             success = self._terminate_process_tree(
#                 process=process,
#                 event_type="LAUNCH_BROWSER_TERMINATED",
#                 require_current_user=True,
#             )

#             if success:
#                 terminated.append(pid)

#         return terminated

#     def scan_once(
#         self,
#     ):
#         if not self.supported_os:
#             return

#         browser_roots_handled = set()

#         with self._lock:
#             kiosk_root_pid = self.kiosk_root_pid

#         if self.strict_user_process_lockdown and kiosk_root_pid:
#             strict_result = self.terminate_all_user_processes_before_exam(
#                 max_passes=1,
#                 settle_delay=0.0,
#             )

#             if strict_result.get("failed"):
#                 print(
#                     "[PROCESS MONITOR] Continuous targeted lockdown "
#                     "could not terminate "
#                     f"{len(strict_result['failed'])} "
#                     "restricted process(es)."
#                 )

#             return

#         for process in psutil.process_iter(
#             attrs=[
#                 "pid",
#                 "name",
#                 "exe",
#             ]
#         ):
#             if self._stop_event.is_set():
#                 return

#             try:
#                 if process.pid == self.current_pid:
#                     continue

#                 process_name = self._normalize(
#                     process.info.get(
#                         "name",
#                         "",
#                     )
#                 )

#                 executable = self._normalize(
#                     process.info.get(
#                         "exe",
#                         "",
#                     )
#                 )

#                 if not process_name:
#                     continue

#                 if self._is_protected_system_process(process):
#                     continue

#                 if self._is_kiosk_process(process):
#                     continue

#                 if (
#                     self.terminate_duplicate_app_instances
#                     and self._is_same_proctor_application(process)
#                 ):
#                     self._terminate_restricted_process(
#                         process=process,
#                         category="duplicate_proctor",
#                     )

#                     continue

#                 if self.terminate_remote_access and self._is_remote_access(
#                     process_name,
#                     executable,
#                 ):
#                     self._terminate_restricted_process(
#                         process=process,
#                         category="remote_access",
#                     )

#                     continue

#                 if self.terminate_screen_sharing and self._is_screen_sharing(
#                     process_name,
#                     executable,
#                 ):
#                     self._terminate_restricted_process(
#                         process=process,
#                         category="screen_sharing",
#                     )

#                     continue

#                 if self.terminate_media_processes and self._is_media_process(
#                     process_name,
#                     executable,
#                 ):
#                     self._terminate_restricted_process(
#                         process=process,
#                         category="media",
#                     )

#                     continue

#                 if self.block_external_browsers and self._is_browser(process_name):
#                     if not kiosk_root_pid:
#                         if not self._warned_missing_kiosk_pid:
#                             print(
#                                 "[PROCESS MONITOR] "
#                                 "External-browser termination "
#                                 "is waiting for the kiosk root PID."
#                             )

#                             self._warned_missing_kiosk_pid = True

#                         continue

#                     root = self._get_browser_root(process)

#                     if root is None:
#                         continue

#                     if root.pid in browser_roots_handled:
#                         continue

#                     browser_roots_handled.add(root.pid)

#                     if self._is_kiosk_process(root):
#                         continue

#                     if self._process_tree_contains_kiosk(root):
#                         continue

#                     self._terminate_restricted_process(
#                         process=root,
#                         category="browser",
#                     )

#             except (
#                 psutil.NoSuchProcess,
#                 psutil.AccessDenied,
#                 psutil.ZombieProcess,
#             ):
#                 continue

#             except Exception as error:
#                 print(
#                     "[PROCESS MONITOR] Scan error:",
#                     error,
#                 )

#     def _run(
#         self,
#     ):
#         print("[PROCESS MONITOR] Started.")

#         while not self._stop_event.is_set():
#             try:
#                 self.scan_once()

#             except Exception as error:
#                 print(
#                     "[PROCESS MONITOR] Scan failed:",
#                     error,
#                 )

#             self._stop_event.wait(self.check_interval)

#         print("[PROCESS MONITOR] Stopped.")

#     def start(
#         self,
#     ):
#         if not self.supported_os:
#             print(
#                 "[PROCESS MONITOR] Monitor was not started because "
#                 "this operating system is not supported."
#             )

#             return False

#         with self._lock:
#             if self._thread is not None and self._thread.is_alive():
#                 return False

#             self._stop_event.clear()

#             self._thread = threading.Thread(
#                 target=self._run,
#                 name="SkolariqProcessMonitor",
#                 daemon=True,
#             )

#             self._thread.start()

#         return True

#     def stop(
#         self,
#         timeout=3.0,
#     ):
#         self._stop_event.set()

#         thread = self._thread

#         if (
#             thread is not None
#             and thread.is_alive()
#             and thread is not threading.current_thread()
#         ):
#             thread.join(
#                 timeout=max(
#                     0.0,
#                     float(timeout),
#                 )
#             )

#         with self._lock:
#             self._thread = None

#         return True

#     def close(
#         self,
#     ):
#         return self.stop()

import os
import platform
import subprocess
import threading
import time
from datetime import datetime, timezone
from socket.proctor_socket import ProctorSocket

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
            "msedgewebview2.exe",
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
            "applicationframehost.exe",
            "runtimebroker.exe",
            "searchapp.exe",
            "textinputhost.exe",
            "lockapp.exe",
            "shellhost.exe",
            "securityhealthsystray.exe",
            "widgets.exe",
            "widgetservice.exe",
            "dllhost.exe",
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
            "distnoted",
            "usernoted",
            "notificationcenter",
            "spotlight",
            "mds",
            "mdworker",
            "mdworker_shared",
            "coreservicesuiagent",
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
            "xdg-desktop-portal",
            "xdg-desktop-portal-gtk",
            "xdg-desktop-portal-gnome",
            "xdg-document-portal",
            "gvfsd",
            "gvfsd-fuse",
            "at-spi-bus-launcher",
            "gsettings-helper",
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
        WINDOWS: {
            "zoomsharing",
            "\\screenshare",
            "\\screen_share",
        },
        MACOS: {
            "/screen sharing.app/",
            "zoomsharing",
            "/screenshare",
            "/screen_share",
        },
        LINUX: {
            "zoomsharing",
            "/screenshare",
            "/screen_share",
        },
    }

    OS_MEDIA_PROCESS_NAMES = {
        WINDOWS: {
            "windowscamera.exe",
            "camera.exe",
            "microsoft.windows.camera.exe",
            "soundrecorder.exe",
            "voicerecorder.exe",
            "audacity.exe",
            "obs64.exe",
            "obs32.exe",
            "obs.exe",
            "streamlabs.exe",
            "streamlabs desktop.exe",
            "zoom.exe",
            "teams.exe",
            "ms-teams.exe",
            "skype.exe",
            "skypeapp.exe",
            "discord.exe",
            "webex.exe",
            "webexmta.exe",
            "ciscowebexstart.exe",
            "slack.exe",
            "loom.exe",
            "loom desktop.exe",
            "snippingtool.exe",
            "gamebar.exe",
            "gamebarftserver.exe",
            "vlc.exe",
            "wmplayer.exe",
            "spotify.exe",
            "itunes.exe",
            "musicbee.exe",
            "foobar2000.exe",
            "potplayermini.exe",
            "potplayermini64.exe",
            "mpv.exe",
            "ffmpeg.exe",
            "ffplay.exe",
        },
        MACOS: {
            "photo booth",
            "facetime",
            "quicktime player",
            "voice memos",
            "audacity",
            "obs",
            "obs studio",
            "streamlabs",
            "zoom.us",
            "zoom",
            "microsoft teams",
            "teams",
            "discord",
            "skype",
            "webex",
            "slack",
            "loom",
            "vlc",
            "spotify",
            "itunes",
            "music",
            "ffmpeg",
            "ffplay",
        },
        LINUX: {
            "cheese",
            "guvcview",
            "kamoso",
            "audacity",
            "obs",
            "obs-studio",
            "simplescreenrecorder",
            "vokoscreenng",
            "zoom",
            "teams",
            "teams-for-linux",
            "discord",
            "skypeforlinux",
            "webex",
            "slack",
            "loom",
            "vlc",
            "spotify",
            "mpv",
            "ffmpeg",
            "ffplay",
            "arecord",
            "aplay",
            "parec",
            "paplay",
            "pw-record",
            "pw-play",
        },
    }

    OS_MEDIA_PATH_KEYWORDS = {
        WINDOWS: {
            "\\windowscamera\\",
            "\\camera\\",
            "\\soundrecorder\\",
            "\\voicerecorder\\",
            "\\audacity\\",
            "\\obs studio\\",
            "\\obs-studio\\",
            "\\streamlabs\\",
            "\\zoom\\",
            "\\teams\\",
            "\\microsoft teams\\",
            "\\discord\\",
            "\\skype\\",
            "\\webex\\",
            "\\slack\\",
            "\\loom\\",
            "\\vlc\\",
            "\\spotify\\",
            "\\foobar2000\\",
            "\\potplayer\\",
        },
        MACOS: {
            "/photo booth.app/",
            "/facetime.app/",
            "/quicktime player.app/",
            "/voice memos.app/",
            "/audacity.app/",
            "/obs.app/",
            "/streamlabs",
            "/zoom.us.app/",
            "/microsoft teams.app/",
            "/discord.app/",
            "/skype.app/",
            "/webex.app/",
            "/slack.app/",
            "/loom.app/",
            "/vlc.app/",
            "/spotify.app/",
        },
        LINUX: {
            "/cheese",
            "/guvcview",
            "/kamoso",
            "/audacity",
            "/obs",
            "/obs-studio",
            "/simplescreenrecorder",
            "/vokoscreen",
            "/zoom",
            "/teams",
            "/discord",
            "/skype",
            "/webex",
            "/slack",
            "/loom",
            "/vlc",
            "/spotify",
            "/ffmpeg",
            "/ffplay",
        },
    }

    MEDIA_PROCESS_NAMES = set().union(*OS_MEDIA_PROCESS_NAMES.values())

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
        strict_user_process_lockdown=False,
        terminate_media_processes=True,
        terminate_duplicate_app_instances=True,
        frontend_event_callback=None,
    ):
        self.current_pid = os.getpid()

        self.operating_system = platform.system()

        self.supported_os = self.operating_system in {
            self.WINDOWS,
            self.MACOS,
            self.LINUX,
        }

        self.check_interval = max(
            1.0,
            float(check_interval),
        )

        self.block_external_browsers = bool(block_external_browsers)

        self.terminate_remote_access = bool(terminate_remote_access)

        self.terminate_screen_sharing = bool(terminate_screen_sharing)

        self.strict_user_process_lockdown = bool(strict_user_process_lockdown)

        self.terminate_media_processes = bool(terminate_media_processes)

        self.terminate_duplicate_app_instances = bool(terminate_duplicate_app_instances)

        self.event_callback = event_callback

        # Optional frontend-safe event callback. Unlike event_callback, this
        # callback receives ONLY a human-readable message payload:
        # {"message": "..."}
        # No PID, executable path, session ID, timestamp, category, or other
        # diagnostic information is exposed through this callback.
        self.frontend_event_callback = frontend_event_callback

        self._frontend_event_lock = threading.RLock()
        self._frontend_last_message_times = {}
        self._frontend_event_cooldown_seconds = 1.5

        self.kiosk_root_pid = None

        self.pre_kiosk_browser_root_pids = set()

        self._stop_event = threading.Event()

        self._thread = None

        self._lock = threading.RLock()

        self._warned_missing_kiosk_pid = False

        self.browser_process_names = set(
            self.OS_BROWSER_PROCESS_NAMES.get(
                self.operating_system,
                set(),
            )
        )

        self.remote_access_process_names = set(
            self.OS_REMOTE_ACCESS_PROCESS_NAMES.get(
                self.operating_system,
                set(),
            )
        )

        self.screen_sharing_process_names = set(
            self.OS_SCREEN_SHARING_PROCESS_NAMES.get(
                self.operating_system,
                set(),
            )
        )

        self.media_process_names = set(
            self.OS_MEDIA_PROCESS_NAMES.get(
                self.operating_system,
                set(),
            )
        )

        self.protected_system_process_names = set(
            self.OS_PROTECTED_SYSTEM_PROCESS_NAMES.get(
                self.operating_system,
                set(),
            )
        )

        self.remote_access_path_keywords = set(
            self.OS_REMOTE_ACCESS_PATH_KEYWORDS.get(
                self.operating_system,
                set(),
            )
        )

        self.screen_sharing_path_keywords = set(
            self.OS_SCREEN_SHARING_PATH_KEYWORDS.get(
                self.operating_system,
                set(),
            )
        )

        self.media_path_keywords = set(
            self.OS_MEDIA_PATH_KEYWORDS.get(
                self.operating_system,
                set(),
            )
        )

        self.current_username = ""

        self.current_process_name = ""

        self.current_executable = ""

        self.current_cmdline = []

        self.current_cwd = ""

        self.current_python_entrypoint = None

        try:
            current_process = psutil.Process(self.current_pid)

            self.current_username = self._normalize(current_process.username())

            self.current_process_name = self._normalize(current_process.name())

            self.current_executable = self._normalize_path(current_process.exe())

            try:
                self.current_cmdline = list(current_process.cmdline() or [])

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess,
            ):
                self.current_cmdline = []

            try:
                self.current_cwd = self._normalize_path(current_process.cwd())

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess,
            ):
                self.current_cwd = ""

            self.current_python_entrypoint = self._extract_python_entrypoint(
                self.current_cmdline,
                self.current_cwd,
            )

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
        ):
            self.current_username = ""

        print(
            "[PROCESS MONITOR] Operating system detected: "
            f"{self.operating_system or 'Unknown'}."
        )

        if not self.supported_os:
            print(
                "[PROCESS MONITOR] Unsupported operating system. "
                "Automatic process termination is disabled."
            )

        if kiosk_root_pid is not None:
            self.set_kiosk_root_pid(kiosk_root_pid)

    def _normalize(
        self,
        value,
    ):
        return str(value or "").strip().lower()

    def _normalize_path(
        self,
        value,
    ):
        value = str(value or "").strip()

        if not value:
            return ""

        try:
            return os.path.normcase(os.path.abspath(value))

        except Exception:
            return os.path.normcase(value)

    def _safe_process_executable(
        self,
        process,
    ):
        try:
            return self._normalize_path(process.exe())

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
        ):
            return ""

    def _safe_process_cmdline(
        self,
        process,
    ):
        try:
            return list(process.cmdline() or [])

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
        ):
            return []

    def _safe_process_cwd(
        self,
        process,
    ):
        try:
            return self._normalize_path(process.cwd())

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
        ):
            return ""

    def _is_python_runtime_name(
        self,
        process_name,
    ):
        process_name = self._normalize(process_name)

        if not process_name:
            return False

        python_names = {
            "python",
            "python.exe",
            "pythonw",
            "pythonw.exe",
            "python3",
            "python3.exe",
        }

        if process_name in python_names:
            return True

        return process_name.startswith("python")

    def _extract_python_entrypoint(
        self,
        cmdline,
        cwd="",
    ):
        if not isinstance(
            cmdline,
            (
                list,
                tuple,
            ),
        ):
            return None

        tokens = [
            str(item or "").strip() for item in cmdline if str(item or "").strip()
        ]

        if not tokens:
            return None

        for (
            index,
            token,
        ) in enumerate(tokens):
            normalized_token = self._normalize(token)

            if normalized_token == "-m" and index + 1 < len(tokens):
                module_name = self._normalize(tokens[index + 1])

                if module_name:
                    return (
                        "module",
                        module_name,
                    )

            if normalized_token.startswith("-m") and len(normalized_token) > 2:
                module_name = normalized_token[2:].strip()

                if module_name:
                    return (
                        "module",
                        module_name,
                    )

        for token in tokens[1:]:
            token_text = str(token).strip().strip('"').strip("'")

            if not token_text.lower().endswith(".py"):
                continue

            if os.path.isabs(token_text):
                script_path = self._normalize_path(token_text)

            else:
                base_cwd = self._normalize_path(cwd)

                script_path = self._normalize_path(
                    os.path.join(
                        base_cwd or os.getcwd(),
                        token_text,
                    )
                )

            if script_path:
                return (
                    "script",
                    script_path,
                )

        return None

    def _is_same_proctor_application(
        self,
        process,
    ):
        """
        Return True only for another instance of this same proctor app.

        Packaged builds are matched by executable identity. Development Python
        launches are matched by entrypoint (for example, `python -m src.main`),
        never by python.exe alone, so unrelated Python processes stay allowed.
        """

        if process is None:
            return False

        try:
            candidate_pid = int(process.pid)

        except (
            TypeError,
            ValueError,
            AttributeError,
        ):
            return False

        if candidate_pid == int(self.current_pid):
            return False

        if not self._is_current_user_process(process):
            return False

        candidate_name = self._safe_process_name(process)

        candidate_executable = self._safe_process_executable(process)

        candidate_cmdline = self._safe_process_cmdline(process)

        candidate_cwd = self._safe_process_cwd(process)

        candidate_entrypoint = self._extract_python_entrypoint(
            candidate_cmdline,
            candidate_cwd,
        )

        current_entrypoint = self.current_python_entrypoint

        if current_entrypoint is not None and candidate_entrypoint is not None:
            if candidate_entrypoint == current_entrypoint:
                return True

            (
                current_kind,
                current_value,
            ) = current_entrypoint

            (
                candidate_kind,
                candidate_value,
            ) = candidate_entrypoint

            module_script_pairs = {
                (
                    "src.main",
                    "src/main.py",
                ),
            }

            if current_kind == "module" and candidate_kind == "script":
                candidate_script = (
                    str(candidate_value)
                    .replace(
                        "\\",
                        "/",
                    )
                    .lower()
                )

                if any(
                    (
                        current_value == module_name
                        and candidate_script.endswith(script_suffix)
                    )
                    for (
                        module_name,
                        script_suffix,
                    ) in module_script_pairs
                ):
                    return True

            if current_kind == "script" and candidate_kind == "module":
                current_script = (
                    str(current_value)
                    .replace(
                        "\\",
                        "/",
                    )
                    .lower()
                )

                if any(
                    (
                        candidate_value == module_name
                        and current_script.endswith(script_suffix)
                    )
                    for (
                        module_name,
                        script_suffix,
                    ) in module_script_pairs
                ):
                    return True

        current_name = self._normalize(self.current_process_name)

        current_executable = self._normalize_path(self.current_executable)

        if (
            current_executable
            and candidate_executable
            and current_executable == candidate_executable
            and not self._is_python_runtime_name(current_name)
        ):
            return True

        if (
            current_name
            and candidate_name == current_name
            and ("skolariq" in current_name or "proctor" in current_name)
        ):
            if (
                not current_executable
                or not candidate_executable
                or candidate_executable == current_executable
            ):
                return True

        return False

    def _is_media_process(
        self,
        process_name,
        executable="",
    ):
        process_name = self._normalize(process_name)

        if process_name in self.media_process_names:
            return True

        if self._path_matches(
            executable,
            self.media_path_keywords,
        ):
            return True

        generic_keywords = {
            "camera",
            "webcam",
            "voice recorder",
            "voicerecorder",
            "sound recorder",
            "soundrecorder",
            "screen recorder",
            "screenrecorder",
            "audacity",
            "obs",
            "streamlabs",
            "zoom",
            "teams",
            "skype",
            "discord",
            "webex",
            "loom",
            "vlc",
            "spotify",
        }

        return any(keyword in process_name for keyword in generic_keywords)

    def _safe_process_name(
        self,
        process,
    ):
        try:
            return self._normalize(process.name())

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
        ):
            return ""

    def _path_matches(
        self,
        executable,
        keywords,
    ):
        executable = self._normalize(executable)

        if not executable:
            return False

        for keyword in keywords:
            keyword = self._normalize(keyword)

            if keyword and keyword in executable:
                return True

        return False

    def _is_browser(
        self,
        process_name,
    ):
        return self._normalize(process_name) in self.browser_process_names

    def _is_remote_access(
        self,
        process_name,
        executable="",
    ):
        process_name = self._normalize(process_name)

        if process_name in self.remote_access_process_names:
            return True

        return self._path_matches(
            executable,
            self.remote_access_path_keywords,
        )

    def _is_screen_sharing(
        self,
        process_name,
        executable="",
    ):
        process_name = self._normalize(process_name)

        if process_name in self.screen_sharing_process_names:
            return True

        return self._path_matches(
            executable,
            self.screen_sharing_path_keywords,
        )

    def _is_current_user_process(
        self,
        process,
    ):
        if not self.current_username:
            return False

        try:
            process_username = self._normalize(process.username())

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
        ):
            return False

        return process_username == self.current_username

    def _is_system_owned_process(
        self,
        process,
    ):
        try:
            username = self._normalize(process.username())

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
        ):
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

    def _is_protected_system_process(
        self,
        process,
    ):
        protected_pids = {
            0,
            1,
            self.current_pid,
        }

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

    def _is_descendant_of(
        self,
        process,
        ancestor_pid,
    ):
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

    def _is_kiosk_process(
        self,
        process,
    ):
        with self._lock:
            kiosk_root_pid = self.kiosk_root_pid

        if not kiosk_root_pid:
            return False

        return self._is_descendant_of(
            process,
            kiosk_root_pid,
        )

    def _process_tree_contains_kiosk(
        self,
        process,
    ):
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

    def _get_browser_root(
        self,
        process,
    ):
        current = process

        root = process

        visited = set()

        while current is not None:
            if current.pid in visited:
                break

            visited.add(current.pid)

            try:
                current_name = current.name()

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess,
            ):
                break

            if not self._is_browser(current_name):
                break

            root = current

            try:
                parent = current.parent()

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess,
            ):
                break

            if parent is None:
                break

            try:
                parent_name = parent.name()

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess,
            ):
                break

            if not self._is_browser(parent_name):
                break

            current = parent

        return root

    def _build_event(
        self,
        event_type,
        process,
        action,
        reason=None,
    ):
        try:
            process_name = process.name()

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
        ):
            process_name = ""

        try:
            executable = process.exe()

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
        ):
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

    def _emit_event(
        self,
        payload,
    ):
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
            print(
                "[PROCESS MONITOR] Callback error:",
                error,
            )

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

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
        ):
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

            except (
                psutil.NoSuchProcess,
                psutil.ZombieProcess,
            ):
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

            except (
                psutil.NoSuchProcess,
                psutil.ZombieProcess,
            ):
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

    def set_kiosk_root_pid(
        self,
        kiosk_root_pid,
    ):
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

        print("[PROCESS MONITOR] " f"Kiosk root PID set to {kiosk_root_pid}.")

    def _process_tree_contains_proctor(
        self,
        process,
    ):
        """
        Return True when `process` is this proctor process or an ancestor of it.

        This is critical on Windows because native `taskkill /T` kills an entire
        descendant tree. We must never target cmd.exe / powershell.exe / a launcher
        process when that tree currently contains this running proctor instance.
        """

        if process is None:
            return True

        try:
            target_pid = int(process.pid)

        except (
            TypeError,
            ValueError,
            AttributeError,
        ):
            return True

        if target_pid == int(self.current_pid):
            return True

        try:
            current = psutil.Process(int(self.current_pid))

            visited = set()

            while current is not None:
                if current.pid in visited:
                    break

                visited.add(current.pid)

                if int(current.pid) == target_pid:
                    return True

                current = current.parent()

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
        ):
            return False

        return False

    def _windows_force_kill_process_tree(
        self,
        process,
        event_type,
        require_current_user=True,
    ):
        """
        Force-close a Windows process tree using taskkill /F /T.

        psutil terminate()/kill() is retained as the normal cross-platform path,
        but Chromium/Electron/WebView trees can be more reliably closed by the
        native Windows process-tree command.
        """

        if self.operating_system != self.WINDOWS:
            return False

        try:
            process = psutil.Process(int(process.pid))

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
            TypeError,
            ValueError,
        ):
            return True

        if self._is_protected_system_process(process):
            return False

        if self._process_tree_contains_proctor(process):
            return False

        if self._is_kiosk_process(process):
            return False

        if self._process_tree_contains_kiosk(process):
            return False

        if require_current_user and not self._is_current_user_process(process):
            return False

        pid = int(process.pid)

        try:
            process_name = process.name()

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
        ):
            process_name = ""

        creationflags = getattr(
            subprocess,
            "CREATE_NO_WINDOW",
            0,
        )

        try:
            completed = subprocess.run(
                [
                    "taskkill",
                    "/PID",
                    str(pid),
                    "/T",
                    "/F",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=6.0,
                creationflags=creationflags,
                check=False,
            )

        except Exception as error:
            self._emit_event(
                {
                    "event_type": event_type,
                    "process_name": process_name,
                    "pid": pid,
                    "executable": "",
                    "action": "native_force_kill_error",
                    "operating_system": self.operating_system,
                    "captured_at": datetime.now(timezone.utc).isoformat(),
                    "reason": str(error),
                }
            )

            return False

        deadline = time.monotonic() + 2.0

        while time.monotonic() < deadline:
            if not psutil.pid_exists(pid):
                break

            time.sleep(0.05)

        terminated = not psutil.pid_exists(pid)

        self._emit_event(
            {
                "event_type": event_type,
                "process_name": process_name,
                "pid": pid,
                "executable": "",
                "action": (
                    "terminated_native" if terminated else "native_force_kill_failed"
                ),
                "operating_system": self.operating_system,
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "reason": (
                    (completed.stderr or completed.stdout or "").strip()
                    if not terminated
                    else None
                ),
            }
        )

        return terminated

    def _collect_browser_roots_for_forced_cleanup(
        self,
    ):
        """
        Collect unique current-user browser roots before the exam.
        """

        roots = {}

        for process in psutil.process_iter(
            attrs=[
                "pid",
                "name",
                "exe",
            ]
        ):
            try:
                if process.pid == self.current_pid:
                    continue

                process_name = self._normalize(
                    process.info.get(
                        "name",
                        "",
                    )
                )

                if not process_name:
                    continue

                if not self._is_browser(process_name):
                    continue

                if not self._is_current_user_process(process):
                    continue

                if self._is_protected_system_process(process):
                    continue

                root = self._get_browser_root(process)

                if root is None:
                    root = process

                if self._process_tree_contains_proctor(root):
                    continue

                if self._is_kiosk_process(root):
                    continue

                if self._process_tree_contains_kiosk(root):
                    continue

                roots[int(root.pid)] = root

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess,
            ):
                continue

        return list(roots.values())

    def terminate_all_browsers_before_exam(
        self,
        max_passes=4,
        settle_delay=0.20,
    ):
        """
        Force-close every current-user browser process tree before hardware opens.

        On Windows this uses taskkill /F /T first. This is intentionally stronger
        than psutil-only termination and closes renderer/audio processes belonging
        to YouTube, Spotify Web, Meet, web cameras, etc.
        """

        result = {
            "detected": [],
            "terminated": [],
            "failed": [],
        }

        seen = set()

        for _ in range(
            max(
                1,
                int(max_passes),
            )
        ):
            roots = self._collect_browser_roots_for_forced_cleanup()

            if not roots:
                break

            terminated_this_pass = 0

            for root in roots:
                try:
                    name = root.name()

                except (
                    psutil.NoSuchProcess,
                    psutil.AccessDenied,
                    psutil.ZombieProcess,
                ):
                    name = ""

                item = {
                    "pid": int(root.pid),
                    "process_name": name,
                    "category": "browser",
                }

                key = (
                    item["pid"],
                    self._normalize(name),
                )

                if key not in seen:
                    seen.add(key)

                    result["detected"].append(dict(item))

                if self.operating_system == self.WINDOWS:
                    success = self._windows_force_kill_process_tree(
                        process=root,
                        event_type="PRE_EXAM_BROWSER_FORCE_TERMINATED",
                        require_current_user=True,
                    )

                else:
                    success = self._terminate_process_tree(
                        process=root,
                        event_type="PRE_EXAM_BROWSER_FORCE_TERMINATED",
                        require_current_user=True,
                    )

                final_success = bool(success or not psutil.pid_exists(int(root.pid)))

                self._emit_frontend_restricted_result(
                    category="browser",
                    terminated=final_success,
                )

                if final_success:
                    terminated_this_pass += 1

                    result["terminated"].append(dict(item))

            if settle_delay > 0:
                time.sleep(float(settle_delay))

            if terminated_this_pass == 0:
                break

        remaining = self._collect_browser_roots_for_forced_cleanup()

        for root in remaining:
            try:
                name = root.name()

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess,
            ):
                name = ""

            result["failed"].append(
                {
                    "pid": int(root.pid),
                    "process_name": name,
                    "category": "browser",
                }
            )

        return result

    def _is_strict_lockdown_exempt(
        self,
        process,
    ):
        """
        Return True when a process must never be terminated by strict lockdown.

        Protected:
        - this Python proctor process,
        - protected/system-owned processes,
        - the active secure kiosk process tree,
        - any process tree that contains the secure kiosk.
        """

        if process is None:
            return True

        try:
            if int(process.pid) == int(self.current_pid):
                return True

        except (
            TypeError,
            ValueError,
            AttributeError,
        ):
            return True

        if self._is_protected_system_process(process):
            return True

        if self._process_tree_contains_proctor(process):
            return True

        if self._is_kiosk_process(process):
            return True

        if self._process_tree_contains_kiosk(process):
            return True

        return False

    def _classify_restricted_process(
        self,
        process,
        include_browsers=True,
        include_media=True,
        include_remote_access=True,
        include_screen_sharing=True,
        include_duplicate_application=True,
    ):
        if process is None:
            return None

        try:
            if int(process.pid) == int(self.current_pid):
                return None

        except (
            TypeError,
            ValueError,
            AttributeError,
        ):
            return None

        if not self._is_current_user_process(process):
            return None

        if self._is_strict_lockdown_exempt(process):
            return None

        process_name = self._safe_process_name(process)

        executable = self._safe_process_executable(process)

        if not process_name:
            return None

        if (
            include_duplicate_application
            and self.terminate_duplicate_app_instances
            and self._is_same_proctor_application(process)
        ):
            return "duplicate_proctor"

        if (
            include_remote_access
            and self.terminate_remote_access
            and self._is_remote_access(
                process_name,
                executable,
            )
        ):
            return "remote_access"

        if (
            include_screen_sharing
            and self.terminate_screen_sharing
            and self._is_screen_sharing(
                process_name,
                executable,
            )
        ):
            return "screen_sharing"

        if (
            include_media
            and self.terminate_media_processes
            and self._is_media_process(
                process_name,
                executable,
            )
        ):
            return "media"

        if (
            include_browsers
            and self.block_external_browsers
            and self._is_browser(process_name)
        ):
            return "browser"

        return None

    def _collect_targeted_user_process_roots(
        self,
        include_browsers=True,
        include_media=True,
        include_remote_access=True,
        include_screen_sharing=True,
        include_duplicate_application=True,
    ):
        candidates = {}

        for process in psutil.process_iter(
            attrs=[
                "pid",
                "ppid",
                "name",
                "exe",
            ]
        ):
            try:
                category = self._classify_restricted_process(
                    process=process,
                    include_browsers=include_browsers,
                    include_media=include_media,
                    include_remote_access=include_remote_access,
                    include_screen_sharing=include_screen_sharing,
                    include_duplicate_application=include_duplicate_application,
                )

                if category is None:
                    continue

                target = process

                if category == "browser":
                    root = self._get_browser_root(process)

                    if root is not None:
                        target = root

                if self._is_strict_lockdown_exempt(target):
                    continue

                if self._process_tree_contains_proctor(target):
                    continue

                if self._is_kiosk_process(target):
                    continue

                if self._process_tree_contains_kiosk(target):
                    continue

                target_pid = int(target.pid)

                existing = candidates.get(target_pid)

                if existing is None:
                    candidates[target_pid] = (
                        target,
                        category,
                    )

                else:
                    priority = {
                        "duplicate_proctor": 5,
                        "remote_access": 4,
                        "screen_sharing": 3,
                        "media": 2,
                        "browser": 1,
                    }

                    if priority.get(
                        category,
                        0,
                    ) > priority.get(
                        existing[1],
                        0,
                    ):
                        candidates[target_pid] = (
                            target,
                            category,
                        )

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess,
                TypeError,
                ValueError,
            ):
                continue

        if not candidates:
            return []

        candidate_pids = set(candidates.keys())

        roots = []

        for (
            _pid,
            (
                process,
                category,
            ),
        ) in candidates.items():
            try:
                parent_pid = int(process.ppid())

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess,
                TypeError,
                ValueError,
            ):
                parent_pid = None

            if parent_pid in candidate_pids:
                parent_category = candidates[parent_pid][1]

                if parent_category == category:
                    continue

            roots.append(
                (
                    process,
                    category,
                )
            )

        return roots

    def _collect_strict_user_process_roots(
        self,
    ):
        """
        Backward-compatible private helper.

        Historically this returned every safe current-user application. It now
        returns only browser, remote-access, screen-sharing, media/camera/audio,
        and duplicate-proctor processes so backend/dev processes remain alive.
        """

        return [
            process
            for (
                process,
                _category,
            ) in self._collect_targeted_user_process_roots()
        ]

    def _event_type_for_restricted_category(
        self,
        category,
    ):
        return {
            "duplicate_proctor": "DUPLICATE_PROCTOR_INSTANCE_DETECTED",
            "remote_access": "REMOTE_ACCESS_DETECTED",
            "screen_sharing": "SCREEN_SHARING_DETECTED",
            "media": "MEDIA_DEVICE_APPLICATION_DETECTED",
            "browser": "EXTERNAL_BROWSER_DETECTED",
        }.get(
            category,
            "RESTRICTED_PROCESS_DETECTED",
        )

    def _frontend_message_for_restricted_process(
        self,
        category,
        terminated,
    ):
        """
        Build the only process-monitor text intended for the assessment UI.

        Important privacy/safety rule:
        - no PID
        - no executable path
        - no username
        - no process identifier
        - no session/exam/schedule identifier
        - no timestamp
        - no raw diagnostic payload
        """

        category = self._normalize(category)

        if category == "duplicate_proctor":
            subject = "Another Skolariq Proctor instance"

        elif category == "remote_access":
            subject = "A remote-access application"

        elif category == "screen_sharing":
            subject = "A screen-sharing application"

        elif category == "media":
            subject = "A camera, microphone, recording, or media application"

        elif category == "browser":
            subject = "An external browser"

        else:
            subject = "A restricted application"

        if terminated:
            return f"{subject} was detected and closed for exam security."

        return (
            f"{subject} was detected but could not be closed. "
            "Please close it before continuing the assessment."
        )

    def _emit_frontend_process_message(
        self,
        message,
    ):
        """
        Emit a minimal frontend-safe process-monitor event.

        The callback payload intentionally contains one field only:
            {"message": "human readable text"}
        """

        message = str(message or "").strip()

        if not message or not callable(self.frontend_event_callback):
            return False

        now = time.monotonic()

        with self._frontend_event_lock:
            last_time = self._frontend_last_message_times.get(message)

            if (
                last_time is not None
                and now - last_time < self._frontend_event_cooldown_seconds
            ):
                return False

            self._frontend_last_message_times[message] = now

            # Keep the tiny deduplication cache bounded.
            if len(self._frontend_last_message_times) > 32:
                cutoff = now - 60.0
                self._frontend_last_message_times = {
                    key: value
                    for key, value in self._frontend_last_message_times.items()
                    if value >= cutoff
                }

        try:
            self.frontend_event_callback(
                {
                    "message": message,
                }
            )

            return True

        except Exception as error:
            print(
                "[PROCESS MONITOR] Frontend event callback error:",
                error,
            )

            return False

    def _emit_frontend_restricted_result(
        self,
        category,
        terminated,
    ):
        return self._emit_frontend_process_message(
            self._frontend_message_for_restricted_process(
                category=category,
                terminated=bool(terminated),
            )
        )

    def _terminate_restricted_process(
        self,
        process,
        category,
    ):
        event_type = self._event_type_for_restricted_category(category)

        success = False

        try:
            if self.operating_system == self.WINDOWS:
                success = self._windows_force_kill_process_tree(
                    process=process,
                    event_type=event_type,
                    require_current_user=True,
                )

                if not success:
                    try:
                        process_still_exists = psutil.pid_exists(int(process.pid))
                    except Exception:
                        process_still_exists = False

                    if process_still_exists:
                        success = self._terminate_process_tree(
                            process=process,
                            event_type=event_type,
                            require_current_user=True,
                        )

            else:
                success = self._terminate_process_tree(
                    process=process,
                    event_type=event_type,
                    require_current_user=True,
                )

            try:
                process_still_exists = psutil.pid_exists(int(process.pid))
            except Exception:
                process_still_exists = False

            final_success = bool(success or not process_still_exists)

            self._emit_frontend_restricted_result(
                category=category,
                terminated=final_success,
            )

            return final_success

        except Exception:
            self._emit_frontend_restricted_result(
                category=category,
                terminated=False,
            )

            raise

    def terminate_targeted_processes_before_exam(
        self,
        max_passes=4,
        settle_delay=0.20,
        include_browsers=True,
        include_media=True,
        include_remote_access=True,
        include_screen_sharing=True,
        include_duplicate_application=True,
    ):
        """
        Close only processes that conflict with a secure proctored session.

        Normal developer/backend processes such as Node.js, terminals, IDEs,
        unrelated Python processes and ordinary desktop applications remain
        untouched. Core operating-system media services also stay protected.
        """

        result = {
            "detected": [],
            "terminated": [],
            "failed": [],
            "passes": 0,
        }

        if not self.supported_os:
            print(
                "[PROCESS MONITOR] Targeted pre-exam process cleanup skipped "
                "because this operating system is unsupported."
            )

            return result

        try:
            max_passes = max(
                1,
                int(max_passes),
            )

        except (
            TypeError,
            ValueError,
        ):
            max_passes = 4

        try:
            settle_delay = max(
                0.0,
                float(settle_delay),
            )

        except (
            TypeError,
            ValueError,
        ):
            settle_delay = 0.20

        detected_keys = set()

        terminated_keys = set()

        print()

        print(
            "[PROCESS MONITOR] Targeted pre-exam cleanup started. "
            "Normal developer/backend processes are preserved."
        )

        for pass_number in range(
            1,
            max_passes + 1,
        ):
            result["passes"] = pass_number

            targets = self._collect_targeted_user_process_roots(
                include_browsers=include_browsers,
                include_media=include_media,
                include_remote_access=include_remote_access,
                include_screen_sharing=include_screen_sharing,
                include_duplicate_application=include_duplicate_application,
            )

            if not targets:
                break

            print(
                "[PROCESS MONITOR] Targeted cleanup pass "
                f"{pass_number}/{max_passes} "
                f"| restricted_roots={len(targets)}"
            )

            terminated_this_pass = 0

            for (
                process,
                category,
            ) in targets:
                try:
                    process_name = process.name()

                except (
                    psutil.NoSuchProcess,
                    psutil.AccessDenied,
                    psutil.ZombieProcess,
                ):
                    process_name = ""

                executable = self._safe_process_executable(process)

                item = {
                    "pid": int(process.pid),
                    "process_name": process_name,
                    "executable": executable,
                    "category": category,
                }

                item_key = (
                    item["pid"],
                    self._normalize(item["process_name"]),
                    category,
                )

                if item_key not in detected_keys:
                    detected_keys.add(item_key)

                    result["detected"].append(dict(item))

                print(
                    "[PROCESS MONITOR] Restricted process detected "
                    f"| category={category} "
                    f"| process={process_name or 'Unknown'} "
                    f"| pid={process.pid}"
                )

                success = self._terminate_restricted_process(
                    process=process,
                    category=category,
                )

                if success or not psutil.pid_exists(int(process.pid)):
                    terminated_this_pass += 1

                    if item_key not in terminated_keys:
                        terminated_keys.add(item_key)

                        result["terminated"].append(dict(item))

            if settle_delay > 0.0:
                time.sleep(settle_delay)

            if terminated_this_pass == 0:
                break

        remaining_targets = self._collect_targeted_user_process_roots(
            include_browsers=include_browsers,
            include_media=include_media,
            include_remote_access=include_remote_access,
            include_screen_sharing=include_screen_sharing,
            include_duplicate_application=include_duplicate_application,
        )

        remaining = []

        remaining_keys = set()

        for (
            process,
            category,
        ) in remaining_targets:
            try:
                process_name = process.name()

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess,
            ):
                process_name = ""

            item = {
                "pid": int(process.pid),
                "process_name": process_name,
                "executable": self._safe_process_executable(process),
                "category": category,
            }

            key = (
                item["pid"],
                self._normalize(item["process_name"]),
                category,
            )

            if key in remaining_keys:
                continue

            remaining_keys.add(key)

            remaining.append(item)

        result["failed"] = remaining

        print(
            "[PROCESS MONITOR] Targeted pre-exam cleanup result "
            f"| detected={len(result['detected'])} "
            f"| terminated={len(result['terminated'])} "
            f"| remaining={len(result['failed'])}"
        )

        if result["failed"]:
            for item in result["failed"]:
                print(
                    "[PROCESS MONITOR] Unable to terminate restricted process "
                    f"| category={item.get('category')} "
                    f"| process={item.get('process_name')} "
                    f"| pid={item.get('pid')}"
                )

        return result

    def terminate_all_user_processes_before_exam(
        self,
        max_passes=3,
        settle_delay=0.25,
    ):
        """
        Backward-compatible legacy entry point.

        The historical name is intentionally retained, but the implementation
        now performs targeted lockdown rather than terminating every user app.
        """

        return self.terminate_targeted_processes_before_exam(
            max_passes=max_passes,
            settle_delay=settle_delay,
            include_browsers=True,
            include_media=True,
            include_remote_access=True,
            include_screen_sharing=True,
            include_duplicate_application=True,
        )

    def terminate_pre_exam_media_processes(
        self,
        include_browsers=True,
        include_camera_microphone=True,
        include_audio_playback=True,
    ):
        """
        Backward-compatible entry point used by main.py.

        Browsers, remote-access/screen-sharing apps, duplicate proctor instances,
        and user-space camera/microphone/audio applications are closed. Normal
        backend/development applications such as Node.js remain running.
        """

        include_media = bool(include_camera_microphone or include_audio_playback)

        return self.terminate_targeted_processes_before_exam(
            max_passes=4,
            settle_delay=0.20,
            include_browsers=bool(include_browsers),
            include_media=include_media,
            include_remote_access=True,
            include_screen_sharing=True,
            include_duplicate_application=True,
        )

    def enable_strict_user_process_lockdown(
        self,
        enabled=True,
    ):
        """
        Enable/disable continuous targeted lockdown after kiosk startup.

        The method name remains unchanged for backward compatibility. When
        enabled, scan_once() continuously removes only restricted categories:
        external browsers, remote access, screen sharing, media/camera/audio
        applications, and duplicate proctor instances.
        """

        self.strict_user_process_lockdown = bool(enabled)

        print(
            "[PROCESS MONITOR] Continuous targeted process lockdown "
            f"{'enabled' if self.strict_user_process_lockdown else 'disabled'}."
        )

        return self.strict_user_process_lockdown

    def capture_pre_kiosk_browser_processes(
        self,
    ):
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
            "[PROCESS MONITOR] "
            "Captured pre-kiosk browser roots: "
            f"{sorted(browser_roots)}"
        )

        return sorted(browser_roots)

    def terminate_pre_kiosk_browser_processes(
        self,
    ):
        if not self.supported_os:
            return []

        with self._lock:
            kiosk_root_pid = self.kiosk_root_pid

            browser_root_pids = list(self.pre_kiosk_browser_root_pids)

        if not kiosk_root_pid:
            print(
                "[PROCESS MONITOR] "
                "Pre-kiosk browser termination skipped "
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

            self._emit_frontend_restricted_result(
                category="browser",
                terminated=bool(success),
            )

            if success:
                terminated.append(pid)

        return terminated

    def scan_once(
        self,
    ):
        if not self.supported_os:
            return

        browser_roots_handled = set()

        with self._lock:
            kiosk_root_pid = self.kiosk_root_pid

        if self.strict_user_process_lockdown and kiosk_root_pid:
            strict_result = self.terminate_all_user_processes_before_exam(
                max_passes=1,
                settle_delay=0.0,
            )

            if strict_result.get("failed"):
                print(
                    "[PROCESS MONITOR] Continuous targeted lockdown "
                    "could not terminate "
                    f"{len(strict_result['failed'])} "
                    "restricted process(es)."
                )

            return

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

                if (
                    self.terminate_duplicate_app_instances
                    and self._is_same_proctor_application(process)
                ):
                    self._terminate_restricted_process(
                        process=process,
                        category="duplicate_proctor",
                    )

                    continue

                if self.terminate_remote_access and self._is_remote_access(
                    process_name,
                    executable,
                ):
                    self._terminate_restricted_process(
                        process=process,
                        category="remote_access",
                    )

                    continue

                if self.terminate_screen_sharing and self._is_screen_sharing(
                    process_name,
                    executable,
                ):
                    self._terminate_restricted_process(
                        process=process,
                        category="screen_sharing",
                    )

                    continue

                if self.terminate_media_processes and self._is_media_process(
                    process_name,
                    executable,
                ):
                    self._terminate_restricted_process(
                        process=process,
                        category="media",
                    )

                    continue

                if self.block_external_browsers and self._is_browser(process_name):
                    if not kiosk_root_pid:
                        if not self._warned_missing_kiosk_pid:
                            print(
                                "[PROCESS MONITOR] "
                                "External-browser termination "
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

                    self._terminate_restricted_process(
                        process=root,
                        category="browser",
                    )

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess,
            ):
                continue

            except Exception as error:
                print(
                    "[PROCESS MONITOR] Scan error:",
                    error,
                )

    def _run(
        self,
    ):
        print("[PROCESS MONITOR] Started.")

        while not self._stop_event.is_set():
            try:
                self.scan_once()

            except Exception as error:
                print(
                    "[PROCESS MONITOR] Scan failed:",
                    error,
                )

            self._stop_event.wait(self.check_interval)

        print("[PROCESS MONITOR] Stopped.")

    def start(
        self,
    ):
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

    def stop(
        self,
        timeout=3.0,
    ):
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

    def close(
        self,
    ):
        return self.stop()
