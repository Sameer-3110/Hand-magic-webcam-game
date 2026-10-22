# HAND MAGIC — webcam hand-controlled game

This is a working starter game inspired by the hand-tracked magic-circle effect in the reference image.

## 1. Install Python
Use Python 3.10 or 3.11 for the smoothest MediaPipe setup.

## 2. Create/activate a virtual environment (recommended)

Windows:
    py -3.11 -m venv .venv
    .venv\Scripts\activate

macOS/Linux:
    python3.11 -m venv .venv
    source .venv/bin/activate

## 3. Install dependencies

    pip install -r requirements.txt

## 4. Run

    python main.py

Allow webcam access if your operating system asks.

## Controls

OPEN PALM  -> animated magic circle / shield
POINT      -> fire energy bolts
PINCH      -> charge a smaller spell
FIST       -> burst effect
TWO HANDS  -> connect both hands with a magic field
Q or ESC   -> quit

## If the camera does not open

In main.py change:

    cv2.VideoCapture(0)

to:

    cv2.VideoCapture(1)

## Next upgrades

- Add enemies that move toward the player
- Make projectiles hit enemies
- Add health and score
- Add sound effects
- Add 3D/transparent magic textures
- Add gesture combos
- Add a proper start screen
- Port the visual effects to Unity for a more cinematic result
