import time

import cv2

try:
    from src.vision.object_detector_phone_gate import (
        YOLO26ObjectDetector,
    )
except ImportError:
    try:
        from src.vision.object_detector_yolo26 import (
            YOLO26ObjectDetector,
        )
    except ImportError:
        from src.vision.object_detector_yolo26 import (
            ObjectDetector as YOLO26ObjectDetector,
        )


from src.vision.phone_verification import (
    MobileNetPhoneVerifier,
)

CAMERA_INDEX = 0

DETECTION_INTERVAL_SECONDS = 0.15

PHONE_LABEL = "CELL_PHONE"
BOOK_LABEL = "BOOK"

CROP_PADDING_RATIO = 0.30

GATE_1_COLOR = (
    0,
    165,
    255,
)

GATE_2_COLOR = (
    0,
    200,
    0,
)

BOOK_COLOR = (
    255,
    120,
    0,
)

TEXT_COLOR = (
    255,
    255,
    255,
)

STATUS_BACKGROUND = (
    40,
    40,
    40,
)

GATE_2_INSET_PIXELS = 5


def crop_detection(
    frame,
    detection,
):
    frame_height, frame_width = frame.shape[:2]

    x1 = int(
        detection.get(
            "x",
            0,
        )
    )

    y1 = int(
        detection.get(
            "y",
            0,
        )
    )

    x2 = int(
        detection.get(
            "x2",
            x1,
        )
    )

    y2 = int(
        detection.get(
            "y2",
            y1,
        )
    )

    box_width = max(
        1,
        x2 - x1,
    )

    box_height = max(
        1,
        y2 - y1,
    )

    pad_x = int(round(box_width * CROP_PADDING_RATIO))

    pad_y = int(round(box_height * CROP_PADDING_RATIO))

    x1 = max(
        0,
        x1 - pad_x,
    )

    y1 = max(
        0,
        y1 - pad_y,
    )

    x2 = min(
        frame_width,
        x2 + pad_x,
    )

    y2 = min(
        frame_height,
        y2 + pad_y,
    )

    if x2 <= x1 or y2 <= y1:
        return None

    crop = frame[
        y1:y2,
        x1:x2,
    ]

    if crop.size == 0:
        return None

    return crop.copy()


