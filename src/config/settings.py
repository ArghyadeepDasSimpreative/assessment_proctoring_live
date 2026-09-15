import os
import sys

from pathlib import Path

from dotenv import load_dotenv

DEFAULT_ASSESSMENT_WEB_BASE_URL = "http://localhost:5173"
DEFAULT_SOCKET_SERVER_URL = "http://localhost:4000"


def get_application_directory():
    """
    Returns the directory containing the executable when running
    as a PyInstaller application.

    During development, returns the project root.
    """

    if getattr(
        sys,
        "frozen",
        False,
    ):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parents[2]


def get_project_root():
    """
    Development project root.

    Kept separately so the existing development setup continues
    to work exactly as before.
    """

    if getattr(
        sys,
        "frozen",
        False,
    ):
        return get_application_directory()

    return Path(__file__).resolve().parents[2]


PROJECT_ROOT = get_project_root()

APPLICATION_DIR = get_application_directory()


def get_env_candidates():
    """
    Search for .env in multiple locations.

    Development:
        project/.env

    Installed application:
        C:/Program Files/Skolariq Proctor/.env

    PyInstaller bundled data:
        sys._MEIPASS/.env
    """

    candidates = []

    # Installed EXE location
    candidates.append(APPLICATION_DIR / ".env")

    # Normal development location
    candidates.append(PROJECT_ROOT / ".env")

    # Current working directory
    candidates.append(Path.cwd() / ".env")

    # PyInstaller bundled resource directory
    if hasattr(
        sys,
        "_MEIPASS",
    ):
        candidates.append(Path(sys._MEIPASS) / ".env")

    # Remove duplicate paths while preserving order
    unique_candidates = []

    seen = set()

    for candidate in candidates:

        try:
            normalized = str(candidate.resolve())

        except Exception:
            normalized = str(candidate)

        if normalized in seen:
            continue

        seen.add(normalized)

        unique_candidates.append(candidate)

    return unique_candidates


ENV_FILE = None


for env_candidate in get_env_candidates():

    if not env_candidate.is_file():
        continue

    load_dotenv(
        dotenv_path=env_candidate,
        override=False,
    )

    ENV_FILE = env_candidate

    break


if ENV_FILE:

    print(
        "[CONFIG] Environment loaded from:",
        ENV_FILE,
    )

else:

    print("[CONFIG] WARNING: .env file was not found.")

    print("[CONFIG] Searched:")

    for candidate in get_env_candidates():
        print(
            "[CONFIG]  -",
            candidate,
        )


def get_env(
    key,
    default=None,
    required=False,
):

    value = os.getenv(
        key,
        default,
    )

    if required and (value is None or str(value).strip() == ""):
        raise RuntimeError(f"Required environment variable " f"'{key}' is missing.")

    return value


def normalize_public_key(
    value,
):

    if not value:
        return value

    return str(value).replace(
        "\\n",
        "\n",
    )


def normalize_base_url(
    value,
):

    if not value:
        return value

    return str(value).strip().rstrip("/")


def parse_bool(
    value,
    default=False,
):

    if value is None:
        return default

    return str(value).strip().lower() in (
        "true",
        "1",
        "yes",
        "y",
        "on",
    )


def parse_float(
    value,
    default=0.0,
):

    if value is None:
        return float(default)

    try:

        parsed = float(str(value).strip())

        if parsed < 0:
            return float(default)

        return parsed

    except (
        TypeError,
        ValueError,
    ):

        return float(default)


