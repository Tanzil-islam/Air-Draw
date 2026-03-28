"""
gesture.py — Phase 2
Classifies a 21-landmark hand pose into one of four gesture states:
  DRAW   — index finger up, middle down
  PINCH  — thumb tip close to index tip
  PALM   — all fingers extended
  IDLE   — default / fist
"""
import math
from utils.smoothing import GestureBuffer, distance

# Key landmark indices (mirrors HandTracker constants)
THUMB_TIP   = 4
INDEX_PIP   = 6
INDEX_TIP   = 8
MIDDLE_PIP  = 10
MIDDLE_TIP  = 12
RING_PIP    = 14
RING_TIP    = 16
PINKY_PIP   = 18
PINKY_TIP   = 20

# Pinch threshold in pixels (≈40 px on 1280-wide frame)
PINCH_THRESHOLD = 45


def _finger_up(landmarks: list, tip: int, pip: int) -> bool:
    """True if fingertip is above its PIP joint (lower y = higher on screen)."""
    return landmarks[tip][1] < landmarks[pip][1]


def classify_raw(landmarks: list[tuple[int, int]]) -> str:
    """
    Classify gesture from raw 21 landmarks.
    Returns: 'DRAW', 'FIST', 'PALM', 'V_SIGN' or 'IDLE'
    """
    if not landmarks or len(landmarks) < 21:
        return "IDLE"

    idx_up    = _finger_up(landmarks, INDEX_TIP,  INDEX_PIP)
    mid_up    = _finger_up(landmarks, MIDDLE_TIP, MIDDLE_PIP)
    ring_up   = _finger_up(landmarks, RING_TIP,   RING_PIP)
    pinky_up  = _finger_up(landmarks, PINKY_TIP,  PINKY_PIP)

    # ── Palm: all four fingers up ─────────────────────────────────────────────
    if idx_up and mid_up and ring_up and pinky_up:
        return "PALM"
        
    # ── V Sign: index and middle up, others down ──────────────────────────────
    if idx_up and mid_up and not ring_up and not pinky_up:
        return "V_SIGN"

    # ── Draw: only index finger up ────────────────────────────────────────────
    if idx_up and not mid_up and not ring_up and not pinky_up:
        return "DRAW"
        
    # ── Fist: all fingers down ────────────────────────────────────────────────
    if not idx_up and not mid_up and not ring_up and not pinky_up:
        return "FIST"

    return "IDLE"


class GestureClassifier:
    """
    Wraps classify_raw with a smoothing buffer so rapid hand shifts
    don't cause gesture flickering.
    """
    def __init__(self, buffer_size: int = 5):
        self._buf     = GestureBuffer(size=buffer_size)
        self.gesture  = "IDLE"   # current smoothed gesture
        self.current_state = "IDLE"
        self.state_count = 0

    def update(self, landmarks: list[tuple[int, int]]) -> str:
        raw           = classify_raw(landmarks)
        gesture  = self._buf.update(raw)
        
        if gesture == self.current_state:
            self.state_count += 1
        else:
            self.current_state = gesture
            self.state_count = 1
            
        self.gesture = gesture
        return self.gesture

    def frames_in_state(self, gesture: str) -> int:
        if gesture == self.current_state:
            return self.state_count
        return 0

    def reset(self):
        self._buf.clear()
        self.gesture = "IDLE"
        self.current_state = "IDLE"
        self.state_count = 0
