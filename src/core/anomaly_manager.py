# import time

# from src.config.settings import settings


# class AnomalyManager:

#     DEFAULT_RULE = {
#         "duration": 0.0,
#         "cooldown": 12.0,
#         "recovery_grace": 0.0,
#         "capture_once_per_incident": False,
#     }

#     AUDIO_EVENT_TYPES = {
#         "VOICE_DETECTED",
#     }

#     def __init__(
#         self,
#         evidence_store,
#         socket_client=None,
#     ):
#         if evidence_store is None:
#             raise ValueError("AnomalyManager requires an evidence_store.")

#         self.evidence_store = evidence_store
#         self.socket_client = socket_client

#         self.rules = {
#             "NO_FACE": {
#                 "duration": 2.0,
#                 "cooldown": settings.EVIDENCE_COOLDOWN_NO_FACE,
#                 "recovery_grace": 0.5,
#                 "capture_once_per_incident": True,
#             },
#             "MULTIPLE_FACES": {
#                 "duration": 0.0,
#                 "cooldown": settings.EVIDENCE_COOLDOWN_MULTIPLE_FACES,
#                 "recovery_grace": 0.5,
#                 "capture_once_per_incident": False,
#             },
#             "GAZE_AWAY": {
#                 "duration": 3.0,
#                 "cooldown": settings.EVIDENCE_COOLDOWN_GAZE_AWAY,
#                 "recovery_grace": 0.8,
#                 "capture_once_per_incident": False,
#             },
#             "HEAD_AWAY": {
#                 "duration": 1.0,
#                 "cooldown": settings.EVIDENCE_COOLDOWN_HEAD_AWAY,
#                 "recovery_grace": 0.8,
#                 "capture_once_per_incident": False,
#             },
#             "PHONE_DETECTED": {
#                 "duration": 0.3,
#                 "cooldown": settings.EVIDENCE_COOLDOWN_PHONE_DETECTED,
#                 "recovery_grace": 1.0,
#                 "capture_once_per_incident": False,
#             },
#             "BOOK_DETECTED": {
#                 "duration": 1.0,
#                 "cooldown": settings.EVIDENCE_COOLDOWN_BOOK_DETECTED,
#                 "recovery_grace": 1.0,
#                 "capture_once_per_incident": False,
#             },
#             "EXTRA_PERSON": {
#                 "duration": 1.0,
#                 "cooldown": settings.EVIDENCE_COOLDOWN_EXTRA_PERSON,
#                 "recovery_grace": 1.0,
#                 "capture_once_per_incident": False,
#             },
#             "BODY_LEAN_LEFT": {
#                 "duration": 2.0,
#                 "cooldown": settings.EVIDENCE_COOLDOWN_BODY_LEAN_LEFT,
#                 "recovery_grace": 0.8,
#                 "capture_once_per_incident": False,
#             },
#             "BODY_LEAN_RIGHT": {
#                 "duration": 2.0,
#                 "cooldown": settings.EVIDENCE_COOLDOWN_BODY_LEAN_RIGHT,
#                 "recovery_grace": 0.8,
#                 "capture_once_per_incident": False,
#             },
#             "LEFT_ARM_RAISED": {
#                 "duration": 2.0,
#                 "cooldown": settings.EVIDENCE_COOLDOWN_LEFT_ARM_RAISED,
#                 "recovery_grace": 0.8,
#                 "capture_once_per_incident": False,
#             },
#             "RIGHT_ARM_RAISED": {
#                 "duration": 2.0,
#                 "cooldown": settings.EVIDENCE_COOLDOWN_RIGHT_ARM_RAISED,
#                 "recovery_grace": 0.8,
#                 "capture_once_per_incident": False,
#             },
#             "UNUSUAL_ARM_MOVEMENT": {
#                 "duration": 1.5,
#                 "cooldown": settings.EVIDENCE_COOLDOWN_UNUSUAL_ARM_MOVEMENT,
#                 "recovery_grace": 1.0,
#                 "capture_once_per_incident": False,
#             },
#             "UPPER_BODY_NOT_VISIBLE": {
#                 "duration": 2.0,
#                 "cooldown": settings.EVIDENCE_COOLDOWN_UPPER_BODY_NOT_VISIBLE,
#                 "recovery_grace": 0.8,
#                 "capture_once_per_incident": False,
#             },
#             "CAMERA_OFF": {
#                 "duration": 0.0,
#                 "cooldown": settings.EVIDENCE_COOLDOWN_CAMERA_OFF,
#                 "recovery_grace": 0.0,
#                 "capture_once_per_incident": False,
#             },
#             "MIC_OFF": {
#                 "duration": 0.0,
#                 "cooldown": settings.EVIDENCE_COOLDOWN_MIC_OFF,
#                 "recovery_grace": 0.0,
#                 "capture_once_per_incident": False,
#             },
#             "CAMERA_ERROR": {
#                 "duration": 0.0,
#                 "cooldown": settings.EVIDENCE_COOLDOWN_CAMERA_ERROR,
#                 "recovery_grace": 0.0,
#                 "capture_once_per_incident": False,
#             },
#             "MIC_ERROR": {
#                 "duration": 0.0,
#                 "cooldown": settings.EVIDENCE_COOLDOWN_MIC_ERROR,
#                 "recovery_grace": 0.0,
#                 "capture_once_per_incident": False,
#             },
#             "VOICE_DETECTED": {
#                 "duration": 0.0,
#                 "cooldown": getattr(
#                     settings,
#                     "EVIDENCE_COOLDOWN_VOICE_DETECTED",
#                     12.0,
#                 ),
#                 "recovery_grace": 0.75,
#                 "capture_once_per_incident": True,
#                 "minimum_audio_duration": 0.25,
#             },
#         }

#         self.states = {}

#         print("[ANOMALY] Manager initialized.")

#         print(f"[ANOMALY] " f"{len(self.rules)} anomaly rules loaded.")

#     def set_socket_client(
#         self,
#         socket_client,
#     ):
#         self.socket_client = socket_client

#         if socket_client is None:

#             print("[ANOMALY] Socket client detached.")

#         else:

#             print("[ANOMALY] Socket client attached.")

#     def _notify_socket(
#         self,
#         anomaly_result,
#     ):
#         if self.socket_client is None:
#             return False

#         if not isinstance(
#             anomaly_result,
#             dict,
#         ):
#             return False

#         if not anomaly_result.get("captured"):
#             return False

#         api_violation = anomaly_result.get("api_violation")

#         if not isinstance(
#             api_violation,
#             dict,
#         ):
#             return False

#         try:

#             notify_anomaly_result = getattr(
#                 self.socket_client,
#                 "notify_anomaly_result",
#                 None,
#             )

#             if callable(notify_anomaly_result):

#                 sent = notify_anomaly_result(anomaly_result)

#                 if sent:

#                     print(
#                         "[ANOMALY] Socket notification sent "
#                         f"for "
#                         f"{anomaly_result.get('event_type')}."
#                     )

#                 else:

#                     print(
#                         "[ANOMALY] Socket notification was not sent "
#                         f"for "
#                         f"{anomaly_result.get('event_type')}."
#                     )

#                 return bool(sent)

#             notify_proctor_violation = getattr(
#                 self.socket_client,
#                 "notify_proctor_violation",
#                 None,
#             )

#             if callable(notify_proctor_violation):

#                 sent = notify_proctor_violation(api_violation)

#                 if sent:

#                     print(
#                         "[ANOMALY] Socket violation notification sent "
#                         f"for "
#                         f"{anomaly_result.get('event_type')}."
#                     )

#                 else:

#                     print(
#                         "[ANOMALY] Socket violation notification "
#                         f"was not sent for "
#                         f"{anomaly_result.get('event_type')}."
#                     )

#                 return bool(sent)

#             print(
#                 "[ANOMALY] Socket client does not provide "
#                 "notify_anomaly_result() or "
#                 "notify_proctor_violation()."
#             )

#             return False

#         except Exception as error:

#             print(
#                 "[ANOMALY] Failed to send socket notification "
#                 f"for "
#                 f"{anomaly_result.get('event_type')}: "
#                 f"{error}"
#             )

#             return False

#     def notify_recorded_result(
#         self,
#         anomaly_result,
#     ):
#         return self._notify_socket(anomaly_result)

