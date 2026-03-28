"""
geometry.py — Shared geometry helpers.
Used by drawing, shape detection, object store, and grouping.
"""
import math
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Point / distance helpers
# ─────────────────────────────────────────────────────────────────────────────

def distance(p1: tuple, p2: tuple) -> float:
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def lerp_point(p1: tuple, p2: tuple, t: float) -> tuple:
    return (lerp(p1[0], p2[0], t), lerp(p1[1], p2[1], t))


def midpoint(p1: tuple, p2: tuple) -> tuple:
    return ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)


def angle_between(p1: tuple, vertex: tuple, p2: tuple) -> float:
    """Angle at `vertex` formed by the vectors vertex→p1 and vertex→p2 (degrees)."""
    v1 = (p1[0] - vertex[0], p1[1] - vertex[1])
    v2 = (p2[0] - vertex[0], p2[1] - vertex[1])
    dot   = v1[0]*v2[0] + v1[1]*v2[1]
    mag1  = math.hypot(*v1)
    mag2  = math.hypot(*v2)
    if mag1 < 1e-9 or mag2 < 1e-9:
        return 0.0
    cos_a = max(-1.0, min(1.0, dot / (mag1 * mag2)))
    return math.degrees(math.acos(cos_a))


# ─────────────────────────────────────────────────────────────────────────────
# Interpolation
# ─────────────────────────────────────────────────────────────────────────────

def interpolate_points(p1: tuple, p2: tuple, max_gap: int = 10) -> list[tuple]:
    """
    Return intermediate integer pixel points between p1 and p2
    if their distance exceeds max_gap. Prevents gaps on fast movement.
    """
    dist = distance(p1, p2)
    if dist <= max_gap:
        return [p2]
    steps = int(dist / max_gap)
    pts   = []
    for i in range(1, steps + 1):
        t = i / steps
        pts.append((int(lerp(p1[0], p2[0], t)), int(lerp(p1[1], p2[1], t))))
    return pts


# ─────────────────────────────────────────────────────────────────────────────
# Bounding box
# ─────────────────────────────────────────────────────────────────────────────

def compute_bbox(points: list[tuple]) -> Optional[dict]:
    """Return {x, y, w, h} bounding box from a list of (x, y) points."""
    if not points:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    x, y = int(min(xs)), int(min(ys))
    w, h = int(max(xs)) - x, int(max(ys)) - y
    return {"x": x, "y": y, "w": max(w, 1), "h": max(h, 1)}


def bbox_intersects(a: dict, b: dict, padding: int = 5) -> bool:
    """True if two {x,y,w,h} bboxes overlap (with optional padding)."""
    return not (
        a["x"] + a["w"] + padding < b["x"] or
        b["x"] + b["w"] + padding < a["x"] or
        a["y"] + a["h"] + padding < b["y"] or
        b["y"] + b["h"] + padding < a["y"]
    )


def bbox_union(a: dict, b: dict) -> dict:
    """Return the union bounding box of two {x,y,w,h} bboxes."""
    x = min(a["x"], b["x"])
    y = min(a["y"], b["y"])
    x2 = max(a["x"] + a["w"], b["x"] + b["w"])
    y2 = max(a["y"] + a["h"], b["y"] + b["h"])
    return {"x": x, "y": y, "w": x2 - x, "h": y2 - y}


def point_in_bbox(px: int, py: int, bbox: dict, padding: int = 10) -> bool:
    """True if point (px, py) is inside bbox (with optional padding)."""
    return (
        bbox["x"] - padding <= px <= bbox["x"] + bbox["w"] + padding and
        bbox["y"] - padding <= py <= bbox["y"] + bbox["h"] + padding
    )


# ─────────────────────────────────────────────────────────────────────────────
# Ramer–Douglas–Peucker simplification
# ─────────────────────────────────────────────────────────────────────────────

def _perpendicular_distance(pt: tuple, line_start: tuple, line_end: tuple) -> float:
    """Perpendicular distance from pt to the line segment start→end."""
    dx = line_end[0] - line_start[0]
    dy = line_end[1] - line_start[1]
    if dx == 0 and dy == 0:
        return distance(pt, line_start)
    t = ((pt[0] - line_start[0]) * dx + (pt[1] - line_start[1]) * dy) / (dx*dx + dy*dy)
    t = max(0.0, min(1.0, t))
    closest = (line_start[0] + t*dx, line_start[1] + t*dy)
    return distance(pt, closest)


def rdp_simplify(points: list[tuple], epsilon: float = 5.0) -> list[tuple]:
    """Ramer–Douglas–Peucker point-cloud simplification."""
    if len(points) < 3:
        return points
    max_dist  = 0.0
    max_index = 0
    end = len(points) - 1
    for i in range(1, end):
        d = _perpendicular_distance(points[i], points[0], points[end])
        if d > max_dist:
            max_dist  = d
            max_index = i
    if max_dist > epsilon:
        left  = rdp_simplify(points[:max_index + 1], epsilon)
        right = rdp_simplify(points[max_index:], epsilon)
        return left[:-1] + right
    return [points[0], points[end]]
