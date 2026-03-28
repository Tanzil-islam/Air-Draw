"""
shape_detector.py — Phase 4
Detects closed shapes in a stroke and snaps them to clean primitives.
MVP: Rectangle. Extended: Circle, Triangle, Line.
"""
import math
import cv2
import numpy as np
from utils.geometry import distance, rdp_simplify, angle_between, compute_bbox


# ─────────────────────────────────────────────────────────────────────────────
# Thresholds
# ─────────────────────────────────────────────────────────────────────────────
CLOSE_THRESHOLD   = 120     # px — first↔last point to consider shape closed
RDP_EPSILON       = 15.0    # RDP simplification aggressiveness
RECT_ANGLE_TOL    = 40      # degrees — how much corner can deviate from 90°
MIN_SHAPE_AREA    = 250     # px² — ignore tiny accidental shapes
CIRCLE_VAR_TOL    = 0.35    # normalised radius variance for circle detection


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def is_closed(stroke: list, threshold: int = CLOSE_THRESHOLD) -> bool:
    if len(stroke) < 10:
        return False
    return distance(stroke[0], stroke[-1]) < threshold


def stroke_area(stroke: list) -> float:
    """Shoelace formula for polygon area."""
    n = len(stroke)
    if n < 3:
        return 0.0
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += stroke[i][0] * stroke[j][1]
        area -= stroke[j][0] * stroke[i][1]
    return abs(area) / 2.0


# ─────────────────────────────────────────────────────────────────────────────
# Shape detectors
# ─────────────────────────────────────────────────────────────────────────────

def detect_rectangle(simplified: list[tuple]) -> dict | None:
    """
    Returns {type:'rectangle', bbox:{x,y,w,h}} if simplified has ~4 corners
    all at ~90°, else None.
    """
    # Allow 3–5 vertices (hand drawing is imprecise)
    if not (3 <= len(simplified) <= 6):
        return None
    n = len(simplified)
    angles = []
    for i in range(n):
        p_prev = simplified[(i - 1) % n]
        p_curr = simplified[i]
        p_next = simplified[(i + 1) % n]
        angles.append(angle_between(p_prev, p_curr, p_next))

    if all(abs(a - 90.0) < RECT_ANGLE_TOL for a in angles):
        bbox = compute_bbox(simplified)
        if bbox and bbox["w"] * bbox["h"] >= MIN_SHAPE_AREA:
            return {"type": "rectangle", "bbox": bbox}
    return None


def detect_circle(stroke: list) -> dict | None:
    """
    Returns {type:'circle', cx, cy, r} if stroke is roughly circular.
    """
    if len(stroke) < 20:
        return None
    pts = np.array(stroke, dtype=np.float32)
    # Bounding box center is much more reliable for hand-drawn circles
    cx = float((pts[:, 0].min() + pts[:, 0].max()) / 2)
    cy = float((pts[:, 1].min() + pts[:, 1].max()) / 2)
    
    radii     = [distance((cx, cy), p) for p in stroke]
    mean_r    = sum(radii) / len(radii)
    variance  = sum((r - mean_r) ** 2 for r in radii) / len(radii)
    norm_var  = math.sqrt(variance) / (mean_r + 1e-9)
    if norm_var < CIRCLE_VAR_TOL and mean_r > 20:
        return {"type": "circle", "cx": int(cx), "cy": int(cy), "r": int(mean_r)}
    return None


def detect_line(stroke: list) -> dict | None:
    """
    Returns {type:'line', p1, p2} if stroke is mostly linear.
    """
    if len(stroke) < 5:
        return None
        
    p1 = np.array(stroke[0])
    p2 = np.array(stroke[-1])
    d = np.linalg.norm(p2 - p1)
    
    if d < 40:
        return None
        
    v = (p2 - p1) / d
    n = np.array([-v[1], v[0]])
    
    pts = np.array(stroke)
    deviations = np.abs(np.dot(pts - p1, n))
    max_dev = np.max(deviations)
    
    # A line if maximum deviation from the straight sequence is minimal
    if max_dev < d * 0.15 + 15:
        return {"type": "line", "p1": stroke[0], "p2": stroke[-1]}
        
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Main pipeline
# ─────────────────────────────────────────────────────────────────────────────

def detect_shape(stroke: list[tuple]) -> dict | None:
    """
    Run shape detection pipeline on a finalized stroke.
    Returns a shape dict, or None if no shape detected (freehand).
    """
    if len(stroke) < 5:
        return None

    # 1. Check line first. This prevents lines whose endpoints happen to be 
    # closer than CLOSE_THRESHOLD from being swallowed by area tests.
    line = detect_line(stroke)
    if line:
        return line

    closed = is_closed(stroke)

    # 2. Check 2D shapes if closed
    if closed:
        area = stroke_area(stroke)
        if area < MIN_SHAPE_AREA:
            return None

        # Try circle 
        circle = detect_circle(stroke)
        if circle:
            return circle

        # Try rectangle
        simplified = rdp_simplify(stroke, epsilon=RDP_EPSILON)
        rect = detect_rectangle(simplified)
        if rect:
            return rect

    return None   # Freehand stroke — keep as-is


# ─────────────────────────────────────────────────────────────────────────────
# Rendering helpers (used by ObjectStore renderer)
# ─────────────────────────────────────────────────────────────────────────────

def render_shape(frame, shape: dict, color: tuple, thickness: int = 2,
                 label: str | None = None):
    """Render a detected clean shape onto frame."""
    t = shape.get("type")

    if t == "rectangle":
        b = shape["bbox"]
        cv2.rectangle(frame,
                      (b["x"], b["y"]),
                      (b["x"] + b["w"], b["y"] + b["h"]),
                      color, thickness, cv2.LINE_AA)

    elif t == "circle":
        cv2.circle(frame,
                   (shape["cx"], shape["cy"]),
                   shape["r"],
                   color, thickness, cv2.LINE_AA)

    elif t == "line":
        cv2.line(frame,
                 tuple(map(int, shape["p1"])),
                 tuple(map(int, shape["p2"])),
                 color, thickness, cv2.LINE_AA)

    if label:
        x = shape.get("bbox", {}).get("x", shape.get("cx", shape.get("p1", [10])[0]))
        y = shape.get("bbox", {}).get("y", shape.get("cy", shape.get("p1", [0, 10])[1]))
        cv2.putText(frame, label, (int(x), int(y) - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1, cv2.LINE_AA)