#     def _get_rule(
#         self,
#         event_type,
#     ):
#         return self.rules.get(
#             event_type,
#             self.DEFAULT_RULE,
#         )

#     def _get_state(
#         self,
#         event_type,
#     ):
#         if event_type not in self.states:

#             self.states[event_type] = {
#                 "started_at": None,
#                 "last_active_at": None,
#                 "last_capture_at": None,
#                 "confirmed": False,
#                 "captured_in_incident": False,
#             }

#         state = self.states[event_type]

#         if "captured_in_incident" not in state:

#             state["captured_in_incident"] = False

#         return state

#     def _reset_state(
#         self,
#         event_type,
#         state,
#     ):
#         if state.get("confirmed"):

#             print(f"[ANOMALY] RECOVERED " f"{event_type}")

#         state["started_at"] = None

#         state["last_active_at"] = None

#         state["confirmed"] = False

#         state["captured_in_incident"] = False

#     def get_cooldown(
#         self,
#         event_type,
#     ):
#         event_type = str(event_type).upper().strip()

#         rule = self._get_rule(event_type)

#         try:

#             cooldown = float(
#                 rule.get(
#                     "cooldown",
#                     12.0,
#                 )
#             )

#         except (
#             TypeError,
#             ValueError,
#         ):

#             cooldown = 12.0

#         return max(
#             0.0,
#             cooldown,
#         )

#     def get_required_duration(
#         self,
#         event_type,
#     ):
#         event_type = str(event_type).upper().strip()

#         rule = self._get_rule(event_type)

#         try:

#             duration = float(
#                 rule.get(
#                     "duration",
#                     0.0,
#                 )
#             )

#         except (
#             TypeError,
#             ValueError,
#         ):

#             duration = 0.0

#         return max(
#             0.0,
#             duration,
#         )

#     def get_minimum_audio_duration(
#         self,
#         event_type,
#     ):
#         event_type = str(event_type).upper().strip()

#         rule = self._get_rule(event_type)

#         try:

#             duration = float(
#                 rule.get(
#                     "minimum_audio_duration",
#                     0.0,
#                 )
#             )

#         except (
#             TypeError,
#             ValueError,
#         ):

#             duration = 0.0

#         return max(
#             0.0,
#             duration,
#         )

#     def _get_recovery_grace(
#         self,
#         event_type,
#     ):
#         rule = self._get_rule(event_type)

#         try:

#             recovery_grace = float(
#                 rule.get(
#                     "recovery_grace",
#                     0.0,
#                 )
#             )

#         except (
#             TypeError,
#             ValueError,
#         ):

#             recovery_grace = 0.0

#         return max(
#             0.0,
#             recovery_grace,
#         )

#     def _capture_once_per_incident(
#         self,
#         event_type,
#     ):
#         rule = self._get_rule(event_type)

#         return bool(
#             rule.get(
#                 "capture_once_per_incident",
#                 False,
#             )
#         )

#     def _get_cooldown_remaining(
#         self,
#         state,
#         now,
#         cooldown,
#     ):
#         last_capture_at = state.get("last_capture_at")

#         if last_capture_at is None:
#             return 0.0

#         elapsed = now - last_capture_at

#         return max(
#             0.0,
#             cooldown - elapsed,
#         )

#     def _build_api_violation(
#         self,
#         event_type,
#         evidence,
#         event_metadata,
#     ):
#         if not evidence:
#             return None

#         file_path = evidence.get("file_path")

#         if not file_path:

#             file_path = evidence.get("image_path")

#         if not file_path:

#             file_path = evidence.get("audio_path")

#         metadata_path = evidence.get("metadata_path")

#         event_payload = evidence.get("event")

#         client_captured_at = None

#         if isinstance(
#             event_payload,
#             dict,
#         ):

#             client_captured_at = event_payload.get("captured_at")

#         if not client_captured_at:

#             client_captured_at = evidence.get("client_captured_at")

#         violation_metadata = dict(event_metadata or {})

#         if metadata_path:

#             violation_metadata["evidence_metadata_path"] = metadata_path

#         evidence_type = evidence.get("evidence_type")

#         if evidence_type:

#             violation_metadata["evidence_type"] = evidence_type

#         return {
#             "violation_type": event_type,
#             "client_captured_at": client_captured_at,
#             "metadata": violation_metadata,
#             "file_path": file_path,
#         }

#     def _empty_result(
#         self,
#         event_type,
#         active,
#         confirmed,
#         duration,
#         required_duration,
#         cooldown,
#         cooldown_remaining,
#     ):
#         return {
#             "event_type": event_type,
#             "active": bool(active),
#             "confirmed": bool(confirmed),
#             "captured": False,
#             "duration": duration,
#             "required_duration": required_duration,
#             "cooldown": cooldown,
#             "cooldown_remaining": cooldown_remaining,
#             "evidence": None,
#             "api_violation": None,
#         }

#     def _capture_image_evidence(
#         self,
#         event_type,
#         frame,
#         event_metadata,
#     ):
#         return self.evidence_store.capture(
#             frame=frame,
#             event_type=event_type,
#             metadata=event_metadata,
#         )

#     def _capture_audio_evidence(
#         self,
#         event_type,
#         audio_evidence,
#         event_metadata,
#     ):
#         capture_audio = getattr(
#             self.evidence_store,
#             "capture_audio",
#             None,
#         )

#         if not callable(capture_audio):

#             raise RuntimeError("EvidenceStore does not provide capture_audio().")

#         if not isinstance(
#             audio_evidence,
#             dict,
#         ):

#             raise ValueError("Audio evidence must be a dictionary.")

#         pcm = audio_evidence.get("pcm")

#         sample_rate = audio_evidence.get("sample_rate")

#         channels = audio_evidence.get(
#             "channels",
#             1,
#         )

#         sample_width = audio_evidence.get(
#             "sample_width",
#             2,
#         )

#         if not pcm:

#             raise ValueError("Audio evidence contains no PCM data.")

#         if not sample_rate:

#             raise ValueError("Audio evidence sample rate is missing.")

#         return capture_audio(
#             pcm=pcm,
#             sample_rate=int(sample_rate),
#             channels=int(channels),
#             sample_width=int(sample_width),
#             event_type=event_type,
#             metadata=event_metadata,
#         )

#     def update(
#         self,
#         event_type,
#         active,
#         frame,
#         metadata=None,
#     ):
#         event_type = str(event_type).upper().strip()

#         if not event_type:

#             return {
#                 "event_type": "",
#                 "active": False,
#                 "confirmed": False,
#                 "captured": False,
#                 "duration": 0.0,
#                 "required_duration": 0.0,
#                 "cooldown": 0.0,
#                 "cooldown_remaining": 0.0,
#                 "evidence": None,
#                 "api_violation": None,
#             }

#         active = bool(active)

#         required_duration = self.get_required_duration(event_type)

#         cooldown = self.get_cooldown(event_type)

#         recovery_grace = self._get_recovery_grace(event_type)

#         capture_once = self._capture_once_per_incident(event_type)

#         state = self._get_state(event_type)

#         now = time.monotonic()

#         if active:

#             state["last_active_at"] = now

#             if state["started_at"] is None:

#                 state["started_at"] = now

#         else:

#             if state["started_at"] is None:

#                 return self._empty_result(
#                     event_type=event_type,
#                     active=False,
#                     confirmed=False,
#                     duration=0.0,
#                     required_duration=required_duration,
#                     cooldown=cooldown,
#                     cooldown_remaining=self._get_cooldown_remaining(
#                         state,
#                         now,
#                         cooldown,
#                     ),
#                 )

#             last_active_at = state.get("last_active_at")

#             if last_active_at is not None and (now - last_active_at) < recovery_grace:

#                 active = True

#             else:

#                 self._reset_state(
#                     event_type,
#                     state,
#                 )

#                 return self._empty_result(
#                     event_type=event_type,
#                     active=False,
#                     confirmed=False,
#                     duration=0.0,
#                     required_duration=required_duration,
#                     cooldown=cooldown,
#                     cooldown_remaining=self._get_cooldown_remaining(
#                         state,
#                         now,
#                         cooldown,
#                     ),
#                 )

#         started_at = state.get("started_at")

#         if started_at is None:

#             duration = 0.0

#         else:

