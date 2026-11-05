# Gesture-Controlled Rover

A real-time computer vision and embedded robotics project. Hand gestures are captured via a laptop webcam, classified in real time using Google MediaPipe Tasks, converted into directional commands, and transmitted wirelessly over Bluetooth (or USB serial) to an Arduino Uno driving an L298N dual-motor rover chassis.

---

## Table of Contents
- [What It Does](#what-it-does)
- [System Architecture](#system-architecture)
- [Gesture to Command Mapping](#gesture-to-command-mapping)
- [Hardware Setup & Wiring](#hardware-setup--wiring)
- [Project Layout](#project-layout)
- [Software Installation](#software-installation)
- [Running the System](#running-the-system)
- [Safety & Fail-Safe Mechanisms](#safety--fail-safe-mechanisms)
- [Arduino Firmware (Reference Sketch)](#arduino-firmware-reference-sketch)
- [Roadmap & Upcoming Features](#roadmap--upcoming-features)
- [Troubleshooting](#troubleshooting)

---

## What It Does

- **Real-Time Hand Tracking & Gesture Recognition:** Uses the MediaPipe Tasks Python Vision API to track 21 hand landmarks and classify gestures directly from video frames at high frame rates.
- **Visual Feedback HUD:** Displays bounding boxes, 21-joint skeleton connections, gesture classifications, and current active commands live on the OpenCV feed.
- **Debounced & Safe Telemetry:** Commands are filtered with confidence scoring (`MIN_SCORE = 0.5`) and frame debouncing (`STABLE_FRAMES = 3`) to prevent erratic jerky motion.
- **Wireless Bluetooth Control:** Transmits continuous single-byte commands (10 Hz heartbeat) over an HC-05 Bluetooth module (or USB COM port) to the Arduino Uno.
- **Hardware Fail-Safe:** The rover immediately stops if the hand leaves the frame, confidence drops, or if communication is lost for more than 500 ms.
- **Upcoming - Obstacle Avoidance:** Autonomous collision avoidance using an ultrasonic sensor is currently planned and in development *(not yet implemented)*.

---

## System Architecture

```
  [ Laptop Webcam ]
         │
         ▼
  [ OpenCV Pipeline ]  ──►  Mirror Selfie (Flip) ──► BGR to RGB
         │
         ▼
  [ MediaPipe Gesture Recognizer ]  ──►  21 Landmarks + Classification Category + Score
         │
         ▼
  [ Python Safety & Filter Logic ]
     ├── Confidence Gate (score >= 0.5)
     ├── Consecutive Frame Debounce (>= 3 frames)
     └── Fallback: Any low confidence / unknown gesture ──► Emergency STOP ('S')
         │
         ▼
  [ Serial Telemetry (10 Hz Heartbeat) ]
         │
         ├──► USB Serial Cable (Development & Testing)
         └──► HC-05 Bluetooth SPP (Wireless Rover Operation)
                 │
                 ▼
          [ Arduino Uno R3 ]
             ├── Serial Parser: 'F', 'B', 'L', 'R', 'S'
             ├── Safety Watchdog: Stops motors if no byte received in 500 ms
             └── (Upcoming) HC-SR04 Ultrasonic Distance Sensor [In Development]
                 │
                 ▼
          [ L298N Dual H-Bridge Motor Driver ]
                 │
                 ├──► Left DC TT Gear Motor
                 └──► Right DC TT Gear Motor
```

---

## Gesture to Command Mapping

| Gesture | MediaPipe Classification | Rover Action | Serial Byte | Description |
|---|---|---|---|---|
| **Open Palm** | `open_palm` | **Forward** | `F` | Both motors drive forward |
| **Closed Fist** | `closed_fist` | **Reverse** | `B` | Both motors drive backward |
| **Pointing Up** | `pointing_up` | **Left** | `L` | Pivot/spin left (wheels in opposite directions) |
| **Victory (V sign)** | `victory` | **Right** | `R` | Pivot/spin right (wheels in opposite directions) |
| **Thumbs Up** | `thumb_up` / `thumbs_up` | **Stop** | `S` | Active stop command |
| **No Hand / Low Confidence** | *None* or score < 0.5 | **Stop** | `S` | Instant safety cutoff |

---

## Hardware Setup & Wiring

### Bill of Materials
- **Microcontroller:** Arduino Uno R3
- **Motor Driver:** L298N Dual H-Bridge Driver
- **Chassis & Motors:** 2WD Smart Robot Car Chassis with 2x DC TT gear motors
- **Wireless Communication:** HC-05 Bluetooth Serial Module (or USB cable for tethered tests)
- **Power Supply:** 4x to 6x AA battery pack (or 2x 18650 Li-ion cells) connected to L298N
- **Workstation:** PC/Laptop with webcam running Windows, Linux, or macOS
- **Upcoming Hardware:** HC-SR04 Ultrasonic Distance Sensor *(Not yet connected / in development)*

---

### Wiring Connections

#### 1. L298N Motor Driver to Arduino Uno
> **Important:** Remove the black jumper caps from **ENA** and **ENB** on the L298N board so the Arduino can control motor speed via PWM.

| Arduino Uno Pin | L298N Driver Pin | Description |
|---|---|---|
| **Pin 9 (PWM)** | **ENA** | Left motor speed control |
| **Pin 4** | **IN1** | Left motor forward direction |
| **Pin 5** | **IN2** | Left motor reverse direction |
| **Pin 10 (PWM)** | **ENB** | Right motor speed control |
| **Pin 6** | **IN3** | Right motor forward direction |
| **Pin 7** | **IN4** | Right motor reverse direction |
| **GND** | **GND** | **Common Ground** (Must be shared with Arduino GND) |

- **Motor Outputs:** Left motor wires to `OUT1`/`OUT2`, right motor wires to `OUT3`/`OUT4`. (If a motor spins backwards, simply invert its two output wires).
- **Driver Power:** Battery (+) to `12V` terminal; Battery (-) to `GND` terminal.
- **Arduino Power:** Arduino can be powered from the L298N `5V` output pin into Arduino `VIN`/`5V` (when 5V regulator jumper is installed), **or** via a separate battery/power bank. 
  *(Do not connect both USB 5V and L298N 5V simultaneously).*

#### 2. HC-05 Bluetooth Module
| HC-05 Pin | Arduino Uno Pin | Notes |
|---|---|---|
| **VCC** | **5V** | Power (3.6V - 6V tolerant) |
| **GND** | **GND** | Shared common ground |
| **TXD** | **Pin 0 (RX)** | HC-05 transmits, Arduino receives (3.3V logic is safely read as HIGH by 5V Arduino) |
| **RXD** | *Unconnected / Voltage Divider* | Only needed if Arduino sends data back to laptop (use 1k/2k resistor divider for 5V -> 3.3V) |

> **Pro Tip:** Disconnect HC-05 `TXD` from Arduino `Pin 0` when uploading sketches via the Arduino IDE USB cable, as they share the same hardware UART.

#### 3. Ultrasonic Sensor (Upcoming Feature)
> **Status: Planned / In Development (Not yet implemented)**  
> The HC-SR04 ultrasonic sensor will be mounted to the front chassis for hardware-level collision avoidance. Pins will be allocated (e.g., Trigger on Pin 11, Echo on Pin 12).

---

## Project Layout

```
gesture-robot/
├── .gitignore                     # Git ignore rules (virtualenv, cache, OS files, notes)
├── README.md                      # Comprehensive project documentation
└── gesture/
    ├── gesture_recognizer.task    # Google MediaPipe pretrained gesture model asset (~8.4 MB)
    └── live_gesture.py            # Main application: Webcam capture, inference & serial bridge
```

---

## Software Installation

### 1. Prerequisites
- **Python 3.12** is strongly recommended for MediaPipe compatibility.
- Arduino IDE for uploading the rover firmware.

### 2. Set Up Virtual Environment (Windows PowerShell)
```powershell
# Navigate to the project root
cd "C:\Users\Jeet Gohil\gesture-robot"

# Create a clean virtual environment
py -3.12 -m venv gesture-env

# Activate the virtual environment
.\gesture-env\Scripts\Activate.ps1

# Install dependencies
pip install mediapipe opencv-python pyserial numpy
```

### 3. MediaPipe Model Asset
The model file `gesture_recognizer.task` is located inside the `gesture/` folder.  
If you ever need to re-download it:
```powershell
Invoke-WebRequest -Uri "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task" -OutFile "gesture\gesture_recognizer.task"
```

---

## Running the System

### 1. Bluetooth Pairing (HC-05)
1. Power on the rover. The HC-05 LED will blink rapidly.
2. Pair the HC-05 in Windows Settings (`Bluetooth & devices` > `Add device`). PIN is typically `1234` or `0000`.
3. Open **Device Manager** or **Bluetooth Settings > More Bluetooth Settings > COM Ports** to check the **Outgoing COM Port** (e.g., `COM4` or `COM5`).

### 2. Configure & Run
Open `gesture/live_gesture.py` and set your port (or leave `PORT = None` for auto-detection):
```python
# ---------------- Settings ----------------
PORT = "COM4"              # Set to your Bluetooth or USB COM port, or None to auto-detect
BAUD = 9600
SEND_INTERVAL = 0.1        # 10 Hz telemetry frequency
STABLE_FRAMES = 3          # Consecutive frames required to confirm gesture
MIN_SCORE = 0.5            # Minimum gesture confidence threshold
# ------------------------------------------
```

Run the controller:
```powershell
python gesture/live_gesture.py
```

- A window titled **"live gesture"** will open.
- Show your hand to the camera to drive the rover.
- Press **`q`** in the video window to safely shut down (transmits an emergency stop byte `'S'` before closing).

---

## Safety & Fail-Safe Mechanisms

To protect the hardware and surroundings from unintended motion, multiple layers of safety are integrated:

1. **Self-Centering Stop State:** The default command is `'S'` (Stop). The rover only moves while a valid gesture is continuously recognized.
2. **Debounce Buffer (`STABLE_FRAMES`):** A gesture must be consistently recognized for at least 3 consecutive frames before triggering a movement command.
3. **Immediate Cutoff:** A transition to `stop` has zero debounce delay and is dispatched immediately.
4. **Arduino Hardware Watchdog (`TIMEOUT_MS`):** The Arduino firmware tracks the time of the last received command. If no byte is received for **500 ms** (e.g., laptop crashes, Python process exits, or Bluetooth disconnects), motor power is automatically cut.
5. **Always-Safe Exit:** Terminating the Python script automatically transmits `'S'` and releases serial resources.

---

## Arduino Firmware (Reference Sketch)

Upload the following sketch to your Arduino Uno using the Arduino IDE:

```cpp
/*
 * Gesture Controlled Rover - Arduino Firmware
 * Receives single-byte commands ('F', 'B', 'L', 'R', 'S') via Serial at 9600 baud.
 * Includes a 500ms safety timeout to prevent runaway conditions.
 */

// Left Motor (Motor A)
const int ENA = 9;   // PWM speed pin
const int IN1 = 4;   // Direction pin 1
const int IN2 = 5;   // Direction pin 2

// Right Motor (Motor B)
const int ENB = 10;  // PWM speed pin
const int IN3 = 6;   // Direction pin 1
const int IN4 = 7;   // Direction pin 2

// Configuration
const int MOTOR_SPEED = 180;         // PWM value (0 to 255)
const unsigned long TIMEOUT_MS = 500; // Watchdog timeout in ms
unsigned long lastCommandTime = 0;

void setup() {
  Serial.begin(9600);

  pinMode(ENA, OUTPUT);
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);

  pinMode(ENB, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);

  stopMotors();
}

void loop() {
  if (Serial.available() > 0) {
    char cmd = Serial.read();
    executeCommand(cmd);
    lastCommandTime = millis();
  }

  // Safety Watchdog: Auto-stop if no command received for TIMEOUT_MS
  if (millis() - lastCommandTime > TIMEOUT_MS) {
    stopMotors();
  }
}

void executeCommand(char cmd) {
  switch (cmd) {
    case 'F': forward();   break;
    case 'B': reverse();   break;
    case 'L': spinLeft();  break;
    case 'R': spinRight(); break;
    case 'S':
    default:  stopMotors(); break;
  }
}

void forward() {
  analogWrite(ENA, MOTOR_SPEED);
  analogWrite(ENB, MOTOR_SPEED);
  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, HIGH);
  digitalWrite(IN4, LOW);
}

void reverse() {
  analogWrite(ENA, MOTOR_SPEED);
  analogWrite(ENB, MOTOR_SPEED);
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, HIGH);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, HIGH);
}

void spinLeft() {
  analogWrite(ENA, MOTOR_SPEED);
  analogWrite(ENB, MOTOR_SPEED);
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, HIGH);
  digitalWrite(IN3, HIGH);
  digitalWrite(IN4, LOW);
}

void spinRight() {
  analogWrite(ENA, MOTOR_SPEED);
  analogWrite(ENB, MOTOR_SPEED);
  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, HIGH);
}

void stopMotors() {
  analogWrite(ENA, 0);
  analogWrite(ENB, 0);
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);
}
```

---

## Roadmap & Upcoming Features

- [x] **Webcam Hand Landmark Tracking:** Real-time 21-joint skeleton extraction using MediaPipe.
- [x] **Gesture Classification:** Real-time classification of Open Palm, Fist, Pointing, Victory, and Thumbs Up.
- [x] **Visual HUD:** Interactive skeleton, joint circles, bounding box, and label overlay.
- [x] **Safety Watchdog & Debounce:** Elimination of command jitter and fail-safe stop logic.
- [x] **Wireless Bluetooth Telemetry:** HC-05 connection over Windows COM port.
- [ ] **Upcoming Feature: Ultrasonic Obstacle Avoidance *(Not Implemented Yet)*:**
  - Mount an HC-SR04 ultrasonic distance sensor to the front of the rover.
  - Integrate distance reading directly into the Arduino loop.
  - Enforce an automatic emergency braking override if an obstacle is closer than 20 cm, regardless of incoming gesture commands.
- [ ] **Proportional Speed Control:** Modulate motor PWM based on hand distance from camera or finger spread.
- [ ] **Custom CNN Landmark Classifier:** Train a custom lightweight PyTorch model on custom-recorded gesture sessions for comparison against MediaPipe.

---

## Troubleshooting

| Issue | Likely Cause | Solution |
|---|---|---|
| `SerialException: could not open port` | Port in use by Arduino Serial Monitor or wrong COM port | Close Arduino IDE Serial Monitor/Plotter, check device manager for correct COM port number. |
| Rover does not move but script runs | Driver enable jumpers (ENA/ENB) still connected or battery low | Remove ENA/ENB jumpers to enable PWM control; ensure motor battery provides >= 7V under load. |
| Sketch fails to upload via USB | HC-05 is connected to Arduino Pin 0 (RX) | Unplug the wire from Arduino Pin 0 while uploading code, then reconnect it. |
| Motors spin in opposite directions | Motor wiring polarity inverted | Swap the two output wires on the L298N terminal (`OUT1`/`OUT2` or `OUT3`/`OUT4`). |
| Gesture confidence low / erratic | Poor room lighting or cluttered background | Ensure good frontal lighting on your hand and avoid complex moving background textures. |
| MediaPipe error on startup | Missing `gesture_recognizer.task` | Verify `gesture_recognizer.task` is in the `gesture/` folder alongside `live_gesture.py`. |

---

## License & Acknowledgements
- Powered by [Google MediaPipe Tasks](https://developers.google.com/mediapipe/solutions/vision/gesture_recognizer).
- OpenCV for real-time video stream processing.
- PySerial for serial telemetry communication.
