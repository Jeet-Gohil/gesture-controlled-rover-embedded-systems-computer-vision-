from pathlib import Path
import time
import cv2
import serial
import serial.tools.list_ports
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions, vision

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),          # thumb
    (0, 5), (5, 6), (6, 7), (7, 8),          # index
    (5, 9), (9, 10), (10, 11), (11, 12),     # middle
    (9, 13), (13, 14), (14, 15), (15, 16),   # ring
    (13, 17), (17, 18), (18, 19), (19, 20),  # pinky
    (0, 17),                                  # palm edge
]


def draw_hand(frame, landmarks, label):
    h, w = frame.shape[:2]
    pts = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]

    # skeleton lines
    for a, b in HAND_CONNECTIONS:
        cv2.line(frame, pts[a], pts[b], (0, 255, 0), 2)
    # joints
    for p in pts:
        cv2.circle(frame, p, 4, (0, 0, 255), -1)

    # bounding box with padding
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    pad = 20
    x1, y1 = max(min(xs) - pad, 0), max(min(ys) - pad, 0)
    x2, y2 = min(max(xs) + pad, w - 1), min(max(ys) + pad, h - 1)
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
    cv2.putText(frame, label, (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

# ---------------- Settings ----------------
PORT = "COM4"              # None = auto-detect the Arduino; or set manually, e.g. "COM3"
BAUD = 9600
SEND_INTERVAL = 0.1      # seconds (10 Hz). Must be well below the Arduino TIMEOUT_MS (500 ms)
STABLE_FRAMES = 3        # a gesture must be seen this many frames in a row before it is used
MIN_SCORE = 0.5
# ------------------------------------------

GESTURE_TO_COMMAND = {
    "open_palm": "forward",
    "closed_fist": "reverse",
    "thumb_up": "stop",
    "thumbs_up": "stop",
    "pointing_up": "left",
    "victory": "right",
}
COMMAND_TO_CHAR = {"forward": "F", "reverse": "B", "left": "L", "right": "R", "stop": "S"}


def find_arduino_port():
    ports = list(serial.tools.list_ports.comports())
    print("Ports found:")
    for p in ports:
        print(f"  {p.device} - {p.description}")
    for p in ports:
        desc = (p.description or "").lower()
        if "arduino" in desc or "ch340" in desc or "usb serial" in desc or "usb-serial" in desc:
            return p.device
    return None


port = PORT or find_arduino_port()
if port is None:
    raise SystemExit("Arduino not found. Plug in the USB cable, or set PORT manually (e.g. 'COM3').")

try:
    ser = serial.Serial(port, BAUD, timeout=0.01)
except serial.SerialException as e:
    raise SystemExit(
        f"Could not open {port}: {e}\n"
        "Close the Arduino Serial Monitor / Serial Plotter and any other Python run, then try again."
    )
time.sleep(2)  # Uno resets when the port opens; wait for it to boot
print(f"Serial open on {port}")

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
print("Camera open:", cap.isOpened())

options = vision.GestureRecognizerOptions(
    base_options=BaseOptions(model_asset_path=str(Path(__file__).parent / "gesture_recognizer.task")),
    running_mode=vision.RunningMode.VIDEO,
    num_hands=1,
)
recognizer = vision.GestureRecognizer.create_from_options(options)

last_command = None
active_command = "stop"
pending = "stop"
pending_count = 0
last_sent = 0.0

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = recognizer.recognize_for_video(mp_image, int(time.monotonic() * 1000))

        candidate = "stop"
        if result.gestures:
            top = result.gestures[0][0]
            if top.score >= MIN_SCORE:
                candidate = GESTURE_TO_COMMAND.get(top.category_name.lower(), "stop")
           # draw_hand(frame, result.gesture[0])   
        if result.hand_landmarks:
            label = ""
            if result.gestures:
                top = result.gestures[0][0]
                label = f"{top.category_name} {top.score:.2f}"
            draw_hand(frame, result.hand_landmarks[0], label)  

        # Debounce
        if candidate == pending:
            pending_count += 1
        else:
            pending = candidate
            pending_count = 1
        if pending_count >= STABLE_FRAMES:
            active_command = pending

        # Send continuously so the Arduino timeout doesn't stop the robot
        now = time.monotonic()
        if now - last_sent >= SEND_INTERVAL:
            ser.write(COMMAND_TO_CHAR[active_command].encode())
            last_sent = now

        if active_command != last_command:
            print(active_command)
            last_command = active_command

        cv2.putText(frame, active_command, (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 2)
        cv2.imshow("live gesture", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
finally:
    try:
        ser.write(b"S")
        ser.close()
    except Exception:
        pass
    cap.release()
    recognizer.close()
    cv2.destroyAllWindows()