#             duration = max(
#                 0.0,
#                 now - started_at,
#             )

#         if duration < required_duration:

#             return self._empty_result(
#                 event_type=event_type,
#                 active=True,
#                 confirmed=False,
#                 duration=duration,
#                 required_duration=required_duration,
#                 cooldown=cooldown,
#                 cooldown_remaining=self._get_cooldown_remaining(
#                     state,
#                     now,
#                     cooldown,
#                 ),
#             )

#         if not state["confirmed"]:

#             state["confirmed"] = True

#             print(
#                 f"[ANOMALY] DETECTED "
#                 f"{event_type} "
#                 f"| duration="
#                 f"{duration:.2f}s"
#             )

#         if capture_once and state.get(
#             "captured_in_incident",
#             False,
#         ):

#             return self._empty_result(
#                 event_type=event_type,
#                 active=True,
#                 confirmed=True,
#                 duration=duration,
#                 required_duration=required_duration,
#                 cooldown=cooldown,
#                 cooldown_remaining=self._get_cooldown_remaining(
#                     state,
#                     now,
#                     cooldown,
#                 ),
#             )

#         cooldown_remaining = self._get_cooldown_remaining(
#             state,
#             now,
#             cooldown,
#         )

#         if cooldown_remaining > 0.0:

#             return self._empty_result(
#                 event_type=event_type,
#                 active=True,
#                 confirmed=True,
#                 duration=duration,
#                 required_duration=required_duration,
#                 cooldown=cooldown,
#                 cooldown_remaining=cooldown_remaining,
#             )

#         event_metadata = dict(metadata or {})

#         event_metadata["event_duration_seconds"] = round(
#             duration,
#             2,
#         )

#         event_metadata["required_duration_seconds"] = round(
#             required_duration,
#             2,
#         )

#         event_metadata["evidence_cooldown_seconds"] = round(
#             cooldown,
#             2,
#         )

#         event_metadata["recovery_grace_seconds"] = round(
#             recovery_grace,
#             2,
#         )

#         event_metadata["evidence_type"] = "image"

#         try:

#             evidence = self._capture_image_evidence(
#                 event_type=event_type,
#                 frame=frame,
#                 event_metadata=event_metadata,
#             )

#         except Exception as error:

#             print(
#                 f"[ANOMALY] Evidence capture "
#                 f"failed for "
#                 f"{event_type}: "
#                 f"{error}"
#             )

#             result = self._empty_result(
#                 event_type=event_type,
#                 active=True,
#                 confirmed=True,
#                 duration=duration,
#                 required_duration=required_duration,
#                 cooldown=cooldown,
#                 cooldown_remaining=cooldown,
#             )

#             result["error"] = str(error)

#             return result

#         if evidence is not None:

#             state["last_capture_at"] = now

#             if capture_once:

#                 state["captured_in_incident"] = True

#             api_violation = self._build_api_violation(
#                 event_type=event_type,
#                 evidence=evidence,
#                 event_metadata=event_metadata,
#             )

#             print(f"[ANOMALY] EVIDENCE CAPTURED " f"{event_type}")

#             result = {
#                 "event_type": event_type,
#                 "active": True,
#                 "confirmed": True,
#                 "captured": True,
#                 "duration": duration,
#                 "required_duration": required_duration,
#                 "cooldown": cooldown,
#                 "cooldown_remaining": 0.0,
#                 "evidence": evidence,
#                 "api_violation": api_violation,
#             }

#             if self.socket_client is not None:

#                 self._notify_socket(result)

#             return result

#         return self._empty_result(
#             event_type=event_type,
#             active=True,
#             confirmed=True,
#             duration=duration,
#             required_duration=required_duration,
#             cooldown=cooldown,
#             cooldown_remaining=cooldown,
#         )

#     def update_audio(
#         self,
#         event_type,
#         active,
#         audio_evidence=None,
#         metadata=None,
#     ):
#         event_type = str(event_type).upper().strip()

#         if not event_type:

#             return {
#                 "event_type": "",
#                 "active": False,
#                 "confirmed": False,
#                 "captured": False,
#                 "duration": 0.0,
#                 "required_duration": 0.0,
#                 "cooldown": 0.0,
#                 "cooldown_remaining": 0.0,
#                 "evidence": None,
#                 "api_violation": None,
#             }

#         active = bool(active)

#         state = self._get_state(event_type)

#         cooldown = self.get_cooldown(event_type)

#         minimum_audio_duration = self.get_minimum_audio_duration(event_type)

#         capture_once = self._capture_once_per_incident(event_type)

#         now = time.monotonic()

#         if not active:

#             self._reset_state(
#                 event_type,
#                 state,
#             )

#             return self._empty_result(
#                 event_type=event_type,
#                 active=False,
#                 confirmed=False,
#                 duration=0.0,
#                 required_duration=minimum_audio_duration,
#                 cooldown=cooldown,
#                 cooldown_remaining=self._get_cooldown_remaining(
#                     state,
#                     now,
#                     cooldown,
#                 ),
#             )

#         state["last_active_at"] = now

#         if state["started_at"] is None:

#             state["started_at"] = now

#         if not isinstance(
#             audio_evidence,
#             dict,
#         ):

#             result = self._empty_result(
#                 event_type=event_type,
#                 active=True,
#                 confirmed=False,
#                 duration=0.0,
#                 required_duration=minimum_audio_duration,
#                 cooldown=cooldown,
#                 cooldown_remaining=self._get_cooldown_remaining(
#                     state,
#                     now,
#                     cooldown,
#                 ),
#             )

#             result["error"] = "Audio evidence is missing."

#             return result

#         event_metadata = dict(metadata or {})

#         detected_duration = event_metadata.get("voice_duration_seconds")

#         if detected_duration is None:

#             detected_duration = audio_evidence.get("voice_duration_seconds")

#         if detected_duration is None:

#             detected_duration = audio_evidence.get("duration_seconds")

#         try:

#             detected_duration = float(detected_duration or 0.0)

#         except (
#             TypeError,
#             ValueError,
#         ):

#             detected_duration = 0.0

#         if detected_duration < minimum_audio_duration:

#             return self._empty_result(
#                 event_type=event_type,
#                 active=True,
#                 confirmed=False,
#                 duration=detected_duration,
#                 required_duration=minimum_audio_duration,
#                 cooldown=cooldown,
#                 cooldown_remaining=self._get_cooldown_remaining(
#                     state,
#                     now,
#                     cooldown,
#                 ),
#             )

#         state["confirmed"] = True

#         if capture_once and state.get(
#             "captured_in_incident",
#             False,
#         ):

#             return self._empty_result(
#                 event_type=event_type,
#                 active=True,
#                 confirmed=True,
#                 duration=detected_duration,
#                 required_duration=minimum_audio_duration,
#                 cooldown=cooldown,
#                 cooldown_remaining=self._get_cooldown_remaining(
#                     state,
#                     now,
#                     cooldown,
#                 ),
#             )

#         cooldown_remaining = self._get_cooldown_remaining(
#             state,
#             now,
#             cooldown,
#         )

#         if cooldown_remaining > 0.0:

#             return self._empty_result(
#                 event_type=event_type,
#                 active=True,
#                 confirmed=True,
#                 duration=detected_duration,
#                 required_duration=minimum_audio_duration,
#                 cooldown=cooldown,
#                 cooldown_remaining=cooldown_remaining,
#             )

#         event_metadata["event_duration_seconds"] = round(
#             detected_duration,
#             2,
#         )

#         event_metadata["required_duration_seconds"] = round(
#             minimum_audio_duration,
#             2,
#         )

#         event_metadata["evidence_cooldown_seconds"] = round(
#             cooldown,
#             2,
#         )

#         event_metadata["evidence_type"] = "audio"

#         event_metadata["audio_sample_rate"] = audio_evidence.get("sample_rate")

#         event_metadata["audio_channels"] = audio_evidence.get(
#             "channels",
#             1,
#         )

#         event_metadata["audio_sample_width"] = audio_evidence.get(
#             "sample_width",
#             2,
#         )

#         event_metadata["audio_buffer_duration_seconds"] = audio_evidence.get(
#             "duration_seconds"
#         )

#         print(
#             f"[ANOMALY] DETECTED "
#             f"{event_type} "
#             f"| voice_duration="
#             f"{detected_duration:.2f}s"
#         )

