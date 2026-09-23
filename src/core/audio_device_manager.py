import hashlib
import platform
import threading

import sounddevice as sd


class AudioDeviceManager:
    VIRTUAL_KEYWORDS = {
        "stereo mix",
        "what u hear",
        "what you hear",
        "virtual",
        "vb-audio",
        "vb cable",
        "vb-cable",
        "cable input",
        "cable output",
        "voicemeeter",
        "loopback",
        "monitor of",
        ".monitor",
        "blackhole",
        "soundflower",
        "background music",
        "null sink",
        "null output",
    }

    SAMPLE_RATES = (
        16000,
        48000,
        32000,
        44100,
    )

    def __init__(
        self,
        probe_duration=0.25,
        reject_virtual_devices=True,
    ):
        self.system = platform.system()

        self.probe_duration = max(
            0.1,
            float(probe_duration),
        )

        self.reject_virtual_devices = bool(reject_virtual_devices)

        self._lock = threading.RLock()

        self._devices = {}

        self._last_snapshot = {}

        self._last_default_key = None

        self.active_device_key = None

        self.active_device = None

        self.refresh_devices()

        self._last_snapshot = self._snapshot()

        self._last_default_key = self._get_default_key()

    def _hostapi_name(
        self,
        hostapi_index,
    ):
        try:
            hostapis = sd.query_hostapis()

            if hostapi_index is None:
                return ""

            index = int(hostapi_index)

            if index < 0 or index >= len(hostapis):
                return ""

            return str(hostapis[index].get("name") or "").strip()

        except Exception:
            return ""

    def _default_input_index(
        self,
    ):
        try:
            default_device = sd.default.device

            if isinstance(
                default_device,
                (
                    list,
                    tuple,
                ),
            ):
                index = default_device[0]
            else:
                index = default_device

            index = int(index)

            if index < 0:
                return None

            return index

        except Exception:
            return None

    def _is_virtual(
        self,
        name,
    ):
        text = str(name or "").strip().lower()

        return any(keyword in text for keyword in self.VIRTUAL_KEYWORDS)

    def _device_key(
        self,
        name,
        hostapi_name,
        channels,
        samplerate,
    ):
        raw = "|".join(
            [
                str(hostapi_name or "").strip().lower(),
                str(name or "").strip().lower(),
                str(int(channels or 0)),
                str(int(round(float(samplerate or 0)))),
            ]
        )

        digest = hashlib.sha1(
            raw.encode(
                "utf-8",
                errors="ignore",
            )
        ).hexdigest()[:16]

        return f"mic_{digest}"

    def _hostapi_priority(
        self,
        hostapi_name,
    ):
        name = str(hostapi_name or "").lower()

        if self.system == "Windows":

            if "wasapi" in name:
                return 0

            if "wdm-ks" in name:
                return 1

            if "directsound" in name:
                return 2

            if "mme" in name:
                return 3

        if self.system == "Darwin" and "core audio" in name:
            return 0

        if self.system == "Linux":

            if "pipewire" in name:
                return 0

            if "pulse" in name:
                return 1

            if "alsa" in name:
                return 2

        return 10

    def refresh_devices(
        self,
    ):
        with self._lock:

            try:
                queried = sd.query_devices()

            except Exception:
                queried = []

            default_index = self._default_input_index()

            devices = {}

            for index, device in enumerate(queried):

                try:
                    channels = int(
                        device.get(
                            "max_input_channels",
                            0,
                        )
                        or 0
                    )

                    if channels <= 0:
                        continue

                    name = str(device.get("name") or "").strip()

                    hostapi = int(
                        device.get(
                            "hostapi",
                            -1,
                        )
                    )

                    hostapi_name = self._hostapi_name(hostapi)

                    samplerate = float(
                        device.get(
                            "default_samplerate",
                            0.0,
                        )
                        or 0.0
                    )

                    key = self._device_key(
                        name,
                        hostapi_name,
                        channels,
                        samplerate,
                    )

                    record = {
                        "device_key": key,
                        "index": int(index),
                        "name": name,
                        "hostapi": hostapi,
                        "hostapi_name": hostapi_name,
                        "max_input_channels": channels,
                        "default_samplerate": samplerate,
                        "is_default": (
                            default_index is not None
                            and int(index) == int(default_index)
                        ),
                        "is_virtual": self._is_virtual(name),
                        "available": True,
                        "active": (key == self.active_device_key),
                    }

                    existing = devices.get(key)

                    if existing is None:

                        devices[key] = record

                    elif record["is_default"]:

                        devices[key] = record

                    elif self._hostapi_priority(
                        record["hostapi_name"]
                    ) < self._hostapi_priority(existing["hostapi_name"]):

                        devices[key] = record

                except Exception:
                    continue

            self._devices = devices

            if self.active_device_key:

                current = self._devices.get(self.active_device_key)

                if current:

                    current["active"] = True

                    if self.active_device:

                        current["sample_rate"] = self.active_device.get(
                            "sample_rate",
                            current.get("default_samplerate"),
                        )

                    self.active_device = dict(current)

                else:

                    self.active_device = None

            return self.list_microphones(
                include_virtual=True,
                refresh=False,
            )

    def list_microphones(
        self,
        include_virtual=False,
        refresh=True,
    ):
        with self._lock:

            if refresh:

                self.refresh_devices()

            devices = []

            for device in self._devices.values():

                if not include_virtual and device["is_virtual"]:
                    continue

                item = dict(device)

                item["active"] = item["device_key"] == self.active_device_key

                devices.append(item)

            devices.sort(
                key=lambda item: (
                    not item["is_default"],
                    self._hostapi_priority(item["hostapi_name"]),
                    item["name"].lower(),
                )
            )

            return devices

    def _get_default_key(
        self,
    ):
        for key, device in self._devices.items():

            if device.get("is_default"):
                return key

        return None

    def get_default_microphone(
        self,
    ):
        with self._lock:

            self.refresh_devices()

            key = self._get_default_key()

            if not key:
                return None

            device = self._devices.get(key)

            if not device:
                return None

            if self.reject_virtual_devices and device.get("is_virtual"):
                return None

            return dict(device)

    def _find_supported_sample_rate(
        self,
        device,
    ):
        rates = []

        default_rate = int(
            round(
                float(
                    device.get(
                        "default_samplerate",
                        0.0,
                    )
                    or 0.0
                )
            )
        )

        if default_rate > 0:

            rates.append(default_rate)

        for rate in self.SAMPLE_RATES:

            if rate not in rates:

                rates.append(rate)

        for rate in rates:

            try:
                sd.check_input_settings(
                    device=int(device["index"]),
                    channels=1,
                    dtype="int16",
                    samplerate=rate,
                )

                return rate

            except Exception:
                continue

        return None

    def validate_device(
        self,
        device,
        probe=True,
    ):
        if not isinstance(
            device,
            dict,
        ):

            return {
                "success": False,
                "reason": "INVALID_DEVICE",
            }

        if self.reject_virtual_devices and device.get("is_virtual"):

            return {
                "success": False,
                "reason": "VIRTUAL_DEVICE_REJECTED",
                "device": dict(device),
            }

        sample_rate = self._find_supported_sample_rate(device)

        if not sample_rate:

            return {
                "success": False,
                "reason": "UNSUPPORTED_INPUT_FORMAT",
                "device": dict(device),
            }

        validated = dict(device)

        validated["sample_rate"] = int(sample_rate)

        if not probe:

            return {
                "success": True,
                "device": validated,
            }

        frames = max(
            160,
            int(sample_rate * self.probe_duration),
        )

        try:

            with sd.RawInputStream(
                device=int(device["index"]),
                samplerate=int(sample_rate),
                channels=1,
                dtype="int16",
                blocksize=frames,
            ) as stream:

                stream.read(frames)

        except Exception as error:

            return {
                "success": False,
                "reason": "MICROPHONE_OPEN_FAILED",
                "error": str(error),
                "device": dict(device),
            }

        return {
            "success": True,
            "device": validated,
        }

    def _activate(
        self,
        device,
    ):
        self.active_device_key = device["device_key"]

        self.active_device = dict(device)

        self.active_device["active"] = True

        for record in self._devices.values():

            record["active"] = record["device_key"] == self.active_device_key

        return dict(self.active_device)

    def select_default_microphone(
        self,
    ):
        with self._lock:

            self.refresh_devices()

            candidates = self.list_microphones(
                include_virtual=not self.reject_virtual_devices,
                refresh=False,
            )

            for device in candidates:

                result = self.validate_device(
                    device,
                    probe=True,
                )

                if result.get("success"):

                    selected = self._activate(result["device"])

                    return {
                        "success": True,
                        "device": selected,
                    }

            self.active_device_key = None

            self.active_device = None

            return {
                "success": False,
                "reason": "NO_VALID_MICROPHONE",
            }

    def switch_microphone(
        self,
        device_key,
    ):
        with self._lock:

            self.refresh_devices()

            requested = self._devices.get(str(device_key))

            if not requested:

                return {
                    "success": False,
                    "reason": "MICROPHONE_NOT_FOUND",
                }

            previous = dict(self.active_device) if self.active_device else None

            result = self.validate_device(
                requested,
                probe=True,
            )

            if not result.get("success"):

                result["previous_device"] = previous

                return result

            selected = self._activate(result["device"])

            return {
                "success": True,
                "device": selected,
                "previous_device": previous,
                "changed": (
                    previous is None
                    or previous.get("device_key") != selected.get("device_key")
                ),
            }

    def get_active_microphone(
        self,
    ):
        with self._lock:

            if not self.active_device:
                return None

            return dict(self.active_device)

    def active_microphone_available(
        self,
    ):
        with self._lock:

            if not self.active_device_key:
                return False

            self.refresh_devices()

            return self.active_device_key in self._devices

    def _snapshot(
        self,
    ):
        return {
            key: {
                "device_key": device["device_key"],
                "name": device["name"],
                "hostapi_name": device["hostapi_name"],
                "max_input_channels": device["max_input_channels"],
                "default_samplerate": device["default_samplerate"],
                "is_default": device["is_default"],
                "is_virtual": device["is_virtual"],
            }
            for key, device in (self._devices.items())
        }

    def poll_device_changes(
        self,
    ):
        with self._lock:

            previous_snapshot = self._last_snapshot

            previous_default_key = self._last_default_key

            self.refresh_devices()

            current_snapshot = self._snapshot()

            current_default_key = self._get_default_key()

            previous_keys = set(previous_snapshot)

            current_keys = set(current_snapshot)

            added_keys = current_keys - previous_keys

            removed_keys = previous_keys - current_keys

            added_devices = [current_snapshot[key] for key in added_keys]

            removed_devices = [previous_snapshot[key] for key in removed_keys]

            active_missing = (
                bool(self.active_device_key)
                and self.active_device_key not in current_keys
            )

            default_changed = current_default_key != previous_default_key

            self._last_snapshot = current_snapshot

            self._last_default_key = current_default_key

            return {
                "changed": bool(
                    added_devices
                    or removed_devices
                    or default_changed
                    or active_missing
                ),
                "added_devices": added_devices,
                "removed_devices": removed_devices,
                "default_changed": default_changed,
                "previous_default_device_key": previous_default_key,
                "current_default_device_key": current_default_key,
                "active_device_key": self.active_device_key,
                "active_missing": active_missing,
                "active_device": self.get_active_microphone(),
            }

    def get_public_microphones(
        self,
    ):
        microphones = self.list_microphones(include_virtual=False)

        return [
            {
                "device_key": device["device_key"],
                "name": device["name"],
                "active": device["active"],
                "available": device["available"],
            }
            for device in microphones
        ]

    def clear_active_microphone(
        self,
    ):
        with self._lock:

            self.active_device_key = None

            self.active_device = None

            for record in self._devices.values():

                record["active"] = False
