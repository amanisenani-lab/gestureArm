import cv2
import mediapipe as mp
import socket

# =========================
# WIFI UDP CONFIG
# =========================
ESP32_IP = "172.20.10.2"   # PUT YOUR ESP32 IP HERE
ESP32_PORT = 4210

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# =========================
# CAMERA
# =========================
cam_source = 0  # PC camera

# =========================
# SERVO LIMITS
# =========================

# X Servo
x_min = 0
x_mid = 90
x_max = 180

# Palm angle limits
palm_angle_min = -50
palm_angle_mid = 20

# Y Servo
y_min = 0
y_mid = 35
y_max = 70

# Wrist Y limits
wrist_y_min = 0.3
wrist_y_max = 0.9

# Z Servo
z_min = 0
z_mid = 90
z_max = 180

# Palm size limits
plam_size_min = 0.1
plam_size_max = 0.3

# Claw Servo
claw_open_angle = 90
claw_close_angle = 0

# Default servo angles
servo_angle = [x_mid, y_mid, z_mid, claw_open_angle]
prev_servo_angle = servo_angle.copy()

# Fist threshold
fist_threshold = 7

# =========================
# MEDIAPIPE
# =========================
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_hands = mp.solutions.hands

cap = cv2.VideoCapture(cam_source)

# =========================
# FUNCTIONS
# =========================

clamp = lambda n, minn, maxn: max(min(maxn, n), minn)

map_range = lambda x, in_min, in_max, out_min, out_max: int(
    (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min
)

# Check if hand is closed
def is_fist(hand_landmarks, palm_size):

    distance_sum = 0

    WRIST = hand_landmarks.landmark[0]

    for i in [7,8,11,12,15,16,19,20]:

        distance_sum += (
            (WRIST.x - hand_landmarks.landmark[i].x)**2 +
            (WRIST.y - hand_landmarks.landmark[i].y)**2 +
            (WRIST.z - hand_landmarks.landmark[i].z)**2
        )**0.5

    return distance_sum / palm_size < fist_threshold


def landmark_to_servo_angle(hand_landmarks):

    servo_angle = [x_mid, y_mid, z_mid, claw_open_angle]

    WRIST = hand_landmarks.landmark[0]
    INDEX_FINGER_MCP = hand_landmarks.landmark[5]

    # Palm size
    palm_size = (
        (WRIST.x - INDEX_FINGER_MCP.x)**2 +
        (WRIST.y - INDEX_FINGER_MCP.y)**2 +
        (WRIST.z - INDEX_FINGER_MCP.z)**2
    )**0.5

    # =========================
    # CLAW
    # =========================
    if is_fist(hand_landmarks, palm_size):
        servo_angle[3] = claw_close_angle
    else:
        servo_angle[3] = claw_open_angle

    # =========================
    # X SERVO
    # =========================
    distance = palm_size

    angle = (WRIST.x - INDEX_FINGER_MCP.x) / distance

    angle = int(angle * 180 / 3.1415926)

    angle = clamp(angle, palm_angle_min, palm_angle_mid)

    servo_angle[0] = map_range(
        angle,
        palm_angle_min,
        palm_angle_mid,
        x_max,
        x_min
    )

    # =========================
    # Y SERVO
    # =========================
    wrist_y = clamp(WRIST.y, wrist_y_min, wrist_y_max)

    servo_angle[1] = map_range(
        wrist_y,
        wrist_y_min,
        wrist_y_max,
        y_max,
        y_min
    )

    # =========================
    # Z SERVO
    # =========================
    palm_size = clamp(
        palm_size,
        plam_size_min,
        plam_size_max
    )

    servo_angle[2] = map_range(
        palm_size,
        plam_size_min,
        plam_size_max,
        z_max,
        z_min
    )

    # Convert to int
    servo_angle = [int(i) for i in servo_angle]

    return servo_angle

# =========================
# MAIN LOOP
# =========================

with mp_hands.Hands(
    model_complexity=0,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
) as hands:

    while cap.isOpened():

        success, image = cap.read()

        if not success:
            continue

        # Convert image
        image.flags.writeable = False
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Process hands
        results = hands.process(image)

        # Convert back
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        # =========================
        # HAND DETECTED
        # =========================
        if results.multi_hand_landmarks:

            hand_landmarks = results.multi_hand_landmarks[0]

            servo_angle = landmark_to_servo_angle(hand_landmarks)

            # Send only if changed
            if servo_angle != prev_servo_angle:

                print("Servo:", servo_angle)

                prev_servo_angle = servo_angle.copy()

                # SEND UDP
                sock.sendto(
                    bytearray(servo_angle),
                    (ESP32_IP, ESP32_PORT)
                )

            # Draw landmarks
            mp_drawing.draw_landmarks(
                image,
                hand_landmarks,
                mp_hands.HAND_CONNECTIONS,
                mp_drawing_styles.get_default_hand_landmarks_style(),
                mp_drawing_styles.get_default_hand_connections_style()
            )

        # Flip image
        image = cv2.flip(image, 1)

        # Show angles
        cv2.putText(
            image,
            str(servo_angle),
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 255),
            2
        )

        cv2.imshow("Hand Tracking Robot Arm", image)

        # ESC to exit
        if cv2.waitKey(5) & 0xFF == 27:
            break

cap.release()
cv2.destroyAllWindows()