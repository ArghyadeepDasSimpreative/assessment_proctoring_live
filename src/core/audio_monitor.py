import threading
import time
from collections import deque
from datetime import datetime, timezone

from src.core.audio_device_manager import AudioDeviceManager
from src.core.voice_activity_detector import VoiceActivityDetector

try:
    import sounddevice as sd
except Exception:
    sd = None


class AudioMonitor:
    def __init__(
        self,
        device_manager=None,
        voice_detector=None,
        event_callback=None,
        device_poll_interval=2.0,
        evidence_buffer_seconds=8.0,
        reconnect_interval=2.0,
    ):
        self.device_manager = (
            device_manager if device_manager is not None else AudioDeviceManager()
        )

        self.voice_detector = (
            voice_detector
            if voice_detector is not None
            else VoiceActivityDetector(
                required_voice_duration=2.0,
            )
        )

        self.event_callback = event_callback

        self.device_poll_interval = max(
            0.5,
            float(device_poll_interval),
        )

        self.evidence_buffer_seconds = max(
            3.0,
            float(evidence_buffer_seconds),
        )

        self.reconnect_interval = max(
            0.5,
            float(reconnect_interval),
        )

        self.running = False

        self.monitor_thread = None

        self.stop_event = threading.Event()

        self.stream = None

        self._stream_lock = threading.RLock()
        self._status_lock = threading.RLock()
        self._switch_lock = threading.RLock()

        self._requested_device_key = None
        self._switch_result = None
        self._switch_completed_event = threading.Event()

        self._last_device_poll_at = 0.0
        self._last_reconnect_attempt_at = 0.0

        self._active_device_missing = False

        self._audio_buffer = deque()

        self._buffer_max_frames = self._calculate_buffer_frames()

        self._last_voice_active = False
        self._last_confirmed = False

        self._status = {
            "running": False,
            "microphone_available": False,
            "active_microphone": None,
            "calibrating": False,
            "voice_active": False,
            "voice_confirmed": False,
            "voice_duration_seconds": 0.0,
            "silence_duration_seconds": 0.0,
            "vad_speech": False,
            "whisper_candidate": False,
            "detection_source": None,
            "dbfs": -100.0,
            "noise_floor_dbfs": -60.0,
            "incident_number": 0,
            "last_error": None,
        }

    def _calculate_buffer_frames(
        self,
    ):
        frame_seconds = self.voice_detector.frame_duration_ms / 1000.0

        return max(
            1,
            int(self.evidence_buffer_seconds / frame_seconds),
        )

    def _utc_now(
        self,
    ):
        return datetime.now(timezone.utc).isoformat()

    def _emit(
        self,
        event_type,
        data=None,
    ):
        payload = {
            "event_type": str(event_type),
            "timestamp": self._utc_now(),
        }

        if isinstance(
            data,
            dict,
        ):
            payload.update(data)

        if callable(self.event_callback):
            try:
                self.event_callback(payload)
            except Exception:
                pass

        return payload

    def _public_device(
        self,
        device,
    ):
        if not isinstance(
            device,
            dict,
        ):
            return None

        return {
            "device_key": device.get("device_key"),
            "name": device.get("name"),
            "active": bool(device.get("active")),
            "available": bool(
                device.get(
                    "available",
                    True,
                )
            ),
        }

    def _set_status(
        self,
        **values,
    ):
        with self._status_lock:
            self._status.update(values)

    def get_status(
        self,
    ):
        with self._status_lock:
            status = dict(self._status)

            microphone = status.get("active_microphone")

            if isinstance(
                microphone,
                dict,
            ):
                status["active_microphone"] = dict(microphone)

            return status

    def get_available_microphones(
        self,
    ):
        try:
            return self.device_manager.get_public_microphones()

        except Exception:
            return []

    def _append_audio_buffer(
        self,
        pcm_bytes,
        sample_rate,
    ):
        self._audio_buffer.append(
            {
                "pcm": bytes(pcm_bytes),
                "sample_rate": int(sample_rate),
                "timestamp": self._utc_now(),
            }
        )

        while len(self._audio_buffer) > self._buffer_max_frames:
            self._audio_buffer.popleft()

    def clear_audio_buffer(
        self,
    ):
        self._audio_buffer.clear()

    def get_recent_audio(
        self,
        seconds=None,
    ):
        if seconds is None:
            seconds = self.evidence_buffer_seconds

        seconds = max(
            0.1,
            float(seconds),
        )

        frame_seconds = self.voice_detector.frame_duration_ms / 1000.0

        required_frames = max(
            1,
            int(seconds / frame_seconds),
        )

        frames = list(self._audio_buffer)[-required_frames:]

        if not frames:
            return {
                "pcm": b"",
                "sample_rate": None,
                "channels": 1,
                "sample_width": 2,
                "duration_seconds": 0.0,
            }

        sample_rate = frames[-1].get("sample_rate")

        matching_frames = [
            frame for frame in frames if (frame.get("sample_rate") == sample_rate)
        ]

        pcm = b"".join(frame["pcm"] for frame in matching_frames)

        sample_count = len(pcm) // 2

        duration = sample_count / float(sample_rate) if sample_rate else 0.0

        return {
            "pcm": pcm,
            "sample_rate": sample_rate,
            "channels": 1,
            "sample_width": 2,
            "duration_seconds": round(
                duration,
                3,
            ),
        }

    def _select_initial_microphone(
        self,
    ):
        result = self.device_manager.select_default_microphone()

        if not result.get("success"):
            self._set_status(
                microphone_available=False,
                active_microphone=None,
                last_error=result.get("reason"),
            )

            self._emit(
                "MIC_UNAVAILABLE",
                {
                    "reason": result.get(
                        "reason",
                        "NO_VALID_MICROPHONE",
                    ),
                    "devices": self.get_available_microphones(),
                },
            )

            return None

        device = result["device"]

        public_device = self._public_device(device)

        self._set_status(
            microphone_available=True,
            active_microphone=public_device,
            last_error=None,
        )

        self._emit(
            "MIC_SELECTED",
            {
                "device": public_device,
            },
        )

        return device

    def _open_stream(
        self,
        device,
    ):
        if sd is None:
            raise RuntimeError("sounddevice is not available.")

        sample_rate = int(
            device.get("sample_rate") or device.get("default_samplerate") or 16000
        )

        blocksize = max(
            1,
            int(round(sample_rate * self.voice_detector.frame_duration_ms / 1000.0)),
        )

        with self._stream_lock:

            self._close_stream()

            self.stream = sd.RawInputStream(
                device=int(device["index"]),
                samplerate=sample_rate,
                channels=1,
                dtype="int16",
                blocksize=blocksize,
            )

            self.stream.start()

        self.clear_audio_buffer()

        self.voice_detector.reset(recalibrate=True)

        self._active_device_missing = False

        self._set_status(
            microphone_available=True,
            active_microphone=self._public_device(device),
            last_error=None,
        )

        self._emit(
            "MIC_STREAM_STARTED",
            {
                "device": self._public_device(device),
                "sample_rate": sample_rate,
                "blocksize": blocksize,
            },
        )

        return {
            "sample_rate": sample_rate,
            "blocksize": blocksize,
        }

    def _close_stream(
        self,
    ):
        stream = self.stream

        self.stream = None

        if stream is None:
            return

        try:
            stream.stop()
        except Exception:
            pass

        try:
            stream.close()
        except Exception:
            pass

    def _handle_voice_result(
        self,
        result,
    ):
        active_device = self.device_manager.get_active_microphone()

        public_device = self._public_device(active_device)

        self._set_status(
            microphone_available=True,
            active_microphone=public_device,
            calibrating=bool(result.get("calibrating")),
            voice_active=bool(result.get("voice_active")),
            voice_confirmed=bool(result.get("confirmed")),
            voice_duration_seconds=float(
                result.get(
                    "voice_duration_seconds",
                    0.0,
                )
            ),
            silence_duration_seconds=float(
                result.get(
                    "silence_duration_seconds",
                    0.0,
                )
            ),
            vad_speech=bool(result.get("vad_speech")),
            whisper_candidate=bool(result.get("whisper_candidate")),
            detection_source=result.get("detection_source"),
            dbfs=float(
                result.get(
                    "dbfs",
                    -100.0,
                )
            ),
            noise_floor_dbfs=float(
                result.get(
                    "noise_floor_dbfs",
                    -60.0,
                )
            ),
            incident_number=int(
                result.get(
                    "incident_number",
                    0,
                )
            ),
            last_error=None,
        )

        voice_active = bool(result.get("voice_active"))

        confirmed = bool(result.get("confirmed"))

        just_confirmed = bool(result.get("just_confirmed"))

        if voice_active and not self._last_voice_active:
            self._emit(
                "VOICE_ACTIVITY_STARTED",
                {
                    "device": public_device,
                    "detection_source": result.get("detection_source"),
                    "dbfs": result.get("dbfs"),
                },
            )

        if just_confirmed:

            evidence = self.get_recent_audio(seconds=self.evidence_buffer_seconds)

            self._emit(
                "VOICE_DETECTED",
                {
                    "violation_type": "VOICE_DETECTED",
                    "device": public_device,
                    "voice_duration_seconds": result.get("voice_duration_seconds"),
                    "required_voice_duration_seconds": result.get(
                        "required_voice_duration_seconds",
                        2.0,
                    ),
                    "detection_source": result.get("detection_source"),
                    "vad_speech": bool(result.get("vad_speech")),
                    "whisper_candidate": bool(result.get("whisper_candidate")),
                    "dbfs": result.get("dbfs"),
                    "noise_floor_dbfs": result.get("noise_floor_dbfs"),
                    "incident_number": result.get("incident_number"),
                    "evidence_audio": evidence,
                },
            )

        if not voice_active and self._last_voice_active:
            self._emit(
                "VOICE_ACTIVITY_ENDED",
                {
                    "device": public_device,
                    "incident_number": result.get("incident_number"),
                },
            )

        self._last_voice_active = voice_active

        self._last_confirmed = confirmed

    def _poll_devices(
        self,
    ):
        now = time.monotonic()

        if now - self._last_device_poll_at < self.device_poll_interval:
            return

        self._last_device_poll_at = now

        try:

            change = self.device_manager.poll_device_changes()

        except Exception as error:

            self._emit(
                "MIC_DEVICE_POLL_ERROR",
                {"error": str(error)},
            )

            return

        if not change.get("changed"):
            return

        if change.get("default_changed"):

            self._emit(
                "DEFAULT_MIC_CHANGED",
                {
                    "previous_default_device_key": change.get(
                        "previous_default_device_key"
                    ),
                    "current_default_device_key": change.get(
                        "current_default_device_key"
                    ),
                },
            )

        added_devices = change.get("added_devices") or []

        removed_devices = change.get("removed_devices") or []

        if added_devices or removed_devices:

            self._emit(
                "MIC_DEVICE_LIST_CHANGED",
                {
                    "added_devices": added_devices,
                    "removed_devices": removed_devices,
                    "devices": self.get_available_microphones(),
                },
            )

        if change.get("active_missing"):

            self._active_device_missing = True

            previous_device = self.get_status().get("active_microphone")

            self._set_status(
                microphone_available=False,
                last_error="ACTIVE_MICROPHONE_DISCONNECTED",
            )

            self._emit(
                "MIC_CHANGE_REQUIRED",
                {
                    "reason": "MIC_DISCONNECTED",
                    "current_device": previous_device,
                    "devices": self.get_available_microphones(),
                },
            )

            self._close_stream()

    def _attempt_active_device_recovery(
        self,
    ):
        if not self._active_device_missing:
            return False

        now = time.monotonic()

        if now - self._last_reconnect_attempt_at < self.reconnect_interval:
            return False

        self._last_reconnect_attempt_at = now

        active_key = self.device_manager.active_device_key

        if not active_key:
            return False

        self.device_manager.refresh_devices()

        available = self.device_manager._devices.get(active_key)

        if not available:
            return False

        validation = self.device_manager.validate_device(
            available,
            probe=True,
        )

        if not validation.get("success"):
            return False

        device = validation["device"]

        self.device_manager._activate(device)

        try:

            self._open_stream(device)

        except Exception:
            return False

        self._active_device_missing = False

        self._emit(
            "MIC_RECOVERED",
            {"device": self._public_device(device)},
        )

        return True

    def _process_switch_request(
        self,
    ):
        with self._switch_lock:

            device_key = self._requested_device_key

            if not device_key:
                return

            self._requested_device_key = None

        previous_device = self.device_manager.get_active_microphone()

        previous_public = self._public_device(previous_device)

        self._close_stream()

        try:

            result = self.device_manager.switch_microphone(device_key)

            if not result.get("success"):

                self._switch_result = {
                    "success": False,
                    "reason": result.get(
                        "reason",
                        "MICROPHONE_CHANGE_FAILED",
                    ),
                    "error": result.get("error"),
                    "previous_device": previous_public,
                }

                if previous_device:

                    try:
                        self._open_stream(previous_device)
                    except Exception:
                        pass

                self._emit(
                    "MIC_CHANGE_FAILED",
                    dict(self._switch_result),
                )

                return

            new_device = result["device"]

            self._open_stream(new_device)

            new_public = self._public_device(new_device)

            self._switch_result = {
                "success": True,
                "device": new_public,
                "previous_device": previous_public,
                "changed": bool(result.get("changed")),
            }

            self._emit(
                "MIC_DEVICE_CHANGED",
                dict(self._switch_result),
            )

        except Exception as error:

            self._switch_result = {
                "success": False,
                "reason": "MICROPHONE_CHANGE_FAILED",
                "error": str(error),
                "previous_device": previous_public,
            }

            self._emit(
                "MIC_CHANGE_FAILED",
                dict(self._switch_result),
            )

        finally:

            self._switch_completed_event.set()

    def switch_microphone(
        self,
        device_key,
        timeout=8.0,
    ):
        if not device_key:

            return {
                "success": False,
                "reason": "MICROPHONE_DEVICE_KEY_REQUIRED",
            }

        if not self.running:

            return {
                "success": False,
                "reason": "AUDIO_MONITOR_NOT_RUNNING",
            }

        with self._switch_lock:

            self._switch_result = None

            self._switch_completed_event.clear()

            self._requested_device_key = str(device_key)

        completed = self._switch_completed_event.wait(
            timeout=max(
                1.0,
                float(timeout),
            )
        )

        if not completed:

            return {
                "success": False,
                "reason": "MICROPHONE_CHANGE_TIMEOUT",
            }

        return (
            dict(self._switch_result)
            if isinstance(
                self._switch_result,
                dict,
            )
            else {
                "success": False,
                "reason": "MICROPHONE_CHANGE_FAILED",
            }
        )

    def _monitor_loop(
        self,
    ):
        try:

            device = self.device_manager.get_active_microphone()

            if not device:

                device = self._select_initial_microphone()

            if not device:

                while not self.stop_event.is_set():

                    self._poll_devices()

                    with self._switch_lock:
                        has_switch_request = bool(self._requested_device_key)

                    if has_switch_request:

                        self._process_switch_request()

                    time.sleep(0.1)

                return

            stream_info = self._open_stream(device)

            sample_rate = stream_info["sample_rate"]

            blocksize = stream_info["blocksize"]

            while not self.stop_event.is_set():

                self._poll_devices()

                with self._switch_lock:
                    has_switch_request = bool(self._requested_device_key)

                if has_switch_request:

                    self._process_switch_request()

                    active = self.device_manager.get_active_microphone()

                    if active:

                        sample_rate = int(
                            active.get("sample_rate")
                            or active.get("default_samplerate")
                            or 16000
                        )

                        blocksize = max(
                            1,
                            int(
                                round(
                                    sample_rate
                                    * self.voice_detector.frame_duration_ms
                                    / 1000.0
                                )
                            ),
                        )

                    continue

                if self._active_device_missing:

                    self._attempt_active_device_recovery()

                    time.sleep(0.05)

                    continue

                stream = self.stream

                if stream is None:

                    self._active_device_missing = True

                    time.sleep(0.05)

                    continue

                try:

                    audio_data, overflowed = stream.read(blocksize)

                    pcm_bytes = bytes(audio_data)

                except Exception as error:

                    self._set_status(
                        microphone_available=False,
                        last_error=str(error),
                    )

                    self._emit(
                        "MIC_STREAM_ERROR",
                        {
                            "error": str(error),
                            "current_device": self.get_status().get(
                                "active_microphone"
                            ),
                            "devices": self.get_available_microphones(),
                        },
                    )

                    self._active_device_missing = True

                    self._close_stream()

                    continue

                if overflowed:

                    self._emit(
                        "MIC_INPUT_OVERFLOW",
                        {"device": self.get_status().get("active_microphone")},
                    )

                self._append_audio_buffer(
                    pcm_bytes,
                    sample_rate,
                )

                try:

                    result = self.voice_detector.process_frame(
                        pcm_bytes,
                        sample_rate,
                    )

                except Exception as error:

                    self._set_status(last_error=str(error))

                    self._emit(
                        "VOICE_DETECTION_ERROR",
                        {"error": str(error)},
                    )

                    continue

                self._handle_voice_result(result)

        except Exception as error:

            self._set_status(
                microphone_available=False,
                last_error=str(error),
            )

            self._emit(
                "AUDIO_MONITOR_ERROR",
                {"error": str(error)},
            )

        finally:

            self._close_stream()

            self._set_status(running=False)

            self.running = False

            self._emit("AUDIO_MONITOR_STOPPED")

    def start(
        self,
    ):
        if self.running:
            return True

        if sd is None:

            self._set_status(
                running=False,
                microphone_available=False,
                last_error="sounddevice is not available.",
            )

            return False

        self.stop_event.clear()

        self.running = True

        self._set_status(
            running=True,
            last_error=None,
        )

        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="ProctorAudioMonitor",
        )

        self.monitor_thread.start()

        self._emit("AUDIO_MONITOR_STARTED")

        return True

    def stop(
        self,
    ):
        if not self.running:

            self._close_stream()

            return

        self.stop_event.set()

        self._close_stream()

        thread = self.monitor_thread

        if thread and thread.is_alive() and thread is not threading.current_thread():

            thread.join(timeout=3.0)

        self.monitor_thread = None

        self.running = False

        self._set_status(running=False)

    def close(
        self,
    ):
        self.stop()