class Settings:

    APP_ENV = get_env(
        "APP_ENV",
        "development",
    )

    PROCTOR_KIOSK_ENABLED = parse_bool(
        get_env(
            "PROCTOR_KIOSK_ENABLED",
            "true",
        ),
        default=True,
    )

    ASSESSMENT_API_BASE_URL = normalize_base_url(
        get_env(
            "ASSESSMENT_API_BASE_URL",
            required=True,
        )
    )

    ASSESSMENT_WEB_BASE_URL = normalize_base_url(
        get_env(
            "ASSESSMENT_WEB_BASE_URL",
            DEFAULT_ASSESSMENT_WEB_BASE_URL,
        )
    )

    SOCKET_SERVER_URL = normalize_base_url(
        get_env(
            "SOCKET_SERVER_URL",
            DEFAULT_SOCKET_SERVER_URL,
        )
    )

    PROCTOR_JWT_PUBLIC_KEY = normalize_public_key(
        get_env(
            "PROCTOR_JWT_PUBLIC_KEY",
            required=True,
        )
    )

    PROCTOR_JWT_ALGORITHM = get_env(
        "PROCTOR_JWT_ALGORITHM",
        "RS256",
    )

    PROCTOR_JWT_AUDIENCE = get_env(
        "PROCTOR_JWT_AUDIENCE",
        "proctor-client",
    )

    PROCTOR_JWT_ISSUER = get_env(
        "PROCTOR_JWT_ISSUER",
        "assessment-api",
    )

    EVIDENCE_COOLDOWN_NO_FACE = parse_float(
        get_env(
            "EVIDENCE_COOLDOWN_NO_FACE",
            "10",
        ),
        default=10.0,
    )

    EVIDENCE_COOLDOWN_MULTIPLE_FACES = parse_float(
        get_env(
            "EVIDENCE_COOLDOWN_MULTIPLE_FACES",
            "8",
        ),
        default=8.0,
    )

    EVIDENCE_COOLDOWN_GAZE_AWAY = parse_float(
        get_env(
            "EVIDENCE_COOLDOWN_GAZE_AWAY",
            "15",
        ),
        default=15.0,
    )

    EVIDENCE_COOLDOWN_HEAD_AWAY = parse_float(
        get_env(
            "EVIDENCE_COOLDOWN_HEAD_AWAY",
            "15",
        ),
        default=15.0,
    )

    EVIDENCE_COOLDOWN_PHONE_DETECTED = parse_float(
        get_env(
            "EVIDENCE_COOLDOWN_PHONE_DETECTED",
            "10",
        ),
        default=10.0,
    )

    EVIDENCE_COOLDOWN_BOOK_DETECTED = parse_float(
        get_env(
            "EVIDENCE_COOLDOWN_BOOK_DETECTED",
            "10",
        ),
        default=10.0,
    )

    EVIDENCE_COOLDOWN_EXTRA_PERSON = parse_float(
        get_env(
            "EVIDENCE_COOLDOWN_EXTRA_PERSON",
            "8",
        ),
        default=8.0,
    )

    EVIDENCE_COOLDOWN_BODY_LEAN_LEFT = parse_float(
        get_env(
            "EVIDENCE_COOLDOWN_BODY_LEAN_LEFT",
            "15",
        ),
        default=15.0,
    )

    EVIDENCE_COOLDOWN_BODY_LEAN_RIGHT = parse_float(
        get_env(
            "EVIDENCE_COOLDOWN_BODY_LEAN_RIGHT",
            "15",
        ),
        default=15.0,
    )

    EVIDENCE_COOLDOWN_LEFT_ARM_RAISED = parse_float(
        get_env(
            "EVIDENCE_COOLDOWN_LEFT_ARM_RAISED",
            "15",
        ),
        default=15.0,
    )

    EVIDENCE_COOLDOWN_RIGHT_ARM_RAISED = parse_float(
        get_env(
            "EVIDENCE_COOLDOWN_RIGHT_ARM_RAISED",
            "15",
        ),
        default=15.0,
    )

    EVIDENCE_COOLDOWN_UNUSUAL_ARM_MOVEMENT = parse_float(
        get_env(
            "EVIDENCE_COOLDOWN_UNUSUAL_ARM_MOVEMENT",
            "15",
        ),
        default=15.0,
    )

    EVIDENCE_COOLDOWN_UPPER_BODY_NOT_VISIBLE = parse_float(
        get_env(
            "EVIDENCE_COOLDOWN_UPPER_BODY_NOT_VISIBLE",
            "15",
        ),
        default=15.0,
    )

    EVIDENCE_COOLDOWN_CAMERA_OFF = parse_float(
        get_env(
            "EVIDENCE_COOLDOWN_CAMERA_OFF",
            "5",
        ),
        default=5.0,
    )

    EVIDENCE_COOLDOWN_MIC_OFF = parse_float(
        get_env(
            "EVIDENCE_COOLDOWN_MIC_OFF",
            "5",
        ),
        default=5.0,
    )

    EVIDENCE_COOLDOWN_CAMERA_ERROR = parse_float(
        get_env(
            "EVIDENCE_COOLDOWN_CAMERA_ERROR",
            "5",
        ),
        default=5.0,
    )

    EVIDENCE_COOLDOWN_MIC_ERROR = parse_float(
        get_env(
            "EVIDENCE_COOLDOWN_MIC_ERROR",
            "5",
        ),
        default=5.0,
    )

    PROCTORING_API_COOLDOWN_SECONDS = parse_float(
        get_env(
            "PROCTORING_API_COOLDOWN_SECONDS",
            "5",
        ),
        default=5.0,
    )


settings = Settings()
