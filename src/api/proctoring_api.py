# import json
# import time
# from pathlib import Path

# import requests

# from src.config import settings


# class ProctoringAPI:

#     def __init__(
#         self,
#         token,
#     ):
#         self.token = str(token).strip()

#         self.base_url = str(settings.ASSESSMENT_API_BASE_URL).strip().rstrip("/")

#         self.endpoint = f"{self.base_url}" "/proctoring/violations"

#         self.api_cooldown = float(settings.PROCTORING_API_COOLDOWN_SECONDS)

#         self.last_successful_call_at = None

#     def _can_send(self):

#         if self.last_successful_call_at is None:
#             return True

#         elapsed = time.monotonic() - self.last_successful_call_at

#         return elapsed >= self.api_cooldown

#     def send_violations(
#         self,
#         violations,
#         evidence_files=None,
#     ):

#         if not violations:
#             return {
#                 "success": False,
#                 "sent": False,
#                 "reason": "NO_VIOLATIONS",
#             }

#         if not self.token:
#             return {
#                 "success": False,
#                 "sent": False,
#                 "reason": "NO_TOKEN",
#             }

#         if not self._can_send():
#             return {
#                 "success": False,
#                 "sent": False,
#                 "reason": "API_COOLDOWN",
#             }

#         evidence_files = evidence_files if evidence_files else []

#         files = []

#         opened_files = []

#         try:

#             for file_path in evidence_files:

#                 if not file_path:
#                     continue

#                 path = Path(file_path)

#                 if not path.exists():
#                     print(
#                         "[API] Evidence file does not exist:",
#                         path,
#                     )
#                     continue

#                 if not path.is_file():
#                     print(
#                         "[API] Evidence path is not a file:",
#                         path,
#                     )
#                     continue

#                 file_handle = open(
#                     path,
#                     "rb",
#                 )

#                 opened_files.append(file_handle)

#                 files.append(
#                     (
#                         "files",
#                         (
#                             path.name,
#                             file_handle,
#                             self._get_content_type(path),
#                         ),
#                     )
#                 )

#             serialized_violations = self._serialize_violations(violations)

#             print("[API] Sending violation batch...")

#             print(
#                 "[API] Endpoint:",
#                 self.endpoint,
#             )

#             print(
#                 "[API] Violation count:",
#                 len(violations),
#             )

#             print(
#                 "[API] Evidence file count:",
#                 len(files),
#             )

#             response = requests.post(
#                 self.endpoint,
#                 headers={
#                     "Authorization": (f"Bearer {self.token}"),
#                     "Accept": "application/json",
#                 },
#                 data={
#                     "violations": (serialized_violations),
#                 },
#                 files=files,
#                 timeout=15,
#             )

#             print(
#                 "[API] HTTP status:",
#                 response.status_code,
#             )

#             print(
#                 "[API] Response body:",
#                 response.text,
#             )

#             try:
#                 response_data = response.json()

#             except ValueError:
#                 response_data = {"message": response.text}

#             if 200 <= response.status_code < 300:

#                 self.last_successful_call_at = time.monotonic()

#                 return {
#                     "success": True,
#                     "sent": True,
#                     "status_code": (response.status_code),
#                     "response": response_data,
#                 }

#             return {
#                 "success": False,
#                 "sent": False,
#                 "status_code": (response.status_code),
#                 "response": response_data,
#             }

#         except requests.RequestException as error:

#             print(
#                 "[API] Network error:",
#                 error,
#             )

#             return {
#                 "success": False,
#                 "sent": False,
#                 "reason": "NETWORK_ERROR",
#                 "error": str(error),
#             }

#         except Exception as error:

#             print(
#                 "[API] Unexpected API error:",
#                 error,
#             )

#             return {
#                 "success": False,
#                 "sent": False,
#                 "reason": "API_ERROR",
#                 "error": str(error),
#             }

#         finally:

#             for file_handle in opened_files:

#                 try:
#                     file_handle.close()

#                 except Exception:
#                     pass

#     @staticmethod
#     def _get_content_type(
#         path,
#     ):

#         suffix = path.suffix.lower()

#         content_types = {
#             ".jpg": "image/jpeg",
#             ".jpeg": "image/jpeg",
#             ".png": "image/png",
#             ".webp": "image/webp",
#             ".gif": "image/gif",
#             ".wav": "audio/wav",
#             ".mp3": "audio/mpeg",
#             ".ogg": "audio/ogg",
#             ".webm": "audio/webm",
#             ".mp4": "video/mp4",
#             ".avi": "video/x-msvideo",
#             ".mov": "video/quicktime",
#         }

