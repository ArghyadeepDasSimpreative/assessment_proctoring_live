import jwt

from pydantic import ValidationError

from src.config import settings
from src.schemas.proctor_session import ProctorSessionClaims


class LaunchTokenError(Exception):
    pass


def validate_launch_token(
    token: str,
) -> ProctorSessionClaims:
    if not token:
        raise LaunchTokenError("Launch token is missing.")

    token = token.strip()

    if not token:
        raise LaunchTokenError("Launch token is empty.")

    try:
        payload = jwt.decode(
            token,
            settings.PROCTOR_JWT_PUBLIC_KEY,
            algorithms=[settings.PROCTOR_JWT_ALGORITHM],
            audience=(settings.PROCTOR_JWT_AUDIENCE),
            issuer=(settings.PROCTOR_JWT_ISSUER),
            options={
                "require": [
                    "user_id",
                    "test_id",
                    "schedule_id",
                    "proctor_session_id",
                    "iss",
                    "aud",
                    "iat",
                    "exp",
                ]
            },
        )

    except jwt.ExpiredSignatureError:
        raise LaunchTokenError("Launch token has expired.")

    except jwt.InvalidAudienceError:
        raise LaunchTokenError("Launch token has an invalid audience.")

    except jwt.InvalidIssuerError:
        raise LaunchTokenError("Launch token has an invalid issuer.")

    except jwt.InvalidSignatureError:
        raise LaunchTokenError("Launch token signature is invalid.")

    except jwt.ImmatureSignatureError:
        raise LaunchTokenError("Launch token is not active yet.")

    except jwt.MissingRequiredClaimError as error:
        raise LaunchTokenError(f"Required JWT claim is missing: {error.claim}")

    except jwt.InvalidTokenError as error:
        raise LaunchTokenError(f"Invalid launch token: {error}")

    try:
        session = ProctorSessionClaims.model_validate(payload)

    except ValidationError as error:
        raise LaunchTokenError(
            "Launch token payload does not match " f"the required schema:\n{error}"
        )

    if session.iss != settings.PROCTOR_JWT_ISSUER:
        raise LaunchTokenError("Invalid token issuer.")

    if session.aud != settings.PROCTOR_JWT_AUDIENCE:
        raise LaunchTokenError("Invalid token audience.")

    return session