#         try:

#             evidence = self._capture_audio_evidence(
#                 event_type=event_type,
#                 audio_evidence=audio_evidence,
#                 event_metadata=event_metadata,
#             )

#         except Exception as error:

#             print(
#                 f"[ANOMALY] Audio evidence capture "
#                 f"failed for "
#                 f"{event_type}: "
#                 f"{error}"
#             )

#             result = self._empty_result(
#                 event_type=event_type,
#                 active=True,
#                 confirmed=True,
#                 duration=detected_duration,
#                 required_duration=minimum_audio_duration,
#                 cooldown=cooldown,
#                 cooldown_remaining=0.0,
#             )

#             result["error"] = str(error)

#             return result

#         if evidence is None:

#             return self._empty_result(
#                 event_type=event_type,
#                 active=True,
#                 confirmed=True,
#                 duration=detected_duration,
#                 required_duration=minimum_audio_duration,
#                 cooldown=cooldown,
#                 cooldown_remaining=0.0,
#             )

#         state["last_capture_at"] = now

#         if capture_once:

#             state["captured_in_incident"] = True

#         api_violation = self._build_api_violation(
#             event_type=event_type,
#             evidence=evidence,
#             event_metadata=event_metadata,
#         )

#         print(f"[ANOMALY] AUDIO EVIDENCE CAPTURED " f"{event_type}")

#         result = {
#             "event_type": event_type,
#             "active": True,
#             "confirmed": True,
#             "captured": True,
#             "duration": detected_duration,
#             "required_duration": minimum_audio_duration,
#             "cooldown": cooldown,
#             "cooldown_remaining": 0.0,
#             "evidence": evidence,
#             "api_violation": api_violation,
#         }

#         if self.socket_client is not None:

#             self._notify_socket(result)

#         return result

#     def get_cooldown_remaining(
#         self,
#         event_type,
#     ):
#         event_type = str(event_type).upper().strip()

#         state = self.states.get(event_type)

#         if state is None:
#             return 0.0

#         now = time.monotonic()

#         cooldown = self.get_cooldown(event_type)

#         return self._get_cooldown_remaining(
#             state,
#             now,
#             cooldown,
#         )

#     def update_many(
#         self,
#         anomalies,
#         frame,
#         metadata=None,
#     ):
#         results = {}

#         shared_metadata = dict(metadata or {})

#         if not isinstance(
#             anomalies,
#             dict,
#         ):

#             return results

#         for (
#             event_type,
#             active,
#         ) in anomalies.items():

#             event_metadata = {}

#             possible_event_metadata = shared_metadata.get(event_type)

#             if isinstance(
#                 possible_event_metadata,
#                 dict,
#             ):

#                 event_metadata.update(possible_event_metadata)

#             else:

#                 event_metadata.update(shared_metadata)

#             normalized_event_type = str(event_type).upper().strip()

#             results[normalized_event_type] = self.update(
#                 event_type=event_type,
#                 active=active,
#                 frame=frame,
#                 metadata=event_metadata,
#             )

#         return results

#     def reset_event(
#         self,
#         event_type,
#     ):
#         event_type = str(event_type).upper().strip()

#         state = self.states.get(event_type)

#         if state is None:
#             return

#         self._reset_state(
#             event_type,
#             state,
#         )

#     def reset_all(
#         self,
#     ):
#         for (
#             event_type,
#             state,
#         ) in list(self.states.items()):

#             self._reset_state(
#                 event_type,
#                 state,
#             )

#         self.states.clear()

#         print("[ANOMALY] All anomaly states reset.")

#     def get_state(
#         self,
#         event_type,
#     ):
#         event_type = str(event_type).upper().strip()

#         state = self.states.get(event_type)

#         if state is None:

#             return {
#                 "started_at": None,
#                 "last_active_at": None,
#                 "last_capture_at": None,
#                 "confirmed": False,
#                 "captured_in_incident": False,
#             }

#         result = dict(state)

#         if "captured_in_incident" not in result:

#             result["captured_in_incident"] = False

#         return result

#     def get_all_states(
#         self,
#     ):
#         return {event_type: self.get_state(event_type) for event_type in self.states}

#     def close(
#         self,
#     ):
#         self.reset_all()

#         print("[ANOMALY] Manager closed.")


import time

import cv2

from src.config.settings import settings


