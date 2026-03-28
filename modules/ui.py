"""
ui.py — Phase 9
HUD rendering helpers: legend strip, mode flash, toast notifications,
brightness warning, object count display.
"""
import cv2
import time
from typing import Optional

# Colour palette (BGR)
COL_ACCENT  = (  0, 117, 255)
COL_TEXT    = (200, 200, 200)
COL_DIM     = (100, 100, 100)

GESTURE_COLORS = {
    "DRAW"  : (  0, 117, 255),
    "FIST"  : (  0, 230, 255),
    "PALM"  : (  0,  60, 255),
    "V_SIGN": (  0, 255,   0),
    "IDLE"  : (120, 120, 120),
}
GESTURE_ICONS = {
    "DRAW"  : "\u270f  DRAW",
    "FIST"  : "\u270a FIST",
    "PALM"  : "\u270b PALM",
    "V_SIGN": "\u270c V_SIGN",
    "IDLE"  : "-- IDLE",
}

# ─────────────────────────────────────────────────────────────────────────────
# Mode flash (large centred text when gesture changes)
# ─────────────────────────────────────────────────────────────────────────────
class ModeFlash:
    DURATION = 45   # frames

    def __init__(self):
        self._text    = ""
        self._color   = (200, 200, 200)
        self._timer   = 0
        self._last_g  = ""

    def on_gesture(self, gesture: str):
        if gesture != self._last_g:
            self._text   = GESTURE_ICONS.get(gesture, gesture)
            self._color  = GESTURE_COLORS.get(gesture, (200, 200, 200))
            self._timer  = self.DURATION
            self._last_g = gesture

    def render(self, frame):
        if self._timer <= 0:
            return
        h, w = frame.shape[:2]
        alpha = self._timer / self.DURATION
        text  = self._text
        scale = 1.8
        thick = 3
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, thick)
        x = (w - tw) // 2
        y = (h + th) // 2

        # Fade effect via blended copy
        overlay = frame.copy()
        c = tuple(int(ch * alpha) for ch in self._color)
        cv2.putText(overlay, text, (x, y),
                    cv2.FONT_HERSHEY_SIMPLEX, scale, c, thick, cv2.LINE_AA)
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)
        self._timer -= 1


# ─────────────────────────────────────────────────────────────────────────────
# Toast notifications
# ─────────────────────────────────────────────────────────────────────────────
class ToastManager:
    DURATION = 90   # frames

    def __init__(self):
        self._toasts: list[dict] = []

    def show(self, text: str, color: tuple = (200, 200, 200)):
        self._toasts.append({"text": text, "color": color, "timer": self.DURATION})

    def render(self, frame):
        if not self._toasts:
            return
        h, w = frame.shape[:2]
        alive = []
        for i, t in enumerate(reversed(self._toasts)):
            alpha = t["timer"] / self.DURATION
            y     = h - 80 - i * 40
            text  = t["text"]
            scale = 0.7
            (tw, _), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, 2)
            x = w - tw - 20
            overlay = frame.copy()
            cv2.rectangle(overlay, (x-8, y-22), (x+tw+8, y+8), (15,15,25), -1)
            cv2.addWeighted(overlay, 0.6*alpha, frame, 1-0.6*alpha, 0, frame)
            c = tuple(int(ch * alpha) for ch in t["color"])
            cv2.putText(frame, text, (x, y),
                        cv2.FONT_HERSHEY_SIMPLEX, scale, c, 2, cv2.LINE_AA)
            t["timer"] -= 1
            if t["timer"] > 0:
                alive.append(t)
        self._toasts = list(reversed(alive))


# ─────────────────────────────────────────────────────────────────────────────
# Top HUD bar
# ─────────────────────────────────────────────────────────────────────────────
def draw_hud(frame, fps: float, obj_count: int, debug: bool):
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 52), (10, 10, 20), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

    cv2.putText(frame, "AirDraw AI", (12, 36),
                cv2.FONT_HERSHEY_SIMPLEX, 1.1, COL_ACCENT, 2, cv2.LINE_AA)
    cv2.putText(frame, f"FPS {fps:4.1f}", (w - 145, 36),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 120), 2, cv2.LINE_AA)
    cv2.putText(frame, f"Objects: {obj_count}", (w - 280, 36),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, COL_TEXT, 1, cv2.LINE_AA)
    if debug:
        cv2.putText(frame, "[DEBUG]", (12, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1, cv2.LINE_AA)


# ─────────────────────────────────────────────────────────────────────────────
# Gesture label (bottom-left pill)
# ─────────────────────────────────────────────────────────────────────────────
def draw_gesture_label(frame, gesture: str):
    h, w = frame.shape[:2]
    color = GESTURE_COLORS.get(gesture, COL_DIM)
    label = GESTURE_ICONS.get(gesture, gesture)
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, h - 52), (250, h), (12, 12, 22), -1)
    cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)
    cv2.putText(frame, label, (12, h - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2, cv2.LINE_AA)


# ─────────────────────────────────────────────────────────────────────────────
# Finger cursor dot
# ─────────────────────────────────────────────────────────────────────────────
def draw_finger_cursor(frame, landmarks: list, gesture: str):
    if not landmarks:
        return
    x, y  = landmarks[8]
    x, y  = int(x), int(y)
    color = GESTURE_COLORS.get(gesture, (200, 200, 200))
    cv2.circle(frame, (x, y), 20, color, 2, cv2.LINE_AA)
    cv2.circle(frame, (x, y),  6, color, -1, cv2.LINE_AA)


# ─────────────────────────────────────────────────────────────────────────────
# "Show hand" prompt
# ─────────────────────────────────────────────────────────────────────────────
def draw_no_hand_prompt(frame):
    h, w = frame.shape[:2]
    cv2.putText(frame, "Show your hand", (w//2 - 120, h//2),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (80, 80, 80), 2, cv2.LINE_AA)


# ─────────────────────────────────────────────────────────────────────────────
# Legend strip at bottom-right
# ─────────────────────────────────────────────────────────────────────────────
def draw_legend(frame):
    h, w = frame.shape[:2]
    entries = [
        ("\u270f  Index up  = DRAW",  GESTURE_COLORS["DRAW"]),
        ("\u270c V sign    = FINISH", GESTURE_COLORS["V_SIGN"]),
        ("\u270a Fist      = GRAB",  GESTURE_COLORS["FIST"]),
        ("\u270b Open palm = DELETE", GESTURE_COLORS["PALM"]),
    ]
    line_h = 24
    pad    = 12
    total  = len(entries) * line_h + pad * 2
    x0     = w - 260
    y0     = h - total - 60

    overlay = frame.copy()
    cv2.rectangle(overlay, (x0-8, y0), (w-8, y0+total), (12,12,22), -1)
    cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

    for i, (text, color) in enumerate(entries):
        y = y0 + pad + (i+1)*line_h
        cv2.putText(frame, text, (x0, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, color, 1, cv2.LINE_AA)


# ─────────────────────────────────────────────────────────────────────────────
# Deletion flash overlay
# ─────────────────────────────────────────────────────────────────────────────
class DeleteFlash:
    DURATION = 12

    def __init__(self):
        self._timer = 0

    def trigger(self):
        self._timer = self.DURATION

    def render(self, frame):
        if self._timer <= 0:
            return
        alpha = self._timer / self.DURATION * 0.35
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (frame.shape[1], frame.shape[0]),
                      (0, 40, 180), -1)
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
        self._timer -= 1
