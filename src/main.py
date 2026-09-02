import argparse
import sys
import time

from urllib.parse import (
    parse_qs,
    quote,
    urlparse,
)

from src.auth import (
    LaunchTokenError,
    validate_launch_token,
)

from src.config import settings

from src.core.kiosk_manager import (
    KioskManager,
)

from src.core.keyboard_lockdown import (
    KeyboardLockdownManager,
)

from src.socket.proctor_socket import (
    ProctorSocketClient,
)

PROTOCOL_SCHEME = "skolariq-proctor"

LAUNCH_ACTION = "launch"

DEFAULT_ASSESSMENT_WEB_BASE_URL = "http://localhost:5173"


exam_completed_flag = False


def extract_token_from_url(
    launch_url,
):

    try:

        parsed = urlparse(launch_url)

    except Exception:

        raise ValueError("Invalid proctor launch URL.")

    if parsed.scheme != PROTOCOL_SCHEME:

        raise ValueError("Invalid proctor protocol.")

    if parsed.netloc != LAUNCH_ACTION:

        raise ValueError("Invalid proctor launch action.")

    query = parse_qs(parsed.query)

    tokens = query.get("token")

    if not tokens:

        raise ValueError("Launch token is missing.")

    token = tokens[0].strip()

    if not token:

        raise ValueError("Launch token is empty.")

    return token


def get_launch_token():

    parser = argparse.ArgumentParser(prog="Skolariq Proctor")

    parser.add_argument(
        "launch_url",
        nargs="?",
    )

    parser.add_argument(
        "--token",
        required=False,
    )

    args = parser.parse_args()

    if args.token:

        return args.token.strip()

    if args.launch_url:

        try:

            return extract_token_from_url(args.launch_url)

        except ValueError as error:

            print(f"Launch rejected: {error}")

            sys.exit(1)

    print("Launch rejected: No launch token provided.")

    sys.exit(1)


def get_assessment_web_base_url():

    configured_url = getattr(
        settings,
        "ASSESSMENT_WEB_BASE_URL",
        None,
    )

    if configured_url:

        return str(configured_url).strip().rstrip("/")

    return DEFAULT_ASSESSMENT_WEB_BASE_URL


def get_socket_server_url():

    configured_url = getattr(
        settings,
        "SOCKET_SERVER_URL",
        None,
    )

    if configured_url:

        return str(configured_url).strip().rstrip("/")

    return get_assessment_web_base_url()


def build_bootstrap_url(
    token,
):

    base_url = get_assessment_web_base_url()

    encoded_token = quote(token, safe="")

    return f"{base_url}" "/student/proctor/bootstrap" f"?token={encoded_token}"


def start_kiosk(
    token,
):

    bootstrap_url = build_bootstrap_url(token)

    print()

    print("[PROCTOR] Starting secure kiosk...")

    print("[PROCTOR] Bootstrap URL prepared.")

    kiosk = KioskManager()

    try:

        process = kiosk.start(bootstrap_url)

    except Exception as error:

        print("[PROCTOR] Kiosk launch failed.")

        print(f"[PROCTOR] Reason: {error}")

        sys.exit(1)

    print("[PROCTOR] Kiosk started successfully.")

    return (
        kiosk,
        process,
    )


def start_keyboard_lockdown():

    app_environment = str(
        getattr(
            settings,
            "APP_ENV",
            "development",
        )
    ).lower()

    allow_development_escape = app_environment != "production"

    lockdown = KeyboardLockdownManager(
        allow_development_escape=allow_development_escape
    )

    lockdown.start()

    return lockdown


def start_proctor_socket(
    session,
):

    try:

        socket_client = ProctorSocketClient(
            server_url=get_socket_server_url(),
            token=session.get("raw_token"),
            proctor_session_id=session["proctor_session_id"],
            test_id=session["test_id"],
            schedule_id=session["schedule_id"],
        )

        def exam_completed(data):

            global exam_completed_flag

            print()

            print("[PROCTOR] Exam completion received.")

            print("[PROCTOR]", data)

            exam_completed_flag = True

        socket_client.exam_completed_callback = exam_completed

        socket_client.start_background()

        return socket_client

    except Exception as error:

        print("[PROCTOR] Socket startup failed:", error)

        return None


def run_proctor_session(
    kiosk,
    keyboard_lockdown,
):

    print()

    print("[PROCTOR] Proctoring session active.")

    try:

        while True:

            if exam_completed_flag:

                print()

                print("[PROCTOR] Exam completed. Closing session.")

                break

            if keyboard_lockdown.emergency_unlock_requested:

                print()

                print("[PROCTOR] Development emergency stop requested.")

                break

            time.sleep(0.5)

    except KeyboardInterrupt:

        print()

        print("[PROCTOR] Development stop requested.")

    finally:

        try:

            keyboard_lockdown.stop()

        except Exception as error:

            print("[PROCTOR] Keyboard unlock error:", error)

        try:

            kiosk.stop()

        except Exception as error:

            print("[PROCTOR] Kiosk stop error:", error)


def main():

    token = get_launch_token()

    try:

        session = validate_launch_token(token)

    except LaunchTokenError as error:

        print(f"Launch rejected: {error}")

        sys.exit(1)

    session = session.model_dump()

    session["raw_token"] = token

    print()

    print("[PROCTOR] Launch token validated.")

    print("[PROCTOR] Session:", session)

    kiosk = None

    keyboard_lockdown = None

    socket_client = None

    try:

        kiosk, _ = start_kiosk(token)

        socket_client = start_proctor_socket(session)

        keyboard_lockdown = start_keyboard_lockdown()

        run_proctor_session(kiosk, keyboard_lockdown)

    except Exception as error:

        print()

        print("[PROCTOR] Startup failed.")

        print(f"[PROCTOR] Reason: {error}")

    finally:

        if socket_client:

            try:

                socket_client.disconnect()

            except Exception:

                pass


if __name__ == "__main__":

    main()
