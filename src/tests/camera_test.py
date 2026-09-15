import cv2
import time


def test_camera(camera_index=0, backend=None):
    print("=" * 60)
    print("SKOLARIQ CAMERA TEST")
    print("=" * 60)

    backend_name = "DEFAULT"

    if backend == cv2.CAP_DSHOW:
        backend_name = "DIRECTSHOW"
    elif backend == cv2.CAP_MSMF:
        backend_name = "MSMF"

    print(f"[CAMERA] Index: {camera_index}")
    print(f"[CAMERA] Backend: {backend_name}")
    print("[CAMERA] Opening camera...")

    if backend is None:
        cap = cv2.VideoCapture(camera_index)
    else:
        cap = cv2.VideoCapture(camera_index, backend)

    if not cap.isOpened():
        print("[CAMERA] ❌ Camera could not be opened.")
        return False

    print("[CAMERA] ✅ Camera opened successfully.")

    # Give Windows camera driver a moment to initialize.
    time.sleep(1)

    # Try to configure a normal webcam resolution.
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    actual_width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    actual_height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)

    print(f"[CAMERA] Resolution: " f"{int(actual_width)}x{int(actual_height)}")

    print("[CAMERA] Reading frames...")
    print("[CAMERA] Press Q to close the test.")

    successful_frames = 0
    failed_frames = 0

    while True:
        ret, frame = cap.read()

        if not ret or frame is None:
            failed_frames += 1

            print(f"[CAMERA] ❌ Failed to read frame " f"(failure #{failed_frames})")

            # Don't hammer the camera driver continuously.
            time.sleep(0.1)

            if failed_frames >= 20:
                print("[CAMERA] ❌ Too many frame failures. " "Stopping test.")
                break

            continue

        successful_frames += 1

        if successful_frames == 1:
            print("[CAMERA] ✅ First frame received successfully.")

        # Display the raw camera feed.
        cv2.imshow("Skolariq Camera Test", frame)

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q") or key == ord("Q"):
            print("[CAMERA] Q pressed. Closing camera.")
            break

    cap.release()
    cv2.destroyAllWindows()

    print()
    print("=" * 60)
    print("CAMERA TEST RESULT")
    print("=" * 60)
    print(f"Successful frames : {successful_frames}")
    print(f"Failed frames     : {failed_frames}")

    if successful_frames > 0:
        print("[RESULT] ✅ OpenCV successfully received camera frames.")
    else:
        print("[RESULT] ❌ OpenCV could not receive any camera frames.")

    print("=" * 60)

    return successful_frames > 0


if __name__ == "__main__":

    print()
    print("Testing default OpenCV camera backend...")
    print()

    success = test_camera(
        camera_index=0,
        backend=None,
    )

    if success:
        print()
        print("[TEST] Default backend works.")
    else:
        print()
        print("[TEST] Default backend failed.")
        print()
        print("Now try DirectShow...")
        print()

        test_camera(
            camera_index=0,
            backend=cv2.CAP_DSHOW,
        )