def draw_label(
    frame,
    text,
    x,
    y,
    color,
    font_scale=0.50,
):
    x = max(
        0,
        int(x),
    )

    y = max(
        25,
        int(y),
    )

    (
        text_width,
        text_height,
    ), baseline = cv2.getTextSize(
        text,
        cv2.FONT_HERSHEY_SIMPLEX,
        font_scale,
        2,
    )

    box_x1 = x

    box_y1 = max(
        0,
        y - text_height - baseline - 10,
    )

    box_x2 = min(
        frame.shape[1] - 1,
        x + text_width + 12,
    )

    box_y2 = min(
        frame.shape[0] - 1,
        y,
    )

    cv2.rectangle(
        frame,
        (
            box_x1,
            box_y1,
        ),
        (
            box_x2,
            box_y2,
        ),
        color,
        -1,
    )

    cv2.putText(
        frame,
        text,
        (
            box_x1 + 6,
            box_y2 - 6,
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        font_scale,
        TEXT_COLOR,
        2,
        cv2.LINE_AA,
    )


def get_gate_2_result(
    verification,
):
    if not isinstance(
        verification,
        dict,
    ):
        return False

    if "is_phone" in verification:
        return bool(
            verification.get(
                "is_phone",
                False,
            )
        )

    phone_rank = int(
        verification.get(
            "phone_rank",
            1000,
        )
    )

    return phone_rank <= 5


def get_detection_source(
    detection,
):
    source = str(
        detection.get(
            "detection_source",
            "full_frame",
        )
    ).lower()

    is_partial = bool(
        detection.get(
            "is_partial_candidate",
            False,
        )
    )

    if source == "tile" or is_partial:
        return "PARTIAL / TILE"

    return "FULL FRAME"


def draw_gate_1_box(
    frame,
    detection,
):
    x1 = int(
        detection.get(
            "x",
            0,
        )
    )

    y1 = int(
        detection.get(
            "y",
            0,
        )
    )

    x2 = int(
        detection.get(
            "x2",
            x1,
        )
    )

    y2 = int(
        detection.get(
            "y2",
            y1,
        )
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
        GATE_1_COLOR,
        3,
    )

    source_text = get_detection_source(detection)

    label = f"GATE 1: PHONE CANDIDATE" f" [{source_text}]"

    draw_label(
        frame,
        label,
        x1,
        max(
            30,
            y1,
        ),
        GATE_1_COLOR,
        font_scale=0.48,
    )


def draw_gate_2_box(
    frame,
    detection,
):
    x1 = int(
        detection.get(
            "x",
            0,
        )
    )

    y1 = int(
        detection.get(
            "y",
            0,
        )
    )

    x2 = int(
        detection.get(
            "x2",
            x1,
        )
    )

    y2 = int(
        detection.get(
            "y2",
            y1,
        )
    )

    inset = GATE_2_INSET_PIXELS

    inner_x1 = min(
        x2,
        x1 + inset,
    )

    inner_y1 = min(
        y2,
        y1 + inset,
    )

    inner_x2 = max(
        inner_x1,
        x2 - inset,
    )

    inner_y2 = max(
        inner_y1,
        y2 - inset,
    )

    if inner_x2 <= inner_x1 or inner_y2 <= inner_y1:
        inner_x1 = x1
        inner_y1 = y1
        inner_x2 = x2
        inner_y2 = y2

    cv2.rectangle(
        frame,
        (
            inner_x1,
            inner_y1,
        ),
        (
            inner_x2,
            inner_y2,
        ),
        GATE_2_COLOR,
        3,
    )

    label_y = min(
        frame.shape[0] - 5,
        y2 + 28,
    )

    draw_label(
        frame,
        "GATE 2: PHONE CONFIRMED",
        x1,
        label_y,
        GATE_2_COLOR,
        font_scale=0.50,
    )


def draw_book_box(
    frame,
    detection,
):
    x1 = int(
        detection.get(
            "x",
            0,
        )
    )

    y1 = int(
        detection.get(
            "y",
            0,
        )
    )

    x2 = int(
        detection.get(
            "x2",
            x1,
        )
    )

    y2 = int(
        detection.get(
            "y2",
            y1,
        )
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
        BOOK_COLOR,
        2,
    )

    draw_label(
        frame,
        "BOOK",
        x1,
        max(
            30,
            y1,
        ),
        BOOK_COLOR,
        font_scale=0.50,
    )


def draw_top_status(
    frame,
    gate_1_count,
    gate_2_count,
):
    frame_width = frame.shape[1]

    cv2.rectangle(
        frame,
        (
            0,
            0,
        ),
        (
            frame_width,
            62,
        ),
        STATUS_BACKGROUND,
        -1,
    )

    if gate_2_count > 0:
        status_text = "PHONE CONFIRMED"

        status_color = (
            0,
            220,
            0,
        )

    elif gate_1_count > 0:
        status_text = "PHONE CANDIDATE - " "WAITING FOR GATE 2"

        status_color = (
            0,
            190,
            255,
        )

    else:
        status_text = "NO PHONE CANDIDATE"

        status_color = (
            220,
            220,
            220,
        )

    cv2.putText(
        frame,
        status_text,
        (
            15,
            28,
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.68,
        status_color,
        2,
        cv2.LINE_AA,
    )

    count_text = f"Gate 1: {gate_1_count}   " f"Gate 2 confirmed: " f"{gate_2_count}"

    cv2.putText(
        frame,
        count_text,
        (
            15,
            52,
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.48,
        TEXT_COLOR,
        1,
        cv2.LINE_AA,
    )


def main():
    print("[TEST] Loading Gate-1 " "YOLO detector...")

    detector = YOLO26ObjectDetector()

    print("[TEST] Loading " "Gate-2 MobileNet verifier...")

    verifier = MobileNetPhoneVerifier()

    print("[TEST] Opening camera...")

    camera = cv2.VideoCapture(
        CAMERA_INDEX,
        cv2.CAP_DSHOW,
    )

    if not camera.isOpened():
        camera.release()

        camera = cv2.VideoCapture(CAMERA_INDEX)

    if not camera.isOpened():
        detector.close()
        verifier.close()

        raise RuntimeError("Could not open camera.")

    camera.set(
        cv2.CAP_PROP_BUFFERSIZE,
        1,
    )

    print()
    print("======================================")

    print(" TWO-GATE PHONE VERIFICATION TEST")

    print("======================================")

    print()

    print("ORANGE = Gate 1 phone candidate")

    print("GREEN  = Gate 2 phone confirmed")

    print("BLUE   = book")

    print()

    print("No software mirroring is applied.")

    print("Press Q or ESC to quit.")

    print()

    last_detection_time = 0.0

    gate_1_results = []

    book_results = []

    try:
        while True:
            success, frame = camera.read()

            if not success or frame is None:
                continue

            #
            # IMPORTANT:
            #
            # DO NOT use:
            #
            #     cv2.flip(frame, 1)
            #
            # We intentionally preserve
            # the camera frame orientation.
            #

            current_time = time.monotonic()

            if current_time - last_detection_time >= DETECTION_INTERVAL_SECONDS:
                last_detection_time = current_time

                detections = detector.detect(frame)

                gate_1_results = []
                book_results = []

                for detection in detections:
                    label = detection.get("label")

                    if label == BOOK_LABEL:
                        book_results.append(detection.copy())

                        continue

                    if label != PHONE_LABEL:
                        continue

                    crop = crop_detection(
                        frame,
                        detection,
                    )

                    verification = {
                        "is_phone": False,
                        "phone_probability": 0.0,
                        "phone_rank": 1000,
                        "mode": "invalid",
                    }

                    if crop is not None:
                        try:
                            verification = verifier.classify_crop(crop)

                        except Exception as error:
                            print("[GATE 2 ERROR] " f"{error}")

                    gate_2_confirmed = get_gate_2_result(verification)

                    gate_1_results.append(
                        {
                            "detection": (detection.copy()),
                            "verification": (verification),
                            "gate_2_confirmed": (gate_2_confirmed),
                        }
                    )

                    source_text = get_detection_source(detection)

                    gate_2_text = "CONFIRMED" if gate_2_confirmed else "NOT CONFIRMED"

                    print(
                        "[PHONE TEST] "
                        f"GATE1={source_text} "
                        f"| GATE2={gate_2_text} "
                        f"| YOLO="
                        f"{float(detection.get('confidence', 0.0)):.3f} "
                        f"| rank="
                        f"{int(verification.get('phone_rank', 1000))} "
                        f"| mode="
                        f"{verification.get('mode', 'unknown')}"
                    )

            display_frame = frame.copy()

            for detection in book_results:
                draw_book_box(
                    display_frame,
                    detection,
                )

            gate_2_count = 0

            for item in gate_1_results:
                detection = item["detection"]

                gate_2_confirmed = bool(item["gate_2_confirmed"])

                #
                # Gate 1 is ALWAYS shown.
                #
                draw_gate_1_box(
                    display_frame,
                    detection,
                )

                #
                # Gate 2 is drawn as an
                # INNER/SUBSET box only
                # when MobileNet confirms.
                #
                if gate_2_confirmed:
                    gate_2_count += 1

                    draw_gate_2_box(
                        display_frame,
                        detection,
                    )

            draw_top_status(
                display_frame,
                gate_1_count=len(gate_1_results),
                gate_2_count=(gate_2_count),
            )

            cv2.imshow(
                "Two-Gate Phone Detection",
                display_frame,
            )

            key = cv2.waitKey(1) & 0xFF

            if key in (
                ord("q"),
                ord("Q"),
                27,
            ):
                break

    finally:
        camera.release()

        cv2.destroyAllWindows()

        detector.close()
        verifier.close()

        print("[TEST] Closed.")


if __name__ == "__main__":
    main()
