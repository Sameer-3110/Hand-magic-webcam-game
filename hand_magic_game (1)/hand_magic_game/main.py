import cv2
import math
import random
import time
import numpy as np
import mediapipe as mp

# ============================================================
# HAND MAGIC — webcam hand-controlled visual game
# Controls:
#   Open palm  -> shield / magic circle
#   Point      -> fire energy bolts
#   Pinch      -> grab / charge a spell
#   Fist       -> burst attack
#   Q / ESC    -> quit
# ============================================================

W, H = 1280, 720
MAX_PARTICLES = 700

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

# 21 MediaPipe landmark indices
WRIST = 0
THUMB_TIP = 4
INDEX_MCP = 5
INDEX_TIP = 8
MIDDLE_MCP = 9
MIDDLE_TIP = 12
RING_TIP = 16
PINKY_TIP = 20


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def angle(cx, cy, x, y):
    return math.atan2(y - cy, x - cx)


def is_finger_extended(lm, tip, pip):
    # Compare distance from wrist. This is deliberately forgiving.
    wrist = lm[WRIST]
    return dist(lm[tip], wrist) > dist(lm[pip], wrist) * 1.12


def classify_gesture(lm):
    index = is_finger_extended(lm, INDEX_TIP, 6)
    middle = is_finger_extended(lm, MIDDLE_TIP, 10)
    ring = is_finger_extended(lm, RING_TIP, 14)
    pinky = is_finger_extended(lm, PINKY_TIP, 18)

    pinch = dist(lm[THUMB_TIP], lm[INDEX_TIP]) < 45

    if pinch:
        return "PINCH"
    if not any([index, middle, ring, pinky]):
        return "FIST"
    if index and not middle and not ring and not pinky:
        return "POINT"
    if index and middle and ring and pinky:
        return "OPEN"
    return "HAND"


def glow_circle(img, center, radius, color=(70, 210, 255), thickness=2, glow=18):
    overlay = img.copy()
    for i in range(glow, 0, -2):
        alpha = 0.008
        r = radius + i
        cv2.circle(overlay, center, r, color, max(1, thickness))
        img[:] = cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0)
    cv2.circle(img, center, radius, color, thickness, cv2.LINE_AA)


def draw_magic_circle(img, cx, cy, base_r, t, power=1.0):
    cx, cy = int(cx), int(cy)
    r = int(base_r * (0.92 + 0.08 * math.sin(t * 4)))

    # Soft halo
    halo = img.copy()
    cv2.circle(halo, (cx, cy), r + 18, (20, 100, 100), 7, cv2.LINE_AA)
    img[:] = cv2.addWeighted(halo, 0.10, img, 0.90, 0)

    # Main rings
    for rr, th in [(r, 2), (int(r * .78), 1), (int(r * .48), 2)]:
        cv2.circle(img, (cx, cy), rr, (70, 190, 255), th, cv2.LINE_AA)

    # Rotating dashed ring
    dash_r = int(r * .91)
    dash_count = 30
    for i in range(dash_count):
        a1 = t * 0.75 + i * 2 * math.pi / dash_count
        a2 = a1 + 0.11
        p1 = (int(cx + dash_r * math.cos(a1)), int(cy + dash_r * math.sin(a1)))
        p2 = (int(cx + dash_r * math.cos(a2)), int(cy + dash_r * math.sin(a2)))
        cv2.line(img, p1, p2, (100, 220, 255), 2, cv2.LINE_AA)

    # Inner rotating dashed ring, opposite direction
    inner = int(r * .62)
    for i in range(18):
        a1 = -t * 1.2 + i * 2 * math.pi / 18
        a2 = a1 + .16
        p1 = (int(cx + inner * math.cos(a1)), int(cy + inner * math.sin(a1)))
        p2 = (int(cx + inner * math.cos(a2)), int(cy + inner * math.sin(a2)))
        cv2.line(img, p1, p2, (255, 225, 100), 2, cv2.LINE_AA)

    # Sacred triangle
    tri_r = int(r * .50)
    pts = []
    for k in range(3):
        a = t * .35 - math.pi / 2 + k * 2 * math.pi / 3
        pts.append((int(cx + tri_r * math.cos(a)), int(cy + tri_r * math.sin(a))))
    cv2.polylines(img, [np.array(pts)], True, (255, 220, 100), 1, cv2.LINE_AA)

    # Center
    cv2.circle(img, (cx, cy), 6 + int(5 * power), (255, 240, 130), -1, cv2.LINE_AA)
    cv2.circle(img, (cx, cy), 18 + int(10 * power), (255, 190, 70), 1, cv2.LINE_AA)


