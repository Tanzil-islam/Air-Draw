"""
drawing.py — Phase 3
Stroke capture, interpolation, rendering.
Each completed stroke is handed to shape_detector for shape snapping,
then added to the ObjectStore.
"""
import cv2
import numpy as np
from utils.geometry import interpolate_points, compute_bbox

# Colours (BGR)
COL_ACTIVE    = (0, 117, 255)   # #FF7500 in BGR
COL_COMPLETED = (0, 117, 255)   # #FF7500 in BGR
COL_GLOW      = (0,  60, 180)   # dimmer glow layer

STROKE_THICKNESS = 3
GLOW_THICKNESS   = 8
MAX_STROKE_PTS   = 600            # cap to avoid memory growth


class DrawingEngine:
    def __init__(self):
        self._current = []
        self._drawing = False
        self._cooldown = 0
        self.COOLDOWN_FRAMES = 25
    @property
    def is_drawing(self) -> bool:
        return self._drawing

    def start_stroke(self, pt):
        self._drawing = True
        self._current = [pt]
        self._cooldown = self.COOLDOWN_FRAMES

    def add_point(self, pt):
        if not self._drawing:
            return

        self._cooldown = self.COOLDOWN_FRAMES

        if self._current:
            last = self._current[-1]
            interp = interpolate_points(last, pt, max_gap=20)
            self._current.extend(interp)
        else:
            self._current.append(pt)

    def try_finalize_stroke(self):
        if not self._drawing:
            return None

        self._cooldown -= 1
        if self._cooldown > 0:
            return None

        return self.force_finalize_stroke()
        
    def force_finalize_stroke(self):
        self._drawing = False
        self._cooldown = 0
        stroke = self._current
        self._current = []
        if len(stroke) < 2:
            return None
        return stroke

    def render_active(self, frame):
        if len(self._current) < 2:
            return
        pts = np.array(self._current, dtype=np.int32).reshape(-1, 1, 2)
        cv2.polylines(frame, [pts], False, COL_GLOW, GLOW_THICKNESS, cv2.LINE_AA)
        cv2.polylines(frame, [pts], False, COL_ACTIVE, STROKE_THICKNESS, cv2.LINE_AA)

    @staticmethod
    def render_stroke(frame, points, color=COL_COMPLETED, thickness=STROKE_THICKNESS):
        if len(points) < 2:
            return
        pts = np.array(points, dtype=np.int32).reshape(-1, 1, 2)
        cv2.polylines(frame, [pts], False, color, thickness, cv2.LINE_AA)