class AnomalyManager:

    DEFAULT_RULE = {
        "duration": 0.0,
        "cooldown": 12.0,
        "recovery_grace": 0.0,
        "capture_once_per_incident": False,
    }

    AUDIO_EVENT_TYPES = {
        "VOICE_DETECTED",
    }

    EVIDENCE_COLORS = {
        "PHONE_DETECTED": (0, 165, 255),
        "BOOK_DETECTED": (0, 191, 255),
        "MULTIPLE_FACES": (0, 0, 255),
        "EXTRA_PERSON": (0, 0, 255),
        "HEAD_AWAY": (0, 0, 255),
        "GAZE_AWAY": (0, 165, 255),
        "NO_FACE": (0, 0, 255),
        "BODY_LEAN_LEFT": (0, 165, 255),
        "BODY_LEAN_RIGHT": (0, 165, 255),
        "LEFT_ARM_RAISED": (0, 165, 255),
        "RIGHT_ARM_RAISED": (0, 165, 255),
        "UNUSUAL_ARM_MOVEMENT": (0, 0, 255),
        "UPPER_BODY_NOT_VISIBLE": (0, 0, 255),
        "CAMERA_OFF": (0, 0, 255),
        "CAMERA_ERROR": (0, 0, 255),
    }

    EVIDENCE_LABELS = {
        "PHONE_DETECTED": "PHONE DETECTED",
        "BOOK_DETECTED": "BOOK DETECTED",
        "MULTIPLE_FACES": "MULTIPLE FACES",
        "EXTRA_PERSON": "EXTRA PERSON",
        "HEAD_AWAY": "HEAD AWAY",
        "GAZE_AWAY": "GAZE AWAY",
        "NO_FACE": "NO FACE",
        "BODY_LEAN_LEFT": "BODY LEAN LEFT",
        "BODY_LEAN_RIGHT": "BODY LEAN RIGHT",
        "LEFT_ARM_RAISED": "LEFT ARM RAISED",
        "RIGHT_ARM_RAISED": "RIGHT ARM RAISED",
        "UNUSUAL_ARM_MOVEMENT": "UNUSUAL ARM MOVEMENT",
        "UPPER_BODY_NOT_VISIBLE": "UPPER BODY NOT VISIBLE",
        "CAMERA_OFF": "CAMERA OFF",
        "CAMERA_ERROR": "CAMERA ERROR",
    }

    def __init__(
        self,
        evidence_store,
        socket_client=None,
    ):
        if evidence_store is None:
            raise ValueError("AnomalyManager requires an evidence_store.")

        self.evidence_store = evidence_store
        self.socket_client = socket_client

        self.rules = {
            "NO_FACE": {
                "duration": 2.0,
                "cooldown": settings.EVIDENCE_COOLDOWN_NO_FACE,
                "recovery_grace": 0.5,
                "capture_once_per_incident": True,
            },
            "MULTIPLE_FACES": {
                "duration": 0.0,
                "cooldown": settings.EVIDENCE_COOLDOWN_MULTIPLE_FACES,
                "recovery_grace": 0.5,
                "capture_once_per_incident": False,
            },
            "GAZE_AWAY": {
                "duration": 3.0,
                "cooldown": settings.EVIDENCE_COOLDOWN_GAZE_AWAY,
                "recovery_grace": 0.8,
                "capture_once_per_incident": False,
            },
            "HEAD_AWAY": {
                "duration": 1.0,
                "cooldown": settings.EVIDENCE_COOLDOWN_HEAD_AWAY,
                "recovery_grace": 0.8,
                "capture_once_per_incident": False,
            },
            "PHONE_DETECTED": {
                "duration": 0.3,
                "cooldown": settings.EVIDENCE_COOLDOWN_PHONE_DETECTED,
                "recovery_grace": 1.0,
                "capture_once_per_incident": False,
            },
            "BOOK_DETECTED": {
                "duration": 1.0,
                "cooldown": settings.EVIDENCE_COOLDOWN_BOOK_DETECTED,
                "recovery_grace": 1.0,
                "capture_once_per_incident": False,
            },
            "EXTRA_PERSON": {
                "duration": 1.0,
                "cooldown": settings.EVIDENCE_COOLDOWN_EXTRA_PERSON,
                "recovery_grace": 1.0,
                "capture_once_per_incident": False,
            },
            "BODY_LEAN_LEFT": {
                "duration": 2.0,
                "cooldown": settings.EVIDENCE_COOLDOWN_BODY_LEAN_LEFT,
                "recovery_grace": 0.8,
                "capture_once_per_incident": False,
            },
            "BODY_LEAN_RIGHT": {
                "duration": 2.0,
                "cooldown": settings.EVIDENCE_COOLDOWN_BODY_LEAN_RIGHT,
                "recovery_grace": 0.8,
                "capture_once_per_incident": False,
            },
            "LEFT_ARM_RAISED": {
                "duration": 2.0,
                "cooldown": settings.EVIDENCE_COOLDOWN_LEFT_ARM_RAISED,
                "recovery_grace": 0.8,
                "capture_once_per_incident": False,
            },
            "RIGHT_ARM_RAISED": {
                "duration": 2.0,
                "cooldown": settings.EVIDENCE_COOLDOWN_RIGHT_ARM_RAISED,
                "recovery_grace": 0.8,
                "capture_once_per_incident": False,
            },
            "UNUSUAL_ARM_MOVEMENT": {
                "duration": 1.5,
                "cooldown": settings.EVIDENCE_COOLDOWN_UNUSUAL_ARM_MOVEMENT,
                "recovery_grace": 1.0,
                "capture_once_per_incident": False,
            },
            "UPPER_BODY_NOT_VISIBLE": {
                "duration": 2.0,
                "cooldown": settings.EVIDENCE_COOLDOWN_UPPER_BODY_NOT_VISIBLE,
                "recovery_grace": 0.8,
                "capture_once_per_incident": False,
            },
            "CAMERA_OFF": {
                "duration": 0.0,
                "cooldown": settings.EVIDENCE_COOLDOWN_CAMERA_OFF,
                "recovery_grace": 0.0,
                "capture_once_per_incident": False,
            },
            "MIC_OFF": {
                "duration": 0.0,
                "cooldown": settings.EVIDENCE_COOLDOWN_MIC_OFF,
                "recovery_grace": 0.0,
                "capture_once_per_incident": False,
            },
            "CAMERA_ERROR": {
                "duration": 0.0,
                "cooldown": settings.EVIDENCE_COOLDOWN_CAMERA_ERROR,
                "recovery_grace": 0.0,
                "capture_once_per_incident": False,
            },
            "MIC_ERROR": {
                "duration": 0.0,
                "cooldown": settings.EVIDENCE_COOLDOWN_MIC_ERROR,
                "recovery_grace": 0.0,
                "capture_once_per_incident": False,
            },
            "VOICE_DETECTED": {
                "duration": 0.0,
                "cooldown": getattr(
                    settings,
                    "EVIDENCE_COOLDOWN_VOICE_DETECTED",
                    12.0,
                ),
                "recovery_grace": 0.75,
                "capture_once_per_incident": True,
                "minimum_audio_duration": 0.25,
            },
        }

        self.states = {}

        print("[ANOMALY] Manager initialized.")

        print(f"[ANOMALY] " f"{len(self.rules)} anomaly rules loaded.")

    def set_socket_client(
        self,
        socket_client,
    ):
        self.socket_client = socket_client

        if socket_client is None:
            print("[ANOMALY] Socket client detached.")

        else:
            print("[ANOMALY] Socket client attached.")

    def _notify_socket(
        self,
        anomaly_result,
    ):
        if self.socket_client is None:
            return False

        if not isinstance(
            anomaly_result,
            dict,
        ):
            return False

        if not anomaly_result.get("captured"):
            return False

        api_violation = anomaly_result.get("api_violation")

        if not isinstance(
            api_violation,
            dict,
        ):
            return False

        try:
            notify_anomaly_result = getattr(
                self.socket_client,
                "notify_anomaly_result",
                None,
            )

            if callable(notify_anomaly_result):
                sent = notify_anomaly_result(anomaly_result)

                if sent:
                    print(
                        "[ANOMALY] Socket notification sent "
                        f"for "
                        f"{anomaly_result.get('event_type')}."
                    )

                else:
                    print(
                        "[ANOMALY] Socket notification was not sent "
                        f"for "
                        f"{anomaly_result.get('event_type')}."
                    )

                return bool(sent)

            notify_proctor_violation = getattr(
                self.socket_client,
                "notify_proctor_violation",
                None,
            )

            if callable(notify_proctor_violation):
                sent = notify_proctor_violation(api_violation)

                if sent:
                    print(
                        "[ANOMALY] Socket violation notification sent "
                        f"for "
                        f"{anomaly_result.get('event_type')}."
                    )

                else:
                    print(
                        "[ANOMALY] Socket violation notification "
                        f"was not sent for "
                        f"{anomaly_result.get('event_type')}."
                    )

                return bool(sent)

            print(
                "[ANOMALY] Socket client does not provide "
                "notify_anomaly_result() or "
                "notify_proctor_violation()."
            )

            return False

        except Exception as error:
            print(
                "[ANOMALY] Failed to send socket notification "
                f"for "
                f"{anomaly_result.get('event_type')}: "
                f"{error}"
            )

            return False

    def notify_recorded_result(
        self,
        anomaly_result,
    ):
        return self._notify_socket(anomaly_result)

    def _get_rule(
        self,
        event_type,
    ):
        return self.rules.get(
            event_type,
            self.DEFAULT_RULE,
        )

    def _get_state(
        self,
        event_type,
    ):
        if event_type not in self.states:
            self.states[event_type] = {
                "started_at": None,
                "last_active_at": None,
                "last_capture_at": None,
                "confirmed": False,
                "captured_in_incident": False,
            }

        state = self.states[event_type]

        if "captured_in_incident" not in state:
            state["captured_in_incident"] = False

        return state

    def _reset_state(
        self,
        event_type,
        state,
    ):
        if state.get("confirmed"):
            print(f"[ANOMALY] RECOVERED " f"{event_type}")

        state["started_at"] = None

        state["last_active_at"] = None

        state["confirmed"] = False

        state["captured_in_incident"] = False

    def get_cooldown(
        self,
        event_type,
    ):
        event_type = str(event_type).upper().strip()

        rule = self._get_rule(event_type)

        try:
            cooldown = float(
                rule.get(
                    "cooldown",
                    12.0,
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            cooldown = 12.0

        return max(
            0.0,
            cooldown,
        )

    def get_required_duration(
        self,
        event_type,
    ):
        event_type = str(event_type).upper().strip()

        rule = self._get_rule(event_type)

        try:
            duration = float(
                rule.get(
                    "duration",
                    0.0,
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            duration = 0.0

        return max(
            0.0,
            duration,
        )

    def get_minimum_audio_duration(
        self,
        event_type,
    ):
        event_type = str(event_type).upper().strip()

        rule = self._get_rule(event_type)

        try:
            duration = float(
                rule.get(
                    "minimum_audio_duration",
                    0.0,
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            duration = 0.0

        return max(
            0.0,
            duration,
        )

    def _get_recovery_grace(
        self,
        event_type,
    ):
        rule = self._get_rule(event_type)

        try:
            recovery_grace = float(
                rule.get(
                    "recovery_grace",
                    0.0,
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            recovery_grace = 0.0

        return max(
            0.0,
            recovery_grace,
        )

    def _capture_once_per_incident(
        self,
        event_type,
    ):
        rule = self._get_rule(event_type)

        return bool(
            rule.get(
                "capture_once_per_incident",
                False,
            )
        )

    def _get_cooldown_remaining(
        self,
        state,
        now,
        cooldown,
    ):
        last_capture_at = state.get("last_capture_at")

        if last_capture_at is None:
            return 0.0

        elapsed = now - last_capture_at

        return max(
            0.0,
            cooldown - elapsed,
        )

    def _build_api_violation(
        self,
        event_type,
        evidence,
        event_metadata,
    ):
        if not evidence:
            return None

        file_path = evidence.get("file_path")

        if not file_path:
            file_path = evidence.get("image_path")

        if not file_path:
            file_path = evidence.get("audio_path")

        metadata_path = evidence.get("metadata_path")

        event_payload = evidence.get("event")

        client_captured_at = None

        if isinstance(
            event_payload,
            dict,
        ):
            client_captured_at = event_payload.get("captured_at")

        if not client_captured_at:
            client_captured_at = evidence.get("client_captured_at")

        violation_metadata = dict(event_metadata or {})

        if metadata_path:
            violation_metadata["evidence_metadata_path"] = metadata_path

        evidence_type = evidence.get("evidence_type")

        if evidence_type:
            violation_metadata["evidence_type"] = evidence_type

        return {
            "violation_type": event_type,
            "client_captured_at": client_captured_at,
            "metadata": violation_metadata,
            "file_path": file_path,
        }

    def _empty_result(
        self,
        event_type,
        active,
        confirmed,
        duration,
        required_duration,
        cooldown,
        cooldown_remaining,
    ):
        return {
            "event_type": event_type,
            "active": bool(active),
            "confirmed": bool(confirmed),
            "captured": False,
            "duration": duration,
            "required_duration": required_duration,
            "cooldown": cooldown,
            "cooldown_remaining": cooldown_remaining,
            "evidence": None,
            "api_violation": None,
        }

    def _normalize_evidence_box(
        self,
        frame,
        detection,
    ):
        if frame is None or not isinstance(
            detection,
            dict,
        ):
            return None

        try:
            if all(
                key in detection
                for key in (
                    "x",
                    "y",
                    "x2",
                    "y2",
                )
            ):
                x1 = int(detection["x"])

                y1 = int(detection["y"])

                x2 = int(detection["x2"])

                y2 = int(detection["y2"])

            elif all(
                key in detection
                for key in (
                    "x",
                    "y",
                    "w",
                    "h",
                )
            ):
                x1 = int(detection["x"])

                y1 = int(detection["y"])

                x2 = x1 + int(detection["w"])

                y2 = y1 + int(detection["h"])

            elif all(
                key in detection
                for key in (
                    "x",
                    "y",
                    "width",
                    "height",
                )
            ):
                x1 = int(detection["x"])

                y1 = int(detection["y"])

                x2 = x1 + int(detection["width"])

                y2 = y1 + int(detection["height"])

            elif (
                isinstance(
                    detection.get("bbox"),
                    (
                        list,
                        tuple,
                    ),
                )
                and len(detection["bbox"]) >= 4
            ):
                x1 = int(detection["bbox"][0])

                y1 = int(detection["bbox"][1])

                third = int(detection["bbox"][2])

                fourth = int(detection["bbox"][3])

                bbox_mode = (
                    str(
                        detection.get(
                            "bbox_mode",
                            "xywh",
                        )
                    )
                    .lower()
                    .strip()
                )

                if bbox_mode in {
                    "xyxy",
                    "x1y1x2y2",
                }:
                    x2 = third
                    y2 = fourth

                else:
                    x2 = x1 + third

                    y2 = y1 + fourth

            else:
                return None

        except (
            TypeError,
            ValueError,
            KeyError,
            IndexError,
        ):
            return None

        frame_height, frame_width = frame.shape[:2]

        x1 = max(
            0,
            min(
                frame_width - 1,
                x1,
            ),
        )

        y1 = max(
            0,
            min(
                frame_height - 1,
                y1,
            ),
        )

        x2 = max(
            0,
            min(
                frame_width - 1,
                x2,
            ),
        )

        y2 = max(
            0,
            min(
                frame_height - 1,
                y2,
            ),
        )

        if x2 <= x1 or y2 <= y1:
            return None

        return (
            x1,
            y1,
            x2,
            y2,
        )

    def _draw_evidence_badge(
        self,
        frame,
        text,
        color,
        x=8,
        y=8,
    ):
        if frame is None:
            return

        safe_text = str(text or "VIOLATION").strip().upper()

        font = cv2.FONT_HERSHEY_SIMPLEX

        font_scale = 0.46
        thickness = 1
        padding_x = 7
        padding_y = 6

        (
            text_size,
            baseline,
        ) = cv2.getTextSize(
            safe_text,
            font,
            font_scale,
            thickness,
        )

        (
            text_width,
            text_height,
        ) = text_size

        frame_height, frame_width = frame.shape[:2]

        x1 = max(
            0,
            min(
                frame_width - 1,
                int(x),
            ),
        )

        y1 = max(
            0,
            min(
                frame_height - 1,
                int(y),
            ),
        )

        x2 = min(
            frame_width - 1,
            (x1 + text_width + (padding_x * 2)),
        )

        y2 = min(
            frame_height - 1,
            (y1 + text_height + (padding_y * 2) + baseline),
        )

        cv2.rectangle(
            frame,
            (
                x1,
                y1,
            ),
            (
                x2,
                y2,
            ),
            color,
            -1,
        )

        cv2.putText(
            frame,
            safe_text,
            (
                x1 + padding_x,
                min(
                    frame_height - 1,
                    (y1 + padding_y + text_height),
                ),
            ),
            font,
            font_scale,
            (
                255,
                255,
                255,
            ),
            thickness,
            cv2.LINE_AA,
        )

    def _draw_evidence_box(
        self,
        frame,
        detection,
        color,
        label=None,
    ):
        box = self._normalize_evidence_box(
            frame,
            detection,
        )

        if box is None:
            return False

        (
            x1,
            y1,
            x2,
            y2,
        ) = box

        cv2.rectangle(
            frame,
            (
                x1,
                y1,
            ),
            (
                x2,
                y2,
            ),
            color,
            3,
        )

        if label:
            self._draw_evidence_badge(
                frame,
                label,
                color,
                x=x1,
                y=max(
                    0,
                    y1 - 28,
                ),
            )

        return True

    def _get_metadata_list(
        self,
        metadata,
        *keys,
    ):
        if not isinstance(
            metadata,
            dict,
        ):
            return []

        for key in keys:
            value = metadata.get(key)

            if isinstance(
                value,
                list,
            ):
                return value

        return []

    def _filter_object_detections(
        self,
        metadata,
        labels,
    ):
        normalized_labels = {str(label).upper().strip() for label in labels}

        detections = self._get_metadata_list(
            metadata,
            "objects",
            "object_detections",
            "detections",
        )

        result = []

        for detection in detections:
            if not isinstance(
                detection,
                dict,
            ):
                continue

            label = (
                str(
                    detection.get(
                        "label",
                        "",
                    )
                )
                .upper()
                .strip()
            )

            if label in normalized_labels:
                result.append(detection)

        return result

    def _get_confirmed_phone_detections(
        self,
        metadata,
    ):
        confirmed = []

        gate_results = self._get_metadata_list(
            metadata,
            "phone_gate_results",
        )

        for item in gate_results:
            if not isinstance(
                item,
                dict,
            ):
                continue

            if not bool(
                item.get(
                    "gate_2_confirmed",
                    False,
                )
            ):
                continue

            detection = item.get("detection")

            if isinstance(
                detection,
                dict,
            ):
                confirmed.append(detection)

        if confirmed:
            return confirmed

        return self._filter_object_detections(
            metadata,
            {
                "CELL_PHONE",
                "PHONE",
                "MOBILE_PHONE",
                "MOBILE",
            },
        )

    def _build_annotated_evidence_frame(
        self,
        event_type,
        frame,
        event_metadata=None,
        evidence_frame=None,
        evidence_regions=None,
    ):
        source_frame = evidence_frame if evidence_frame is not None else frame

        if source_frame is None:
            return None

        try:
            annotated = source_frame.copy()

        except Exception:
            return source_frame

        normalized_event_type = str(event_type or "").upper().strip()

        metadata = dict(event_metadata or {})

        color = self.EVIDENCE_COLORS.get(
            normalized_event_type,
            (
                0,
                0,
                255,
            ),
        )

        event_label = self.EVIDENCE_LABELS.get(
            normalized_event_type,
            normalized_event_type.replace(
                "_",
                " ",
            )
            or "VIOLATION",
        )

        explicit_regions = []

        if isinstance(
            evidence_regions,
            list,
        ):
            explicit_regions = [
                item
                for item in evidence_regions
                if isinstance(
                    item,
                    dict,
                )
            ]

        regions = []
        box_label = None

        if explicit_regions:
            regions = explicit_regions

        elif normalized_event_type == "PHONE_DETECTED":
            regions = self._get_confirmed_phone_detections(metadata)

            box_label = "PHONE"

        elif normalized_event_type == "BOOK_DETECTED":
            regions = self._filter_object_detections(
                metadata,
                {
                    "BOOK",
                },
            )

            box_label = "BOOK"

        elif normalized_event_type == "EXTRA_PERSON":
            regions = self._filter_object_detections(
                metadata,
                {
                    "PERSON",
                    "HUMAN",
                },
            )

            box_label = "PERSON"

        elif normalized_event_type == "MULTIPLE_FACES":
            regions = self._get_metadata_list(
                metadata,
                "faces",
                "face_detections",
                "detected_faces",
            )

            box_label = "FACE"

        drawn_regions = 0

        for region in regions:
            region_label = (
                region.get("evidence_label")
                if isinstance(
                    region,
                    dict,
                )
                else None
            )

            if self._draw_evidence_box(
                annotated,
                region,
                color,
                label=(region_label or box_label),
            ):
                drawn_regions += 1

        self._draw_evidence_badge(
            annotated,
            event_label,
            color,
            x=8,
            y=8,
        )

        annotation_metadata = {
            "event_type": normalized_event_type,
            "label": event_label,
            "region_count": drawn_regions,
            "color_bgr": [
                int(color[0]),
                int(color[1]),
                int(color[2]),
            ],
        }

        if isinstance(
            event_metadata,
            dict,
        ):
            event_metadata["evidence_annotation"] = annotation_metadata

        return annotated

    def _capture_image_evidence(
        self,
        event_type,
        frame,
        event_metadata,
    ):
        return self.evidence_store.capture(
            frame=frame,
            event_type=event_type,
            metadata=event_metadata,
        )

    def _capture_audio_evidence(
        self,
        event_type,
        audio_evidence,
        event_metadata,
    ):
        capture_audio = getattr(
            self.evidence_store,
            "capture_audio",
            None,
        )

        if not callable(capture_audio):
            raise RuntimeError("EvidenceStore does not provide capture_audio().")

        if not isinstance(
            audio_evidence,
            dict,
        ):
            raise ValueError("Audio evidence must be a dictionary.")

        pcm = audio_evidence.get("pcm")

        sample_rate = audio_evidence.get("sample_rate")

        channels = audio_evidence.get(
            "channels",
            1,
        )

        sample_width = audio_evidence.get(
            "sample_width",
            2,
        )

        if not pcm:
            raise ValueError("Audio evidence contains no PCM data.")

        if not sample_rate:
            raise ValueError("Audio evidence sample rate is missing.")

        return capture_audio(
            pcm=pcm,
            sample_rate=int(sample_rate),
            channels=int(channels),
            sample_width=int(sample_width),
            event_type=event_type,
            metadata=event_metadata,
        )

    def update(
        self,
        event_type,
        active,
        frame,
        metadata=None,
        evidence_frame=None,
        evidence_regions=None,
    ):
        event_type = str(event_type).upper().strip()

        if not event_type:
            return {
                "event_type": "",
                "active": False,
                "confirmed": False,
                "captured": False,
                "duration": 0.0,
                "required_duration": 0.0,
                "cooldown": 0.0,
                "cooldown_remaining": 0.0,
                "evidence": None,
                "api_violation": None,
            }

        active = bool(active)

        required_duration = self.get_required_duration(event_type)

        cooldown = self.get_cooldown(event_type)

        recovery_grace = self._get_recovery_grace(event_type)

        capture_once = self._capture_once_per_incident(event_type)

        state = self._get_state(event_type)

        now = time.monotonic()

        if active:
            state["last_active_at"] = now

            if state["started_at"] is None:
                state["started_at"] = now

        else:
            if state["started_at"] is None:
                return self._empty_result(
                    event_type=event_type,
                    active=False,
                    confirmed=False,
                    duration=0.0,
                    required_duration=required_duration,
                    cooldown=cooldown,
                    cooldown_remaining=self._get_cooldown_remaining(
                        state,
                        now,
                        cooldown,
                    ),
                )

            last_active_at = state.get("last_active_at")

            if last_active_at is not None and (now - last_active_at) < recovery_grace:
                active = True

            else:
                self._reset_state(
                    event_type,
                    state,
                )

                return self._empty_result(
                    event_type=event_type,
                    active=False,
                    confirmed=False,
                    duration=0.0,
                    required_duration=required_duration,
                    cooldown=cooldown,
                    cooldown_remaining=self._get_cooldown_remaining(
                        state,
                        now,
                        cooldown,
                    ),
                )

        started_at = state.get("started_at")

        if started_at is None:
            duration = 0.0

        else:
            duration = max(
                0.0,
                now - started_at,
            )

        if duration < required_duration:
            return self._empty_result(
                event_type=event_type,
                active=True,
                confirmed=False,
                duration=duration,
                required_duration=required_duration,
                cooldown=cooldown,
                cooldown_remaining=self._get_cooldown_remaining(
                    state,
                    now,
                    cooldown,
                ),
            )

        if not state["confirmed"]:
            state["confirmed"] = True

            print(
                f"[ANOMALY] DETECTED "
                f"{event_type} "
                f"| duration="
                f"{duration:.2f}s"
            )

        if capture_once and state.get(
            "captured_in_incident",
            False,
        ):
            return self._empty_result(
                event_type=event_type,
                active=True,
                confirmed=True,
                duration=duration,
                required_duration=required_duration,
                cooldown=cooldown,
                cooldown_remaining=self._get_cooldown_remaining(
                    state,
                    now,
                    cooldown,
                ),
            )

        cooldown_remaining = self._get_cooldown_remaining(
            state,
            now,
            cooldown,
        )

        if cooldown_remaining > 0.0:
            return self._empty_result(
                event_type=event_type,
                active=True,
                confirmed=True,
                duration=duration,
                required_duration=required_duration,
                cooldown=cooldown,
                cooldown_remaining=cooldown_remaining,
            )

        event_metadata = dict(metadata or {})

        event_metadata["event_duration_seconds"] = round(
            duration,
            2,
        )

        event_metadata["required_duration_seconds"] = round(
            required_duration,
            2,
        )

        event_metadata["evidence_cooldown_seconds"] = round(
            cooldown,
            2,
        )

        event_metadata["recovery_grace_seconds"] = round(
            recovery_grace,
            2,
        )

        event_metadata["evidence_type"] = "image"

        try:
            capture_frame = self._build_annotated_evidence_frame(
                event_type=event_type,
                frame=frame,
                event_metadata=event_metadata,
                evidence_frame=evidence_frame,
                evidence_regions=evidence_regions,
            )

            evidence = self._capture_image_evidence(
                event_type=event_type,
                frame=capture_frame,
                event_metadata=event_metadata,
            )

        except Exception as error:
            print(
                f"[ANOMALY] Evidence capture "
                f"failed for "
                f"{event_type}: "
                f"{error}"
            )

            result = self._empty_result(
                event_type=event_type,
                active=True,
                confirmed=True,
                duration=duration,
                required_duration=required_duration,
                cooldown=cooldown,
                cooldown_remaining=cooldown,
            )

            result["error"] = str(error)

            return result

        if evidence is not None:
            state["last_capture_at"] = now

            if capture_once:
                state["captured_in_incident"] = True

            api_violation = self._build_api_violation(
                event_type=event_type,
                evidence=evidence,
                event_metadata=event_metadata,
            )

            print(f"[ANOMALY] EVIDENCE CAPTURED " f"{event_type}")

            result = {
                "event_type": event_type,
                "active": True,
                "confirmed": True,
                "captured": True,
                "duration": duration,
                "required_duration": required_duration,
                "cooldown": cooldown,
                "cooldown_remaining": 0.0,
                "evidence": evidence,
                "api_violation": api_violation,
            }

            if self.socket_client is not None:
                self._notify_socket(result)

            return result

        return self._empty_result(
            event_type=event_type,
            active=True,
            confirmed=True,
            duration=duration,
            required_duration=required_duration,
            cooldown=cooldown,
            cooldown_remaining=cooldown,
        )

    def update_audio(
        self,
        event_type,
        active,
        audio_evidence=None,
        metadata=None,
    ):
        event_type = str(event_type).upper().strip()

        if not event_type:
            return {
                "event_type": "",
                "active": False,
                "confirmed": False,
                "captured": False,
                "duration": 0.0,
                "required_duration": 0.0,
                "cooldown": 0.0,
                "cooldown_remaining": 0.0,
                "evidence": None,
                "api_violation": None,
            }

        active = bool(active)

        state = self._get_state(event_type)

        cooldown = self.get_cooldown(event_type)

        minimum_audio_duration = self.get_minimum_audio_duration(event_type)

        capture_once = self._capture_once_per_incident(event_type)

        now = time.monotonic()

        if not active:
            self._reset_state(
                event_type,
                state,
            )

            return self._empty_result(
                event_type=event_type,
                active=False,
                confirmed=False,
                duration=0.0,
                required_duration=minimum_audio_duration,
                cooldown=cooldown,
                cooldown_remaining=self._get_cooldown_remaining(
                    state,
                    now,
                    cooldown,
                ),
            )

        state["last_active_at"] = now

        if state["started_at"] is None:
            state["started_at"] = now

        if not isinstance(
            audio_evidence,
            dict,
        ):
            result = self._empty_result(
                event_type=event_type,
                active=True,
                confirmed=False,
                duration=0.0,
                required_duration=minimum_audio_duration,
                cooldown=cooldown,
                cooldown_remaining=self._get_cooldown_remaining(
                    state,
                    now,
                    cooldown,
                ),
            )

            result["error"] = "Audio evidence is missing."

            return result

        event_metadata = dict(metadata or {})

        detected_duration = event_metadata.get("voice_duration_seconds")

        if detected_duration is None:
            detected_duration = audio_evidence.get("voice_duration_seconds")

        if detected_duration is None:
            detected_duration = audio_evidence.get("duration_seconds")

        try:
            detected_duration = float(detected_duration or 0.0)

        except (
            TypeError,
            ValueError,
        ):
            detected_duration = 0.0

        if detected_duration < minimum_audio_duration:
            return self._empty_result(
                event_type=event_type,
                active=True,
                confirmed=False,
                duration=detected_duration,
                required_duration=minimum_audio_duration,
                cooldown=cooldown,
                cooldown_remaining=self._get_cooldown_remaining(
                    state,
                    now,
                    cooldown,
                ),
            )

        state["confirmed"] = True

        if capture_once and state.get(
            "captured_in_incident",
            False,
        ):
            return self._empty_result(
                event_type=event_type,
                active=True,
                confirmed=True,
                duration=detected_duration,
                required_duration=minimum_audio_duration,
                cooldown=cooldown,
                cooldown_remaining=self._get_cooldown_remaining(
                    state,
                    now,
                    cooldown,
                ),
            )

        cooldown_remaining = self._get_cooldown_remaining(
            state,
            now,
            cooldown,
        )

        if cooldown_remaining > 0.0:
            return self._empty_result(
                event_type=event_type,
                active=True,
                confirmed=True,
                duration=detected_duration,
                required_duration=minimum_audio_duration,
                cooldown=cooldown,
                cooldown_remaining=cooldown_remaining,
            )

        event_metadata["event_duration_seconds"] = round(
            detected_duration,
            2,
        )

        event_metadata["required_duration_seconds"] = round(
            minimum_audio_duration,
            2,
        )

        event_metadata["evidence_cooldown_seconds"] = round(
            cooldown,
            2,
        )

        event_metadata["evidence_type"] = "audio"

        event_metadata["audio_sample_rate"] = audio_evidence.get("sample_rate")

        event_metadata["audio_channels"] = audio_evidence.get(
            "channels",
            1,
        )

        event_metadata["audio_sample_width"] = audio_evidence.get(
            "sample_width",
            2,
        )

        event_metadata["audio_buffer_duration_seconds"] = audio_evidence.get(
            "duration_seconds"
        )

        print(
            f"[ANOMALY] DETECTED "
            f"{event_type} "
            f"| voice_duration="
            f"{detected_duration:.2f}s"
        )

        try:
            evidence = self._capture_audio_evidence(
                event_type=event_type,
                audio_evidence=audio_evidence,
                event_metadata=event_metadata,
            )

        except Exception as error:
            print(
                f"[ANOMALY] Audio evidence capture "
                f"failed for "
                f"{event_type}: "
                f"{error}"
            )

            result = self._empty_result(
                event_type=event_type,
                active=True,
                confirmed=True,
                duration=detected_duration,
                required_duration=minimum_audio_duration,
                cooldown=cooldown,
                cooldown_remaining=0.0,
            )

            result["error"] = str(error)

            return result

        if evidence is None:
            return self._empty_result(
                event_type=event_type,
                active=True,
                confirmed=True,
                duration=detected_duration,
                required_duration=minimum_audio_duration,
                cooldown=cooldown,
                cooldown_remaining=0.0,
            )

        state["last_capture_at"] = now

        if capture_once:
            state["captured_in_incident"] = True

        api_violation = self._build_api_violation(
            event_type=event_type,
            evidence=evidence,
            event_metadata=event_metadata,
        )

        print(f"[ANOMALY] AUDIO EVIDENCE CAPTURED " f"{event_type}")

        result = {
            "event_type": event_type,
            "active": True,
            "confirmed": True,
            "captured": True,
            "duration": detected_duration,
            "required_duration": minimum_audio_duration,
            "cooldown": cooldown,
            "cooldown_remaining": 0.0,
            "evidence": evidence,
            "api_violation": api_violation,
        }

        if self.socket_client is not None:
            self._notify_socket(result)

        return result

    def get_cooldown_remaining(
        self,
        event_type,
    ):
        event_type = str(event_type).upper().strip()

        state = self.states.get(event_type)

        if state is None:
            return 0.0

        now = time.monotonic()

        cooldown = self.get_cooldown(event_type)

        return self._get_cooldown_remaining(
            state,
            now,
            cooldown,
        )

    def update_many(
        self,
        anomalies,
        frame,
        metadata=None,
        evidence_frames=None,
        evidence_regions=None,
    ):
        results = {}

        shared_metadata = dict(metadata or {})

        if not isinstance(
            anomalies,
            dict,
        ):
            return results

        for (
            event_type,
            active,
        ) in anomalies.items():

            event_metadata = {}

            possible_event_metadata = shared_metadata.get(event_type)

            if isinstance(
                possible_event_metadata,
                dict,
            ):
                event_metadata.update(possible_event_metadata)

            else:
                event_metadata.update(shared_metadata)

            normalized_event_type = str(event_type).upper().strip()

            event_evidence_frame = None

            if isinstance(
                evidence_frames,
                dict,
            ):
                event_evidence_frame = evidence_frames.get(normalized_event_type)

            event_evidence_regions = None

            if isinstance(
                evidence_regions,
                dict,
            ):
                event_evidence_regions = evidence_regions.get(normalized_event_type)

            results[normalized_event_type] = self.update(
                event_type=event_type,
                active=active,
                frame=frame,
                metadata=event_metadata,
                evidence_frame=event_evidence_frame,
                evidence_regions=event_evidence_regions,
            )

        return results

    def reset_event(
        self,
        event_type,
    ):
        event_type = str(event_type).upper().strip()

        state = self.states.get(event_type)

        if state is None:
            return

        self._reset_state(
            event_type,
            state,
        )

    def reset_all(
        self,
    ):
        for (
            event_type,
            state,
        ) in list(self.states.items()):
            self._reset_state(
                event_type,
                state,
            )

        self.states.clear()

        print("[ANOMALY] All anomaly states reset.")

    def get_state(
        self,
        event_type,
    ):
        event_type = str(event_type).upper().strip()

        state = self.states.get(event_type)

        if state is None:
            return {
                "started_at": None,
                "last_active_at": None,
                "last_capture_at": None,
                "confirmed": False,
                "captured_in_incident": False,
            }

        result = dict(state)

        if "captured_in_incident" not in result:
            result["captured_in_incident"] = False

        return result

    def get_all_states(
        self,
    ):
        return {event_type: self.get_state(event_type) for event_type in self.states}

    def close(
        self,
    ):
        self.reset_all()

        print("[ANOMALY] Manager closed.")