def draw_runes(img, cx, cy, r, t):
    symbols = ["△", "◇", "○", "+", "✦"]
    # OpenCV often lacks Unicode glyphs, so use simple geometry instead.
    for i in range(10):
        a = t * .3 + i * 2 * math.pi / 10
        x = int(cx + r * math.cos(a))
        y = int(cy + r * math.sin(a))
        if i % 3 == 0:
            pts = np.array([[x, y-9], [x-8, y+6], [x+8, y+6]])
            cv2.polylines(img, [pts], True, (150, 190, 255), 1, cv2.LINE_AA)
        elif i % 3 == 1:
            cv2.circle(img, (x, y), 7, (255, 220, 120), 1, cv2.LINE_AA)
        else:
            cv2.rectangle(img, (x-6, y-6), (x+6, y+6), (120, 220, 255), 1, cv2.LINE_AA)


def spawn_particles(particles, x, y, count=12, color=(70, 220, 255), speed=4):
    for _ in range(count):
        if len(particles) >= MAX_PARTICLES:
            particles.pop(0)
        a = random.random() * math.tau
        s = random.uniform(.5, speed)
        particles.append([
            float(x), float(y),
            math.cos(a) * s, math.sin(a) * s,
            random.uniform(.25, 1.0),
            random.randint(2, 6),
            color
        ])


def update_particles(img, particles):
    alive = []
    for p in particles:
        x, y, vx, vy, life, size, color = p
        x += vx
        y += vy
        vx *= .985
        vy *= .985
        life -= .025
        size = max(1, int(size * .97))
        if life > 0 and -30 < x < W + 30 and -30 < y < H + 30:
            cv2.circle(img, (int(x), int(y)), size, color, -1, cv2.LINE_AA)
            alive.append([x, y, vx, vy, life, size, color])
    particles[:] = alive


def draw_bolt(img, x1, y1, x2, y2, t):
    # Lightning-like segmented bolt.
    pts = [(int(x1), int(y1))]
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy) or 1
    nx, ny = -dy / length, dx / length
    steps = max(3, int(length / 35))
    for i in range(1, steps):
        q = i / steps
        jitter = math.sin(t * 20 + i * 5) * 8
        pts.append((int(x1 + dx*q + nx*jitter), int(y1 + dy*q + ny*jitter)))
    pts.append((int(x2), int(y2)))
    arr = np.array(pts)
    cv2.polylines(img, [arr], False, (40, 150, 255), 8, cv2.LINE_AA)
    cv2.polylines(img, [arr], False, (230, 245, 255), 2, cv2.LINE_AA)