#         return content_types.get(
#             suffix,
#             "application/octet-stream",
#         )

#     @staticmethod
#     def _serialize_violations(
#         violations,
#     ):

#         normalized = []

#         for violation in violations:

#             if not isinstance(
#                 violation,
#                 dict,
#             ):
#                 continue

#             item = dict(violation)

#             normalized.append(item)

#         return json.dumps(
#             normalized,
#             ensure_ascii=False,
#         )


import json
import time

from pathlib import Path

import requests

from src.config import settings


class ProctoringAPI:

    def __init__(
        self,
        token,
    ):
        self.token = str(token).strip()

        self.base_url = str(settings.ASSESSMENT_API_BASE_URL).strip().rstrip("/")

        self.endpoint = f"{self.base_url}" "/proctoring/violations"

        self.api_cooldown = float(settings.PROCTORING_API_COOLDOWN_SECONDS)

        self.last_successful_call_at = None

    def _can_send(self):

        if self.last_successful_call_at is None:
            return True

        elapsed = time.monotonic() - self.last_successful_call_at

        return elapsed >= self.api_cooldown

    def send_violations(
        self,
        violations,
        evidence_files=None,
    ):

        if not violations:
            return {
                "success": False,
                "sent": False,
                "reason": "NO_VIOLATIONS",
            }

        if not self.token:
            return {
                "success": False,
                "sent": False,
                "reason": "NO_TOKEN",
            }

        if not self._can_send():
            return {
                "success": False,
                "sent": False,
                "reason": "API_COOLDOWN",
            }

        evidence_files = evidence_files if evidence_files else []

        files = []
        opened_files = []

        try:

            (
                normalized_violations,
                upload_files,
            ) = self._prepare_payload(
                violations=violations,
                evidence_files=evidence_files,
            )

            for file_index, file_path in enumerate(upload_files):

                if not file_path:
                    continue

                path = Path(file_path)

                if not path.exists():

                    print(
                        "[API] Evidence file does not exist:",
                        path,
                    )

                    continue

                if not path.is_file():

                    print(
                        "[API] Evidence path is not a file:",
                        path,
                    )

                    continue

                file_handle = open(
                    path,
                    "rb",
                )

                opened_files.append(file_handle)

                files.append(
                    (
                        "files",
                        (
                            path.name,
                            file_handle,
                            self._get_content_type(path),
                        ),
                    )
                )

                print(
                    "[API] Evidence prepared:",
                    {
                        "file_index": file_index,
                        "path": str(path),
                    },
                )

            serialized_violations = self._serialize_violations(normalized_violations)

            print("[API] Sending violation batch...")

            print(
                "[API] Endpoint:",
                self.endpoint,
            )

            print(
                "[API] Violation count:",
                len(normalized_violations),
            )

            print(
                "[API] Evidence file count:",
                len(files),
            )

            print(
                "[API] Violation payload:",
                json.dumps(
                    normalized_violations,
                    ensure_ascii=False,
                    default=str,
                ),
            )

            response = requests.post(
                self.endpoint,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Accept": "application/json",
                },
                data={
                    "violations": serialized_violations,
                },
                files=files,
                timeout=15,
            )

            print(
                "[API] HTTP status:",
                response.status_code,
            )

            print(
                "[API] Response body:",
                response.text,
            )

            try:

                response_data = response.json()

            except ValueError:

                response_data = {"message": response.text}

            if 200 <= response.status_code < 300:

                self.last_successful_call_at = time.monotonic()

                return {
                    "success": True,
                    "sent": True,
                    "status_code": response.status_code,
                    "response": response_data,
                }

            return {
                "success": False,
                "sent": False,
                "status_code": response.status_code,
                "response": response_data,
            }

        except requests.RequestException as error:

            print(
                "[API] Network error:",
                error,
            )

            return {
                "success": False,
                "sent": False,
                "reason": "NETWORK_ERROR",
                "error": str(error),
            }

        except Exception as error:

            print(
                "[API] Unexpected API error:",
                error,
            )

            return {
                "success": False,
                "sent": False,
                "reason": "API_ERROR",
                "error": str(error),
            }

        finally:

            for file_handle in opened_files:

                try:
                    file_handle.close()

                except Exception:
                    pass

    @staticmethod
    def _prepare_payload(
        violations,
        evidence_files,
    ):

        normalized = []

        upload_files = []

        path_to_index = {}

        def register_file(
            file_path,
        ):

            if not file_path:
                return None

            path = Path(file_path)

            try:
                normalized_path = str(path.resolve())

            except Exception:
                normalized_path = str(path)

            if normalized_path in path_to_index:
                return path_to_index[normalized_path]

            file_index = len(upload_files)

            upload_files.append(str(path))

            path_to_index[normalized_path] = file_index

            return file_index

        for violation in violations:

            if not isinstance(
                violation,
                dict,
            ):
                continue

            item = dict(violation)

            local_file_path = (
                item.pop(
                    "file_path",
                    None,
                )
                or item.pop(
                    "evidence_file",
                    None,
                )
                or item.pop(
                    "evidence_path",
                    None,
                )
            )

            if local_file_path:

                file_index = register_file(local_file_path)

                if file_index is not None:
                    item["file_index"] = file_index

            normalized.append(item)

        mapped_evidence_files = []

        legacy_evidence_files = []

        for evidence_item in evidence_files or []:

            violation_index = None
            file_path = None

            if isinstance(
                evidence_item,
                dict,
            ):

                file_path = (
                    evidence_item.get("path")
                    or evidence_item.get("file_path")
                    or evidence_item.get("evidence_file")
                )

                raw_violation_index = evidence_item.get("violation_index")

                if raw_violation_index is not None:
                    try:

                        violation_index = int(raw_violation_index)

                    except (
                        TypeError,
                        ValueError,
                    ):
                        violation_index = None

            elif (
                isinstance(
                    evidence_item,
                    (
                        list,
                        tuple,
                    ),
                )
                and len(evidence_item) >= 2
            ):

                try:

                    violation_index = int(evidence_item[0])

                    file_path = evidence_item[1]

                except (
                    TypeError,
                    ValueError,
                ):

                    file_path = evidence_item[0]

                    try:

                        violation_index = int(evidence_item[1])

                    except (
                        TypeError,
                        ValueError,
                    ):
                        violation_index = None

            else:

                file_path = evidence_item

            if not file_path:
                continue

            if violation_index is not None:

                mapped_evidence_files.append(
                    {
                        "violation_index": violation_index,
                        "file_path": file_path,
                    }
                )

            else:

                legacy_evidence_files.append(file_path)

        for mapped_item in mapped_evidence_files:

            violation_index = mapped_item["violation_index"]

            if violation_index < 0 or violation_index >= len(normalized):

                print(
                    "[API] Invalid mapped evidence violation index:",
                    violation_index,
                )

                continue

            file_index = register_file(mapped_item["file_path"])

            if file_index is not None:

                normalized[violation_index]["file_index"] = file_index

        if legacy_evidence_files:

            violations_without_files = [
                index
                for index, item in enumerate(normalized)
                if item.get("file_index") is None
            ]

            if len(legacy_evidence_files) == len(normalized):

                for violation_index, file_path in enumerate(legacy_evidence_files):

                    if normalized[violation_index].get("file_index") is not None:
                        continue

                    file_index = register_file(file_path)

                    if file_index is not None:

                        normalized[violation_index]["file_index"] = file_index

            elif len(legacy_evidence_files) == len(violations_without_files):

                for violation_index, file_path in zip(
                    violations_without_files,
                    legacy_evidence_files,
                ):

                    file_index = register_file(file_path)

                    if file_index is not None:

                        normalized[violation_index]["file_index"] = file_index

            else:

                print(
                    "[API] WARNING: Legacy evidence file mapping "
                    "is ambiguous. Mapping available files in order."
                )

                for violation_index, file_path in zip(
                    violations_without_files,
                    legacy_evidence_files,
                ):

                    file_index = register_file(file_path)

                    if file_index is not None:

                        normalized[violation_index]["file_index"] = file_index

        for index, violation in enumerate(normalized):

            print(
                "[API] Violation mapping:",
                {
                    "violation_index": index,
                    "violation_type": violation.get("violation_type")
                    or violation.get("event_type"),
                    "file_index": violation.get("file_index"),
                },
            )

        return (
            normalized,
            upload_files,
        )

    @staticmethod
    def _get_content_type(
        path,
    ):

        suffix = path.suffix.lower()

        content_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".gif": "image/gif",
            ".wav": "audio/wav",
            ".mp3": "audio/mpeg",
            ".ogg": "audio/ogg",
            ".webm": "audio/webm",
            ".mp4": "video/mp4",
            ".avi": "video/x-msvideo",
            ".mov": "video/quicktime",
        }

        return content_types.get(
            suffix,
            "application/octet-stream",
        )

    @staticmethod
    def _serialize_violations(
        violations,
    ):

        normalized = []

        for violation in violations:

            if not isinstance(
                violation,
                dict,
            ):
                continue

            item = dict(violation)

            normalized.append(item)

        return json.dumps(
            normalized,
            ensure_ascii=False,
            default=str,
        )
