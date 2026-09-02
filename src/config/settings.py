import os

from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(dotenv_path=ENV_FILE)


DEFAULT_ASSESSMENT_WEB_BASE_URL = "http://localhost:5173"

DEFAULT_SOCKET_SERVER_URL = "http://localhost:4000"


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

        raise RuntimeError(f"Required environment variable '{key}' is missing.")

    return value


def normalize_public_key(
    value,
):

    if not value:

        return value

    return value.replace(
        "\\n",
        "\n",
    )


def normalize_base_url(
    value,
):

    if not value:

        return value

    return str(value).strip().rstrip("/")


class Settings:

    APP_ENV = get_env(
        "APP_ENV",
        "development",
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


settings = Settings()
