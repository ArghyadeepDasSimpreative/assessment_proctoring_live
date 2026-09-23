import math
from collections import deque

import numpy as np
import webrtcvad

try:
    from silero_vad_lite import SileroVAD
except Exception:
    SileroVAD = None


class VoiceActivityDetector:
    SUPPORTED_VAD_SAMPLE_RATES = (
        8000,
        16000,
        32000,
        48000,
    )

    SILERO_SAMPLE_RATE = 16000
    SILERO_CHUNK_SAMPLES = 512

    def __init__(
        self,
        frame_duration_ms=30,
        required_voice_duration=2.0,
        aggressiveness=1,
        calibration_seconds=1.0,
        smoothing_window_seconds=0.30,
        minimum_voice_ratio=0.40,
        silence_reset_seconds=0.75,
        whisper_noise_margin_db=5.0,
        whisper_absolute_floor_db=-62.0,
        use_silero=True,
        silero_speech_threshold=0.45,
        silero_support_threshold=0.05,
        silero_noise_veto_threshold=0.015,
        silero_noise_veto_frames=10,
        whisper_silero_threshold=0.04,
        whisper_history_seconds=0.42,
    ):
        if frame_duration_ms not in (
            10,
            20,
            30,
        ):
            raise ValueError("frame_duration_ms must be 10, 20, or 30.")

        aggressiveness = max(
            0,
            min(
                3,
                int(aggressiveness),
            ),
        )

        self.frame_duration_ms = int(frame_duration_ms)

        self.frame_duration_seconds = self.frame_duration_ms / 1000.0

        self.required_voice_duration = max(
            0.1,
            float(required_voice_duration),
        )

        self.calibration_seconds = max(
            0.0,
            float(calibration_seconds),
        )

        self.smoothing_window_seconds = max(
            self.frame_duration_seconds,
            float(smoothing_window_seconds),
        )

        self.minimum_voice_ratio = min(
            1.0,
            max(
                0.0,
                float(minimum_voice_ratio),
            ),
        )

        self.silence_reset_seconds = max(
            self.frame_duration_seconds,
            float(silence_reset_seconds),
        )

        self.whisper_noise_margin_db = float(whisper_noise_margin_db)

        self.whisper_absolute_floor_db = float(whisper_absolute_floor_db)

        self.use_silero = bool(use_silero)

        self.silero_speech_threshold = min(
            1.0,
            max(
                0.0,
                float(silero_speech_threshold),
            ),
        )

        self.silero_support_threshold = min(
            self.silero_speech_threshold,
            max(
                0.0,
                float(silero_support_threshold),
            ),
        )

        self.silero_noise_veto_threshold = min(
            self.silero_support_threshold,
            max(
                0.0,
                float(silero_noise_veto_threshold),
            ),
        )

        self.silero_noise_veto_frames = max(
            1,
            int(silero_noise_veto_frames),
        )

        self.whisper_silero_threshold = min(
            self.silero_speech_threshold,
            max(
                0.0,
                float(whisper_silero_threshold),
            ),
        )

        self.whisper_history_seconds = max(
            self.frame_duration_seconds,
            float(whisper_history_seconds),
        )

        self.vad = webrtcvad.Vad(aggressiveness)

        smoothing_frames = max(
            1,
            int(round(self.smoothing_window_seconds / self.frame_duration_seconds)),
        )

        calibration_frames = max(
            0,
            int(round(self.calibration_seconds / self.frame_duration_seconds)),
        )

        whisper_frames = max(
            3,
            int(round(self.whisper_history_seconds / self.frame_duration_seconds)),
        )

        feature_frames = max(
            whisper_frames,
            int(round(0.60 / self.frame_duration_seconds)),
        )

        webrtc_frames = max(
            4,
            int(round(0.45 / self.frame_duration_seconds)),
        )

        self.activity_history = deque(maxlen=smoothing_frames)

        self.whisper_history = deque(maxlen=whisper_frames)

        self.feature_history = deque(maxlen=feature_frames)

        self.webrtc_history = deque(maxlen=webrtc_frames)

        self.silero_probability_history = deque(maxlen=12)

        self.calibration_frames_required = calibration_frames

        self.calibration_levels = []

        self.calibrated = calibration_frames == 0

        self.noise_floor_dbfs = -60.0

        self.voice_duration = 0.0

        self.silence_duration = 0.0

        self.incident_active = False

        self.incident_confirmed = False

        self.incident_number = 0

        self.total_frames = 0

        self.silero_vad = None

        self.silero_available = False

        self.silero_error = None

        self.silero_probability = 0.0

        self.silero_updates = 0

        self.silero_low_streak = 0

        self.silero_input_buffer = np.empty(
            0,
            dtype=np.float32,
        )

        self._initialize_silero()

    def _initialize_silero(
        self,
    ):
        self.silero_vad = None

        self.silero_available = False

        self.silero_error = None

        self.silero_probability = 0.0

        self.silero_updates = 0

        self.silero_low_streak = 0

        self.silero_input_buffer = np.empty(
            0,
            dtype=np.float32,
        )

        self.silero_probability_history.clear()

        if not self.use_silero:
            return

        if SileroVAD is None:

            self.silero_error = "silero-vad-lite is not installed."

            return

        try:

            self.silero_vad = SileroVAD(self.SILERO_SAMPLE_RATE)

            self.silero_available = True

        except Exception as error:

            self.silero_vad = None

            self.silero_available = False

            self.silero_error = str(error)

    def _pcm16_samples(
        self,
        audio,
    ):
        if isinstance(
            audio,
            np.ndarray,
        ):

            samples = audio

            if samples.dtype != np.int16:

                samples = np.clip(
                    samples,
                    -32768,
                    32767,
                ).astype(np.int16)

            return samples.reshape(-1)

        if isinstance(
            audio,
            (
                bytes,
                bytearray,
                memoryview,
            ),
        ):

            return np.frombuffer(
                audio,
                dtype=np.int16,
            )

        raise TypeError("Audio frame must be PCM16 bytes or a numpy array.")

    def _resample(
        self,
        samples,
        source_sample_rate,
        target_sample_rate,
    ):
        source_sample_rate = int(source_sample_rate)

        target_sample_rate = int(target_sample_rate)

        if source_sample_rate <= 0 or target_sample_rate <= 0:

            raise ValueError("Audio sample rate must be greater than zero.")

        if source_sample_rate == target_sample_rate:

            return samples.astype(
                np.int16,
                copy=False,
            )

        if len(samples) == 0:

            return np.empty(
                0,
                dtype=np.int16,
            )

        target_length = max(
            1,
            int(round(len(samples) * target_sample_rate / source_sample_rate)),
        )

        old_positions = np.linspace(
            0.0,
            1.0,
            num=len(samples),
            endpoint=False,
        )

        new_positions = np.linspace(
            0.0,
            1.0,
            num=target_length,
            endpoint=False,
        )

        converted = np.interp(
            new_positions,
            old_positions,
            samples.astype(np.float32),
        )

        return np.clip(
            converted,
            -32768,
            32767,
        ).astype(np.int16)

    def _prepare_vad_frame(
        self,
        samples,
        source_sample_rate,
    ):
        target_sample_rate = 16000

        samples = self._resample(
            samples,
            source_sample_rate,
            target_sample_rate,
        )

        required_samples = int(target_sample_rate * self.frame_duration_ms / 1000)

        if len(samples) > required_samples:

            samples = samples[:required_samples]

        elif len(samples) < required_samples:

            samples = np.pad(
                samples,
                (
                    0,
                    required_samples - len(samples),
                ),
                mode="constant",
            )

        return (
            samples.astype(
                np.int16,
                copy=False,
            ),
            target_sample_rate,
        )

    def _calculate_rms(
        self,
        samples,
    ):
        if len(samples) == 0:

            return 0.0

        values = samples.astype(np.float32)

        return float(np.sqrt(np.mean(values * values)))

    def _calculate_dbfs(
        self,
        rms,
    ):
        if rms <= 0:

            return -100.0

        value = 20.0 * math.log10(rms / 32768.0)

        return max(
            -100.0,
            min(
                0.0,
                value,
            ),
        )

    def _zero_crossing_rate(
        self,
        samples,
    ):
        if len(samples) < 2:

            return 0.0

        signs = np.signbit(samples.astype(np.float32))

        crossings = np.count_nonzero(signs[1:] != signs[:-1])

        return float(crossings / (len(samples) - 1))

    def _spectral_features(
        self,
        samples,
        sample_rate,
    ):
        if len(samples) < 32:

            return {
                "speech_band_ratio": 0.0,
                "spectral_flatness": 0.0,
            }

        values = samples.astype(np.float32)

        values = values - np.mean(values)

        window = np.hanning(len(values)).astype(np.float32)

        spectrum = np.abs(np.fft.rfft(values * window))

        power = spectrum * spectrum

        frequencies = np.fft.rfftfreq(
            len(values),
            d=(1.0 / float(sample_rate)),
        )

        total_mask = (frequencies >= 70.0) & (frequencies <= 7600.0)

        speech_mask = (frequencies >= 150.0) & (frequencies <= 4400.0)

        total_energy = float(np.sum(power[total_mask]))

        speech_energy = float(np.sum(power[speech_mask]))

        if total_energy > 0:

            speech_band_ratio = speech_energy / total_energy

        else:

            speech_band_ratio = 0.0

        valid_spectrum = spectrum[total_mask]

        if len(valid_spectrum) == 0:

            spectral_flatness = 0.0

        else:

            valid_spectrum = valid_spectrum + 1e-12

            geometric_mean = float(np.exp(np.mean(np.log(valid_spectrum))))

            arithmetic_mean = float(np.mean(valid_spectrum))

            if arithmetic_mean > 0:

                spectral_flatness = geometric_mean / arithmetic_mean

            else:

                spectral_flatness = 0.0

        return {
            "speech_band_ratio": float(speech_band_ratio),
            "spectral_flatness": float(spectral_flatness),
        }

    def _calibrate(
        self,
        dbfs,
    ):
        if self.calibrated:

            return False

        self.calibration_levels.append(float(dbfs))

        if len(self.calibration_levels) < self.calibration_frames_required:

            return True

        useful_levels = [level for level in self.calibration_levels if level > -99.0]

        if useful_levels:

            self.noise_floor_dbfs = float(
                np.percentile(
                    useful_levels,
                    25,
                )
            )

        self.calibrated = True

        self.activity_history.clear()

        self.whisper_history.clear()

        self.feature_history.clear()

        self.webrtc_history.clear()

        return False

    def _update_noise_floor(
        self,
        dbfs,
    ):
        dbfs = float(dbfs)

        if dbfs <= -99.0:

            return

        alpha = 0.975

        self.noise_floor_dbfs = alpha * self.noise_floor_dbfs + (1.0 - alpha) * dbfs

    def _update_feature_history(
        self,
        dbfs,
        speech_band_ratio,
        spectral_flatness,
        zero_crossing_rate,
    ):
        self.feature_history.append(
            {
                "dbfs": float(dbfs),
                "speech_band_ratio": float(speech_band_ratio),
                "spectral_flatness": float(spectral_flatness),
                "zero_crossing_rate": float(zero_crossing_rate),
            }
        )

    def _temporal_features(
        self,
    ):
        if len(self.feature_history) < 3:

            return {
                "energy_variation_db": 0.0,
                "speech_band_variation": 0.0,
                "zcr_variation": 0.0,
                "dynamic": False,
            }

        dbfs_values = np.array(
            [item["dbfs"] for item in self.feature_history if item["dbfs"] > -99.0],
            dtype=np.float32,
        )

        band_values = np.array(
            [item["speech_band_ratio"] for item in self.feature_history],
            dtype=np.float32,
        )

        zcr_values = np.array(
            [item["zero_crossing_rate"] for item in self.feature_history],
            dtype=np.float32,
        )

        energy_variation = float(np.std(dbfs_values)) if len(dbfs_values) >= 3 else 0.0

        band_variation = float(np.std(band_values)) if len(band_values) >= 3 else 0.0

        zcr_variation = float(np.std(zcr_values)) if len(zcr_values) >= 3 else 0.0

        dynamic = bool(
            energy_variation >= 0.65
            or band_variation >= 0.020
            or zcr_variation >= 0.012
        )

        return {
            "energy_variation_db": energy_variation,
            "speech_band_variation": band_variation,
            "zcr_variation": zcr_variation,
            "dynamic": dynamic,
        }

    def _effective_whisper_minimum_level(
        self,
    ):
        effective_margin = max(
            2.5,
            self.whisper_noise_margin_db - 0.75,
        )

        effective_floor = min(
            self.whisper_absolute_floor_db,
            -61.0,
        )

        return max(
            effective_floor,
            self.noise_floor_dbfs + effective_margin,
        )

    def _detect_whisper_frame(
        self,
        dbfs,
        zero_crossing_rate,
        speech_band_ratio,
        spectral_flatness,
    ):
        minimum_level = self._effective_whisper_minimum_level()

        detected = bool(
            dbfs >= minimum_level
            and 0.010 <= zero_crossing_rate <= 0.46
            and 0.34 <= speech_band_ratio <= 0.995
            and 0.010 <= spectral_flatness <= 0.90
        )

        return (
            detected,
            minimum_level,
        )

    def _update_whisper_history(
        self,
        detected,
    ):
        self.whisper_history.append(bool(detected))

        if len(self.whisper_history) < 3:

            return (
                False,
                0.0,
            )

        ratio = sum(1 for value in self.whisper_history if value) / len(
            self.whisper_history
        )

        return (
            ratio >= 0.50,
            float(ratio),
        )

    def _update_webrtc_history(
        self,
        detected,
    ):
        self.webrtc_history.append(bool(detected))

        if not self.webrtc_history:

            return 0.0

        return float(
            sum(1 for value in self.webrtc_history if value) / len(self.webrtc_history)
        )

    def _run_silero(
        self,
        samples,
    ):
        if not self.silero_available or self.silero_vad is None:

            return (
                self.silero_probability,
                False,
            )

        normalized = samples.astype(np.float32) / 32768.0

        normalized = np.clip(
            normalized,
            -1.0,
            1.0,
        ).astype(
            np.float32,
            copy=False,
        )

        if len(self.silero_input_buffer) == 0:

            self.silero_input_buffer = normalized.copy()

        else:

            self.silero_input_buffer = np.concatenate(
                (
                    self.silero_input_buffer,
                    normalized,
                )
            )

        probabilities = []

        while len(self.silero_input_buffer) >= self.SILERO_CHUNK_SAMPLES:

            chunk = self.silero_input_buffer[: self.SILERO_CHUNK_SAMPLES]

            self.silero_input_buffer = self.silero_input_buffer[
                self.SILERO_CHUNK_SAMPLES :
            ]

            try:

                probability = float(
                    self.silero_vad.process(
                        chunk.astype(
                            np.float32,
                            copy=False,
                        ).tobytes()
                    )
                )

            except Exception as error:

                self.silero_error = str(error)

                self.silero_available = False

                self.silero_vad = None

                self.silero_input_buffer = np.empty(
                    0,
                    dtype=np.float32,
                )

                return (
                    self.silero_probability,
                    False,
                )

            probability = min(
                1.0,
                max(
                    0.0,
                    probability,
                ),
            )

            probabilities.append(probability)

            self.silero_probability_history.append(probability)

            self.silero_probability = probability

            self.silero_updates += 1

            if probability <= self.silero_noise_veto_threshold:

                self.silero_low_streak += 1

            else:

                self.silero_low_streak = 0

        if probabilities:

            self.silero_probability = float(np.mean(probabilities))

            return (
                self.silero_probability,
                True,
            )

        return (
            self.silero_probability,
            False,
        )

    def _silero_recent_stats(
        self,
    ):
        if not self.silero_probability_history:

            return {
                "max": 0.0,
                "mean": 0.0,
                "available_samples": 0,
            }

        values = np.array(
            self.silero_probability_history,
            dtype=np.float32,
        )

        return {
            "max": float(np.max(values)),
            "mean": float(np.mean(values)),
            "available_samples": int(len(values)),
        }

    def _normal_speech_decision(
        self,
        vad_speech,
        webrtc_ratio,
        dbfs,
        speech_band_ratio,
        spectral_flatness,
        temporal,
        silero_stats,
    ):
        minimum_level = max(
            -66.0,
            self.noise_floor_dbfs + 1.5,
        )

        webrtc_candidate = bool(
            vad_speech
            and dbfs >= minimum_level
            and speech_band_ratio >= 0.24
            and spectral_flatness <= 0.97
        )

        persistent_webrtc = bool(
            webrtc_ratio >= 0.52
            and dbfs >= minimum_level
            and speech_band_ratio >= 0.28
            and spectral_flatness <= 0.94
            and temporal["dynamic"]
        )

        if not self.silero_available:

            if webrtc_candidate:

                return (
                    True,
                    "webrtc_vad_fallback",
                )

            if persistent_webrtc:

                return (
                    True,
                    "webrtc_persistent_fallback",
                )

            return (
                False,
                None,
            )

        silero_max = float(silero_stats["max"])

        silero_mean = float(silero_stats["mean"])

        if (
            silero_max >= self.silero_speech_threshold
            or silero_mean >= self.silero_speech_threshold
        ):

            if dbfs >= max(
                -72.0,
                self.noise_floor_dbfs + 0.5,
            ):

                return (
                    True,
                    "silero_vad",
                )

        if not (webrtc_candidate or persistent_webrtc):

            return (
                False,
                None,
            )

        if self.silero_updates < self.silero_noise_veto_frames:

            return (
                True,
                "webrtc_vad",
            )

        if (
            silero_max >= self.silero_support_threshold
            or silero_mean >= self.silero_support_threshold
        ):

            return (
                True,
                "webrtc_silero",
            )

        if (
            persistent_webrtc
            and self.silero_low_streak < self.silero_noise_veto_frames + 4
        ):

            return (
                True,
                "webrtc_persistent",
            )

        if self.silero_low_streak >= self.silero_noise_veto_frames:

            return (
                False,
                None,
            )

        return (
            True,
            "webrtc_vad",
        )

    def _whisper_decision(
        self,
        whisper_persistent,
        whisper_ratio,
        vad_speech,
        webrtc_ratio,
        temporal,
        silero_stats,
        dbfs,
        minimum_whisper_dbfs,
        speech_band_ratio,
        spectral_flatness,
    ):
        if not whisper_persistent:

            return (
                False,
                None,
            )

        silero_max = float(silero_stats["max"])

        silero_mean = float(silero_stats["mean"])

        if self.silero_available and (
            silero_max >= self.whisper_silero_threshold
            or silero_mean >= self.whisper_silero_threshold
        ):

            return (
                True,
                "silero_whisper",
            )

        if vad_speech and dbfs >= minimum_whisper_dbfs and speech_band_ratio >= 0.34:

            return (
                True,
                "webrtc_whisper",
            )

        if (
            webrtc_ratio >= 0.38
            and temporal["dynamic"]
            and dbfs >= minimum_whisper_dbfs
        ):

            return (
                True,
                "webrtc_whisper_persistent",
            )

        if (
            temporal["dynamic"]
            and whisper_ratio >= 0.62
            and dbfs >= minimum_whisper_dbfs + 0.5
            and speech_band_ratio >= 0.42
            and 0.015 <= spectral_flatness <= 0.82
        ):

            return (
                True,
                "whisper_detector",
            )

        return (
            False,
            None,
        )

    def _smoothed_voice_state(
        self,
        detected,
    ):
        self.activity_history.append(bool(detected))

        if not self.activity_history:

            return False

        ratio = sum(1 for value in self.activity_history if value) / len(
            self.activity_history
        )

        effective_ratio = max(
            0.30,
            self.minimum_voice_ratio - 0.08,
        )

        return ratio >= effective_ratio

    def _reset_incident(
        self,
    ):
        self.voice_duration = 0.0

        self.silence_duration = 0.0

        self.incident_active = False

        self.incident_confirmed = False

    def reset(
        self,
        recalibrate=False,
    ):
        self.activity_history.clear()

        self.whisper_history.clear()

        self.feature_history.clear()

        self.webrtc_history.clear()

        self._reset_incident()

        self.total_frames = 0

        self._initialize_silero()

        if recalibrate:

            self.calibrated = self.calibration_frames_required == 0

            self.calibration_levels = []

            self.noise_floor_dbfs = -60.0

    def _build_result(
        self,
        calibrating,
        vad_speech,
        whisper_candidate,
        raw_voice_detected,
        voice_active,
        just_confirmed,
        rms,
        dbfs,
        zero_crossing_rate,
        speech_band_ratio,
        spectral_flatness,
        minimum_whisper_dbfs,
        detection_source,
        silero_probability,
        silero_stats,
        silero_updated,
        whisper_ratio,
        temporal,
        webrtc_ratio,
    ):
        silero_speech = bool(
            self.silero_available
            and float(
                silero_stats.get(
                    "max",
                    0.0,
                )
            )
            >= self.silero_speech_threshold
        )

        return {
            "calibrating": bool(calibrating),
            "vad_speech": bool(vad_speech),
            "whisper_candidate": bool(whisper_candidate),
            "raw_voice_detected": bool(raw_voice_detected),
            "voice_active": bool(voice_active),
            "voice_duration_seconds": round(
                self.voice_duration,
                3,
            ),
            "silence_duration_seconds": round(
                self.silence_duration,
                3,
            ),
            "required_voice_duration_seconds": self.required_voice_duration,
            "confirmed": bool(self.incident_confirmed),
            "just_confirmed": bool(just_confirmed),
            "incident_number": self.incident_number,
            "rms": round(
                float(rms),
                3,
            ),
            "dbfs": round(
                float(dbfs),
                3,
            ),
            "noise_floor_dbfs": round(
                float(self.noise_floor_dbfs),
                3,
            ),
            "zero_crossing_rate": round(
                float(zero_crossing_rate),
                5,
            ),
            "speech_band_ratio": round(
                float(speech_band_ratio),
                5,
            ),
            "spectral_flatness": round(
                float(spectral_flatness),
                5,
            ),
            "minimum_whisper_dbfs": round(
                float(minimum_whisper_dbfs),
                3,
            ),
            "detection_source": detection_source,
            "silero_available": bool(self.silero_available),
            "silero_speech": silero_speech,
            "silero_probability": round(
                float(silero_probability),
                5,
            ),
            "silero_recent_max": round(
                float(
                    silero_stats.get(
                        "max",
                        0.0,
                    )
                ),
                5,
            ),
            "silero_recent_mean": round(
                float(
                    silero_stats.get(
                        "mean",
                        0.0,
                    )
                ),
                5,
            ),
            "silero_updated": bool(silero_updated),
            "silero_error": self.silero_error,
            "whisper_ratio": round(
                float(whisper_ratio),
                5,
            ),
            "energy_variation_db": round(
                float(
                    temporal.get(
                        "energy_variation_db",
                        0.0,
                    )
                ),
                3,
            ),
            "webrtc_ratio": round(
                float(webrtc_ratio),
                5,
            ),
        }

    def process_frame(
        self,
        audio,
        sample_rate,
    ):
        source_samples = self._pcm16_samples(audio)

        (
            samples,
            vad_sample_rate,
        ) = self._prepare_vad_frame(
            source_samples,
            sample_rate,
        )

        self.total_frames += 1

        rms = self._calculate_rms(samples)

        dbfs = self._calculate_dbfs(rms)

        zero_crossing_rate = self._zero_crossing_rate(samples)

        spectral = self._spectral_features(
            samples,
            vad_sample_rate,
        )

        speech_band_ratio = float(spectral["speech_band_ratio"])

        spectral_flatness = float(spectral["spectral_flatness"])

        calibrating = self._calibrate(dbfs)

        if calibrating:

            return self._build_result(
                calibrating=True,
                vad_speech=False,
                whisper_candidate=False,
                raw_voice_detected=False,
                voice_active=False,
                just_confirmed=False,
                rms=rms,
                dbfs=dbfs,
                zero_crossing_rate=zero_crossing_rate,
                speech_band_ratio=speech_band_ratio,
                spectral_flatness=spectral_flatness,
                minimum_whisper_dbfs=self._effective_whisper_minimum_level(),
                detection_source=None,
                silero_probability=self.silero_probability,
                silero_stats={
                    "max": 0.0,
                    "mean": 0.0,
                },
                silero_updated=False,
                whisper_ratio=0.0,
                temporal={
                    "energy_variation_db": 0.0,
                },
                webrtc_ratio=0.0,
            )

        try:

            vad_speech = bool(
                self.vad.is_speech(
                    samples.tobytes(),
                    vad_sample_rate,
                )
            )

        except Exception:

            vad_speech = False

        webrtc_ratio = self._update_webrtc_history(vad_speech)

        self._update_feature_history(
            dbfs=dbfs,
            speech_band_ratio=speech_band_ratio,
            spectral_flatness=spectral_flatness,
            zero_crossing_rate=zero_crossing_rate,
        )

        temporal = self._temporal_features()

        (
            whisper_frame,
            minimum_whisper_dbfs,
        ) = self._detect_whisper_frame(
            dbfs=dbfs,
            zero_crossing_rate=zero_crossing_rate,
            speech_band_ratio=speech_band_ratio,
            spectral_flatness=spectral_flatness,
        )

        (
            whisper_persistent,
            whisper_ratio,
        ) = self._update_whisper_history(whisper_frame)

        (
            silero_probability,
            silero_updated,
        ) = self._run_silero(samples)

        silero_stats = self._silero_recent_stats()

        (
            normal_speech,
            normal_source,
        ) = self._normal_speech_decision(
            vad_speech=vad_speech,
            webrtc_ratio=webrtc_ratio,
            dbfs=dbfs,
            speech_band_ratio=speech_band_ratio,
            spectral_flatness=spectral_flatness,
            temporal=temporal,
            silero_stats=silero_stats,
        )

        (
            whisper_candidate,
            whisper_source,
        ) = self._whisper_decision(
            whisper_persistent=whisper_persistent,
            whisper_ratio=whisper_ratio,
            vad_speech=vad_speech,
            webrtc_ratio=webrtc_ratio,
            temporal=temporal,
            silero_stats=silero_stats,
            dbfs=dbfs,
            minimum_whisper_dbfs=minimum_whisper_dbfs,
            speech_band_ratio=speech_band_ratio,
            spectral_flatness=spectral_flatness,
        )

        raw_voice_detected = bool(normal_speech or whisper_candidate)

        if normal_speech:

            detection_source = normal_source

        elif whisper_candidate:

            detection_source = whisper_source

        else:

            detection_source = None

        if not raw_voice_detected:

            self._update_noise_floor(dbfs)

        voice_active = self._smoothed_voice_state(raw_voice_detected)

        just_confirmed = False

        if voice_active:

            if not self.incident_active:

                self.incident_active = True

                self.incident_number += 1

            self.voice_duration += self.frame_duration_seconds

            self.silence_duration = 0.0

            if (
                not self.incident_confirmed
                and self.voice_duration >= self.required_voice_duration
            ):

                self.incident_confirmed = True

                just_confirmed = True

        elif self.incident_active:

            self.silence_duration += self.frame_duration_seconds

            if self.silence_duration >= self.silence_reset_seconds:

                self._reset_incident()

        return self._build_result(
            calibrating=False,
            vad_speech=vad_speech,
            whisper_candidate=whisper_candidate,
            raw_voice_detected=raw_voice_detected,
            voice_active=voice_active,
            just_confirmed=just_confirmed,
            rms=rms,
            dbfs=dbfs,
            zero_crossing_rate=zero_crossing_rate,
            speech_band_ratio=speech_band_ratio,
            spectral_flatness=spectral_flatness,
            minimum_whisper_dbfs=minimum_whisper_dbfs,
            detection_source=detection_source,
            silero_probability=silero_probability,
            silero_stats=silero_stats,
            silero_updated=silero_updated,
            whisper_ratio=whisper_ratio,
            temporal=temporal,
            webrtc_ratio=webrtc_ratio,
        )