def main():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, H)

    if not cap.isOpened():
        raise RuntimeError("Could not open webcam. Try camera index 1 instead of 0.")

    particles = []
    bolts = []
    last_time = time.time()
    spell_cooldown = 0.0
    score = 0
    hand_count = 0

    with mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        min_detection_confidence=.60,
        min_tracking_confidence=.60
    ) as hands:

        while True:
            ok, frame = cap.read()
            if not ok:
                break

            frame = cv2.flip(frame, 1)
            frame = cv2.resize(frame, (W, H))
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb)

            now = time.time()
            dt = min(.05, now - last_time)
            last_time = now
            spell_cooldown = max(0, spell_cooldown - dt)

            hand_count = 0
            detected = []

            if results.multi_hand_landmarks:
                hand_count = len(results.multi_hand_landmarks)

                for hand in results.multi_hand_landmarks:
                    lm = []
                    for p in hand.landmark:
                        lm.append((int(p.x * W), int(p.y * H)))

                    gesture = classify_gesture(lm)
                    fx, fy = lm[INDEX_TIP]
                    wristx, wristy = lm[WRIST]

                    detected.append((fx, fy, gesture, lm))

                    # Subtle landmark skeleton.
                    mp_draw.draw_landmarks(
                        frame, hand, mp_hands.HAND_CONNECTIONS,
                        mp_draw.DrawingSpec(color=(80, 150, 170), thickness=1, circle_radius=2),
                        mp_draw.DrawingSpec(color=(50, 90, 120), thickness=1)
                    )

                    if gesture == "OPEN":
                        draw_magic_circle(frame, fx, fy, 175, now, 1.0)
                        draw_runes(frame, fx, fy, 145, now)
                        spawn_particles(particles, fx, fy, 2, (100, 220, 255), 2.5)

                    elif gesture == "PINCH":
                        draw_magic_circle(frame, fx, fy, 120, now * 1.5, 1.5)
                        cv2.line(frame, lm[THUMB_TIP], lm[INDEX_TIP],
                                 (255, 230, 130), 3, cv2.LINE_AA)
                        spawn_particles(particles, fx, fy, 5, (255, 190, 80), 3.5)

                    elif gesture == "POINT":
                        cv2.circle(frame, (fx, fy), 22, (255, 220, 100), 2, cv2.LINE_AA)
                        cv2.line(frame, (wristx, wristy), (fx, fy),
                                 (80, 180, 255), 2, cv2.LINE_AA)

                        # Fire toward the top-center while pointing.
                        if spell_cooldown <= 0:
                            draw_bolt(frame, fx, fy, W//2, 45, now)
                            spawn_particles(particles, fx, fy, 25, (80, 210, 255), 6)
                            spell_cooldown = .22
                            score += 1

                    elif gesture == "FIST":
                        # Burst ring.
                        rr = int(55 + 35 * (0.5 + 0.5 * math.sin(now * 12)))
                        cv2.circle(frame, (fx, fy), rr, (80, 150, 255), 3, cv2.LINE_AA)
                        spawn_particles(particles, fx, fy, 8, (80, 150, 255), 5)

            # Two-hand synergy: connect both index fingers.
            if len(detected) == 2:
                x1, y1 = detected[0][0], detected[0][1]
                x2, y2 = detected[1][0], detected[1][1]
                cv2.line(frame, (x1, y1), (x2, y2), (255, 180, 70), 2, cv2.LINE_AA)
                midx, midy = (x1+x2)//2, (y1+y2)//2
                rr = int(70 + 25 * math.sin(now * 5))
                cv2.circle(frame, (midx, midy), rr, (255, 220, 100), 2, cv2.LINE_AA)
                draw_magic_circle(frame, midx, midy, 90, -now, 1.2)
                spawn_particles(particles, midx, midy, 2, (255, 210, 100), 3)

            update_particles(frame, particles)

            # HUD
            cv2.rectangle(frame, (18, 18), (395, 130), (10, 15, 25), -1)
            cv2.rectangle(frame, (18, 18), (395, 130), (70, 150, 190), 1)

            cv2.putText(frame, "HAND MAGIC", (35, 52),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (120, 220, 255), 2, cv2.LINE_AA)
            cv2.putText(frame, f"Hands: {hand_count}", (35, 82),
                        cv2.FONT_HERSHEY_SIMPLEX, .65, (210, 225, 235), 1, cv2.LINE_AA)
            cv2.putText(frame, f"Spells: {score}", (190, 82),
                        cv2.FONT_HERSHEY_SIMPLEX, .65, (255, 220, 120), 1, cv2.LINE_AA)
            cv2.putText(frame, "OPEN=shield  POINT=fire  PINCH=charge  FIST=burst",
                        (35, 108), cv2.FONT_HERSHEY_SIMPLEX, .43, (170, 190, 205), 1, cv2.LINE_AA)

            cv2.putText(frame, "Q / ESC  EXIT", (W-175, H-25),
                        cv2.FONT_HERSHEY_SIMPLEX, .55, (180, 200, 210), 1, cv2.LINE_AA)

            cv2.imshow("HAND MAGIC - Webcam Game", frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord('q')):
                break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
