"""
interaction.py — Phase 7 & 8
Handles:
  - PINCH: grab nearest object/group and drag it
  - PALM:  hold-to-delete with radial progress arc
"""
import cv2
import time
import math
from utils.geometry   import distance
from modules.object_store import ObjectStore

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
GRAB_RADIUS       = 80     # px — how close pinch must be to an object to select
DELETE_HOLD_SEC   = 1.0    # seconds of palm hold to confirm delete
DRAG_LERP         = 0.4    # smoothing factor for drag movement (0=no move, 1=instant)

COL_SELECT        = (  0, 230, 255)   # selection highlight (BGR)
COL_DELETE_ARC    = (  0,  60, 255)   # delete progress arc
COL_DELETE_FILL   = ( 30,  30,  80)   # arc background circle


class InteractionEngine:
    def __init__(self, store: ObjectStore):
        self._store        = store

        # Grab state
        self._grabbed_id:  str | None  = None    # selected object id
        self._last_pinch:  tuple | None = None   # last pinch (x,y)

        # Delete state
        self._delete_id:   str | None  = None
        self._delete_start: float      = 0.0
        self._delete_x:    int         = 0
        self._delete_y:    int         = 0

    # ── Pinch / Grab ─────────────────────────────────────────────────────────

    def update_pinch(self, px: int, py: int):
        """Call every frame while gesture == PINCH."""
        if self._grabbed_id is None:
            # Try to select nearest object
            oid = self._store.find_at_point(px, py)
            if oid:
                self._grabbed_id = oid
                self._last_pinch = (px, py)
        else:
            if self._last_pinch:
                dx = px - self._last_pinch[0]
                dy = py - self._last_pinch[1]
                # Move entire group
                self._store.move_group(self._grabbed_id, dx, dy)
            self._last_pinch = (px, py)

    def release_pinch(self):
        """Call when gesture leaves PINCH."""
        self._grabbed_id = None
        self._last_pinch = None

    @property
    def grabbed_id(self) -> str | None:
        return self._grabbed_id

    def grabbed_members(self) -> set[str]:
        if self._grabbed_id:
            return set(self._store.get_group_members(self._grabbed_id))
        return set()

    # ── Palm / Delete ────────────────────────────────────────────────────────

    def update_palm(self, px: int, py: int) -> bool:
        """
        Call every frame while gesture == PALM.
        Returns True when deletion is triggered.
        """
        oid = self._store.find_at_point(px, py)
        if oid is None:
            self._reset_delete()
            return False

        if oid != self._delete_id:
            # New target
            self._delete_id    = oid
            self._delete_start = time.time()
            self._delete_x     = px
            self._delete_y     = py
            return False

        # Same target — check elapsed
        elapsed = time.time() - self._delete_start
        self._delete_x = px
        self._delete_y = py

        if elapsed >= DELETE_HOLD_SEC:
            self._store.remove_group(oid)
            self._reset_delete()
            return True   # deletion happened

        return False

    def release_palm(self):
        self._reset_delete()

    def _reset_delete(self):
        self._delete_id    = None
        self._delete_start = 0.0

    def delete_progress(self) -> float:
        """0.0–1.0 progress toward deletion, or 0 if no active target."""
        if self._delete_id is None:
            return 0.0
        return min(1.0, (time.time() - self._delete_start) / DELETE_HOLD_SEC)

    # ── Rendering ─────────────────────────────────────────────────────────────

    def render_grab_cursor(self, frame, px, py):
        """Yellow grab cursor ring at pinch point."""
        px, py = int(px), int(py)
        cv2.circle(frame, (px, py), 22, COL_SELECT, 2, cv2.LINE_AA)
        cv2.circle(frame, (px, py),  5, COL_SELECT, -1, cv2.LINE_AA)
        # Cross-hair lines
        cv2.line(frame, (px-12, py), (px+12, py), COL_SELECT, 1)
        cv2.line(frame, (px, py-12), (px, py+12), COL_SELECT, 1)

    def render_delete_arc(self, frame):
        """Radial progress arc around palm center."""
        progress = self.delete_progress()
        if progress <= 0:
            return
        px, py = int(self._delete_x), int(self._delete_y)
        radius  = 32
        # Background circle
        cv2.circle(frame, (px, py), radius, COL_DELETE_FILL, -1, cv2.LINE_AA)
        cv2.circle(frame, (px, py), radius, COL_DELETE_ARC,   1, cv2.LINE_AA)
        # Progress arc (sweep from -90° clockwise)
        sweep = int(360 * progress)
        if sweep > 0:
            cv2.ellipse(frame, (px, py), (radius, radius),
                        -90, 0, sweep, COL_DELETE_ARC, 3, cv2.LINE_AA)
        # Inner text
        pct = int(progress * 100)
        cv2.putText(frame, f"{pct}%", (px - 15, py + 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1, cv2.LINE_AA)
