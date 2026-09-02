import ctypes
import sys
import threading
from ctypes import wintypes


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class KeyboardLockdownManager:
    WH_KEYBOARD_LL = 13

    HC_ACTION = 0

    WM_KEYDOWN = 0x0100
    WM_KEYUP = 0x0101
    WM_SYSKEYDOWN = 0x0104
    WM_SYSKEYUP = 0x0105
    WM_QUIT = 0x0012

    VK_TAB = 0x09
    VK_RETURN = 0x0D

    VK_SHIFT = 0x10
    VK_CONTROL = 0x11
    VK_MENU = 0x12

    VK_ESCAPE = 0x1B
    VK_SPACE = 0x20

    VK_PRIOR = 0x21
    VK_NEXT = 0x22
    VK_HOME = 0x24

    VK_LEFT = 0x25
    VK_UP = 0x26
    VK_RIGHT = 0x27
    VK_DOWN = 0x28

    VK_SNAPSHOT = 0x2C
    VK_DELETE = 0x2E

    VK_0 = 0x30
    VK_1 = 0x31
    VK_9 = 0x39

    VK_A = 0x41
    VK_C = 0x43
    VK_D = 0x44
    VK_E = 0x45
    VK_F = 0x46
    VK_G = 0x47
    VK_H = 0x48
    VK_I = 0x49
    VK_J = 0x4A
    VK_K = 0x4B
    VK_L = 0x4C
    VK_M = 0x4D
    VK_N = 0x4E
    VK_O = 0x4F
    VK_P = 0x50
    VK_Q = 0x51
    VK_R = 0x52
    VK_S = 0x53
    VK_T = 0x54
    VK_U = 0x55
    VK_V = 0x56
    VK_W = 0x57
    VK_X = 0x58

    VK_LWIN = 0x5B
    VK_RWIN = 0x5C
    VK_APPS = 0x5D

    VK_F1 = 0x70
    VK_F2 = 0x71
    VK_F3 = 0x72
    VK_F4 = 0x73
    VK_F5 = 0x74
    VK_F6 = 0x75
    VK_F10 = 0x79
    VK_F11 = 0x7A
    VK_F12 = 0x7B

    VK_LSHIFT = 0xA0
    VK_RSHIFT = 0xA1

    VK_LCONTROL = 0xA2
    VK_RCONTROL = 0xA3

    VK_LMENU = 0xA4
    VK_RMENU = 0xA5

    VK_BROWSER_BACK = 0xA6
    VK_BROWSER_FORWARD = 0xA7
    VK_BROWSER_REFRESH = 0xA8
    VK_BROWSER_STOP = 0xA9
    VK_BROWSER_SEARCH = 0xAA
    VK_BROWSER_FAVORITES = 0xAB
    VK_BROWSER_HOME = 0xAC

    def __init__(
        self,
        allow_development_escape=True,
    ):
        if sys.platform != "win32":
            raise RuntimeError("Keyboard lockdown is supported only on Windows.")

        self.allow_development_escape = bool(allow_development_escape)

        self.user32 = ctypes.WinDLL(
            "user32",
            use_last_error=True,
        )

        self.kernel32 = ctypes.WinDLL(
            "kernel32",
            use_last_error=True,
        )

        self.running = False

        self.hook = None
        self.thread = None
        self.thread_id = None

        self.emergency_unlock_requested = False

        self.started_event = threading.Event()

        self.startup_error = None

        self.HOOKPROC = ctypes.WINFUNCTYPE(
            ctypes.c_ssize_t,
            ctypes.c_int,
            wintypes.WPARAM,
            wintypes.LPARAM,
        )

        self.callback = self.HOOKPROC(self._keyboard_callback)

        self._configure_windows_api()

    def _configure_windows_api(self):
        self.kernel32.GetModuleHandleW.argtypes = [
            wintypes.LPCWSTR,
        ]

        self.kernel32.GetModuleHandleW.restype = wintypes.HMODULE

        self.kernel32.GetCurrentThreadId.argtypes = []

        self.kernel32.GetCurrentThreadId.restype = wintypes.DWORD

        self.user32.SetWindowsHookExW.argtypes = [
            ctypes.c_int,
            self.HOOKPROC,
            wintypes.HINSTANCE,
            wintypes.DWORD,
        ]

        self.user32.SetWindowsHookExW.restype = wintypes.HHOOK

        self.user32.CallNextHookEx.argtypes = [
            wintypes.HHOOK,
            ctypes.c_int,
            wintypes.WPARAM,
            wintypes.LPARAM,
        ]

        self.user32.CallNextHookEx.restype = ctypes.c_ssize_t

        self.user32.UnhookWindowsHookEx.argtypes = [
            wintypes.HHOOK,
        ]

        self.user32.UnhookWindowsHookEx.restype = wintypes.BOOL

        self.user32.GetAsyncKeyState.argtypes = [
            ctypes.c_int,
        ]

        self.user32.GetAsyncKeyState.restype = wintypes.SHORT

        self.user32.GetMessageW.argtypes = [
            ctypes.POINTER(wintypes.MSG),
            wintypes.HWND,
            wintypes.UINT,
            wintypes.UINT,
        ]

        self.user32.GetMessageW.restype = wintypes.BOOL

        self.user32.TranslateMessage.argtypes = [
            ctypes.POINTER(wintypes.MSG),
        ]

        self.user32.TranslateMessage.restype = wintypes.BOOL

        self.user32.DispatchMessageW.argtypes = [
            ctypes.POINTER(wintypes.MSG),
        ]

        self.user32.DispatchMessageW.restype = ctypes.c_ssize_t

        self.user32.PostThreadMessageW.argtypes = [
            wintypes.DWORD,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        ]

        self.user32.PostThreadMessageW.restype = wintypes.BOOL

    def _pressed(
        self,
        key,
    ):
        return bool(self.user32.GetAsyncKeyState(key) & 0x8000)

    def _ctrl_pressed(self):
        return (
            self._pressed(self.VK_CONTROL)
            or self._pressed(self.VK_LCONTROL)
            or self._pressed(self.VK_RCONTROL)
        )

    def _shift_pressed(self):
        return (
            self._pressed(self.VK_SHIFT)
            or self._pressed(self.VK_LSHIFT)
            or self._pressed(self.VK_RSHIFT)
        )

    def _alt_pressed(self):
        return (
            self._pressed(self.VK_MENU)
            or self._pressed(self.VK_LMENU)
            or self._pressed(self.VK_RMENU)
        )

    def _win_pressed(self):
        return self._pressed(self.VK_LWIN) or self._pressed(self.VK_RWIN)

    def _is_development_escape(
        self,
        vk_code,
        ctrl,
        shift,
        alt,
    ):
        if not self.allow_development_escape:
            return False

        return ctrl and shift and alt and vk_code == self.VK_F10

    def _is_blocked(
        self,
        vk_code,
        ctrl,
        shift,
        alt,
        win,
    ):
        if vk_code in {
            self.VK_LWIN,
            self.VK_RWIN,
        }:
            return True

        if win:
            return True

        if vk_code in {
            self.VK_SNAPSHOT,
            self.VK_APPS,
        }:
            return True

        if vk_code in {
            self.VK_BROWSER_BACK,
            self.VK_BROWSER_FORWARD,
            self.VK_BROWSER_REFRESH,
            self.VK_BROWSER_STOP,
            self.VK_BROWSER_SEARCH,
            self.VK_BROWSER_FAVORITES,
            self.VK_BROWSER_HOME,
        }:
            return True

        if vk_code in {
            self.VK_F6,
            self.VK_F11,
            self.VK_F12,
        }:
            return True

        if alt:
            if vk_code in {
                self.VK_TAB,
                self.VK_ESCAPE,
                self.VK_F4,
                self.VK_SPACE,
                self.VK_LEFT,
                self.VK_RIGHT,
                self.VK_HOME,
            }:
                return True

        if ctrl:
            if vk_code == self.VK_ESCAPE:
                return True

            if shift and vk_code == self.VK_ESCAPE:
                return True

            if vk_code in {
                self.VK_TAB,
                self.VK_PRIOR,
                self.VK_NEXT,
            }:
                return True

            if self.VK_1 <= vk_code <= self.VK_9:
                return True

            if vk_code in {
                self.VK_L,
                self.VK_T,
                self.VK_N,
                self.VK_W,
                self.VK_R,
            }:
                return True

            if shift:
                if vk_code in {
                    self.VK_N,
                    self.VK_W,
                    self.VK_I,
                    self.VK_J,
                    self.VK_DELETE,
                }:
                    return True

        return False

    def _request_emergency_unlock(
        self,
    ):
        self.emergency_unlock_requested = True

        self.running = False

        if self.thread_id:
            self.user32.PostThreadMessageW(
                self.thread_id,
                self.WM_QUIT,
                0,
                0,
            )

    def _keyboard_callback(
        self,
        n_code,
        w_param,
        l_param,
    ):
        if n_code < self.HC_ACTION:
            return self.user32.CallNextHookEx(
                self.hook,
                n_code,
                w_param,
                l_param,
            )

        message = int(w_param)

        if message not in {
            self.WM_KEYDOWN,
            self.WM_SYSKEYDOWN,
        }:
            return self.user32.CallNextHookEx(
                self.hook,
                n_code,
                w_param,
                l_param,
            )

        keyboard = ctypes.cast(
            l_param,
            ctypes.POINTER(KBDLLHOOKSTRUCT),
        ).contents

        vk_code = int(keyboard.vkCode)

        ctrl = self._ctrl_pressed()
        shift = self._shift_pressed()
        alt = self._alt_pressed()
        win = self._win_pressed()

        if self._is_development_escape(
            vk_code,
            ctrl,
            shift,
            alt,
        ):
            print()
            print("[LOCKDOWN] Development emergency unlock requested.")

            self._request_emergency_unlock()

            return 1

        if self._is_blocked(
            vk_code,
            ctrl,
            shift,
            alt,
            win,
        ):
            return 1

        return self.user32.CallNextHookEx(
            self.hook,
            n_code,
            w_param,
            l_param,
        )

    def _message_loop(
        self,
    ):
        try:
            self.thread_id = self.kernel32.GetCurrentThreadId()

            module_handle = self.kernel32.GetModuleHandleW(None)

            ctypes.set_last_error(0)

            self.hook = self.user32.SetWindowsHookExW(
                self.WH_KEYBOARD_LL,
                self.callback,
                module_handle,
                0,
            )

            if not self.hook:
                error_code = ctypes.get_last_error()

                self.startup_error = (
                    "SetWindowsHookExW failed " f"with Windows error " f"{error_code}."
                )

                self.running = False

                self.started_event.set()

                return

            self.running = True

            self.started_event.set()

            message = wintypes.MSG()

            while self.running:
                result = self.user32.GetMessageW(
                    ctypes.byref(message),
                    None,
                    0,
                    0,
                )

                if result == 0:
                    break

                if result == -1:
                    error_code = ctypes.get_last_error()

                    print(
                        "[LOCKDOWN] "
                        "GetMessageW failed "
                        f"with Windows error "
                        f"{error_code}."
                    )

                    break

                self.user32.TranslateMessage(ctypes.byref(message))

                self.user32.DispatchMessageW(ctypes.byref(message))

        except Exception as error:
            self.startup_error = str(error)

            self.running = False

            self.started_event.set()

        finally:
            if self.hook:
                try:
                    self.user32.UnhookWindowsHookEx(self.hook)
                except Exception:
                    pass

            self.hook = None

            self.running = False

    def start(
        self,
    ):
        if self.running:
            return

        self.startup_error = None

        self.emergency_unlock_requested = False

        self.started_event.clear()

        self.thread = threading.Thread(
            target=self._message_loop,
            name="skolariq-keyboard-lockdown",
            daemon=True,
        )

        self.thread.start()

        started = self.started_event.wait(timeout=5)

        if not started:
            raise RuntimeError("Keyboard lockdown hook startup timed out.")

        if not self.running:
            if self.startup_error:
                raise RuntimeError(self.startup_error)

            raise RuntimeError("Unable to install Windows keyboard lockdown hook.")

        print("[LOCKDOWN] Keyboard lockdown active.")

        if self.allow_development_escape:
            print("[LOCKDOWN] Emergency development exit: " "Ctrl+Alt+Shift+F10")

    def stop(
        self,
    ):
        was_running = self.running or self.hook is not None

        self.running = False

        if self.thread_id:
            try:
                self.user32.PostThreadMessageW(
                    self.thread_id,
                    self.WM_QUIT,
                    0,
                    0,
                )
            except Exception:
                pass

        if (
            self.thread
            and self.thread.is_alive()
            and threading.current_thread() is not self.thread
        ):
            self.thread.join(timeout=3)

        self.thread = None
        self.thread_id = None

        if was_running:
            print("[LOCKDOWN] Keyboard lockdown released.")
