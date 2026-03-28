"""
object_store.py — Phase 5
Central store for all drawn objects. Each object has a unique ID,
bounding box, group membership, z-index, and rendering metadata.
"""
import uuid
import cv2
import numpy as np
from utils.geometry  import compute_bbox, bbox_intersects, point_in_bbox
from modules.drawing import DrawingEngine

# ─────────────────────────────────────────────────────────────────────────────
# Colour palette for objects / groups (BGR)
# ─────────────────────────────────────────────────────────────────────────────
_PALETTE = [
    (255, 180,  80),   # warm orange
    ( 80, 220, 255),   # sky cyan
    (180,  80, 255),   # violet
    ( 80, 255, 160),   # mint green
    (255,  80, 160),   # pink
    (255, 230,  80),   # gold
    ( 80, 130, 255),   # periwinkle
    (160, 255,  80),   # lime
]
_palette_idx = 0

def _next_color() -> tuple:
    global _palette_idx
    c = _PALETTE[_palette_idx % len(_PALETTE)]
    _palette_idx += 1
    return c


# ─────────────────────────────────────────────────────────────────────────────
# Union-Find for group management
# ─────────────────────────────────────────────────────────────────────────────
class _UnionFind:
    def __init__(self):
        self._parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        self._parent.setdefault(x, x)
        if self._parent[x] != x:
            self._parent[x] = self.find(self._parent[x])  # path compression
        return self._parent[x]

    def union(self, x: str, y: str):
        rx, ry = self.find(x), self.find(y)
        if rx != ry:
            self._parent[ry] = rx

    def same(self, x: str, y: str) -> bool:
        return self.find(x) == self.find(y)

    def remove(self, x: str):
        self._parent.pop(x, None)


# ─────────────────────────────────────────────────────────────────────────────
# ObjectStore
# ─────────────────────────────────────────────────────────────────────────────
class ObjectStore:
    def __init__(self):
        self._objects:  dict[str, dict]  = {}   # id → object dict
        self._uf:       _UnionFind        = _UnionFind()
        self._z_counter: int              = 0
        self._group_colors: dict[str, tuple] = {}   # group_root → color
        self._label_timers: dict[str, int]   = {}   # id → frames remaining

    # ── CRUD ─────────────────────────────────────────────────────────────────

    def add(self, obj_type: str, points: list[tuple],
            shape: dict | None = None) -> str:
        """
        Add an object. Returns its new ID.
        `shape` is the output of shape_detector.detect_shape (or None).
        """
        oid   = str(uuid.uuid4())
        bbox  = self._shape_bbox(shape) if shape else compute_bbox(points)
        color = _next_color()

        self._objects[oid] = {
            "id":      oid,
            "type":    shape["type"] if shape else "stroke",
            "points":  list(points),
            "shape":   shape,           # raw shape dict (or None)
            "bbox":    bbox,
            "group":   None,            # group root id (from UF)
            "color":   color,
            "z":       self._z_counter,
            "visible": True,
        }
        self._z_counter += 1
        self._uf.find(oid)              # register in UF

        # Auto-group with all intersecting objects
        self._auto_group(oid)
        self._label_timers[oid] = 90   # show type label for 90 frames

        return oid

    def remove(self, oid: str):
        self._objects.pop(oid, None)
        self._label_timers.pop(oid, None)
        self._uf.remove(oid)

    def remove_group(self, oid: str):
        """Remove every object that shares oid's group."""
        root    = self._uf.find(oid)
        victims = [k for k in self._objects if self._uf.find(k) == root]
        for v in victims:
            self.remove(v)

    def get_all(self) -> list[dict]:
        return sorted(self._objects.values(), key=lambda o: o["z"])

    def count(self) -> int:
        return len(self._objects)

    # ── Lookup ───────────────────────────────────────────────────────────────

    def find_at_point(self, px: int, py: int, padding: int = 40) -> str | None:
        """Return the topmost (highest z) object whose bbox contains (px,py)."""
        hits = [
            o for o in self._objects.values()
            if o["bbox"] and point_in_bbox(px, py, o["bbox"], padding)
        ]
        if not hits:
            return None
        return max(hits, key=lambda o: o["z"])["id"]

    def get_group_members(self, oid: str) -> list[str]:
        """Return all object IDs that share the same group as oid."""
        root = self._uf.find(oid)
        return [k for k in self._objects if self._uf.find(k) == root]

    # ── Move ─────────────────────────────────────────────────────────────────

    def move_object(self, oid: str, dx: int, dy: int):
        obj = self._objects.get(oid)
        if not obj:
            return
        obj["points"] = [(p[0]+dx, p[1]+dy) for p in obj["points"]]
        # Update shape geometry
        if obj["shape"]:
            s = obj["shape"]
            if s["type"] == "rectangle" and "bbox" in s:
                s["bbox"]["x"] += dx
                s["bbox"]["y"] += dy
            elif s["type"] == "circle":
                s["cx"] += dx
                s["cy"] += dy
            elif s["type"] == "line":
                s["p1"] = (s["p1"][0]+dx, s["p1"][1]+dy)
                s["p2"] = (s["p2"][0]+dx, s["p2"][1]+dy)
        obj["bbox"] = self._shape_bbox(obj["shape"]) if obj["shape"] else compute_bbox(obj["points"])

    def move_group(self, oid: str, dx: int, dy: int):
        for mid in self.get_group_members(oid):
            self.move_object(mid, dx, dy)

    # ── Grouping ─────────────────────────────────────────────────────────────

    def _auto_group(self, new_id: str):
        new_bbox = self._objects[new_id]["bbox"]
        if not new_bbox:
            return
        for oid, obj in self._objects.items():
            if oid == new_id or not obj["bbox"]:
                continue
            if bbox_intersects(new_bbox, obj["bbox"]):
                self._uf.union(new_id, oid)

        # Assign group color
        root = self._uf.find(new_id)
        if root not in self._group_colors:
            self._group_colors[root] = self._objects[root]["color"]
        # Propagate group color to all members
        for mid in self.get_group_members(new_id):
            self._objects[mid]["group"] = root

    def get_group_bbox(self, oid: str) -> dict | None:
        """Union bbox of all group members."""
        members = self.get_group_members(oid)
        bboxes  = [self._objects[m]["bbox"] for m in members
                   if self._objects[m]["bbox"]]
        if not bboxes:
            return None
        x  = min(b["x"] for b in bboxes)
        y  = min(b["y"] for b in bboxes)
        x2 = max(b["x"] + b["w"] for b in bboxes)
        y2 = max(b["y"] + b["h"] for b in bboxes)
        return {"x": x, "y": y, "w": x2-x, "h": y2-y}

    def group_color(self, oid: str) -> tuple:
        root = self._uf.find(oid)
        return self._group_colors.get(root, (200, 200, 200))

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _shape_bbox(shape: dict | None) -> dict | None:
        if not shape:
            return None
        t = shape["type"]
        if t == "rectangle":
            return shape["bbox"]
        elif t == "circle":
            r = shape["r"]
            return {"x": shape["cx"]-r, "y": shape["cy"]-r, "w": 2*r, "h": 2*r}
        elif t == "line":
            xs = [shape["p1"][0], shape["p2"][0]]
            ys = [shape["p1"][1], shape["p2"][1]]
            x, y = int(min(xs)), int(min(ys))
            return {"x": x, "y": y,
                    "w": int(max(max(xs)-x, 20)), "h": int(max(max(ys)-y, 20))}
        return None

    # ── Rendering ─────────────────────────────────────────────────────────────

    def render(self, frame, debug: bool = False, selected_ids: set | None = None):
        """Render all objects + group highlights onto frame."""
        from modules.shape_detector import render_shape
        from modules.drawing        import DrawingEngine

        selected_ids = selected_ids or set()
        rendered_groups: set[str] = set()

        for obj in self.get_all():
            if not obj["visible"]:
                continue

            oid   = obj["id"]
            color = self.group_color(oid)
            selected = oid in selected_ids
            thickness = 3 if selected else 2
            bright    = tuple(min(255, int(c * 1.5)) for c in color) if selected else color

            # Draw shape or stroke
            if obj["shape"]:
                lbl = obj["type"].capitalize() if self._label_timers.get(oid, 0) > 0 else None
                render_shape(frame, obj["shape"], bright, thickness, label=lbl)
            else:
                DrawingEngine.render_stroke(frame, obj["points"], bright, thickness)

            # Tick label timer
            if oid in self._label_timers:
                self._label_timers[oid] -= 1
                if self._label_timers[oid] <= 0:
                    del self._label_timers[oid]

            # Group bounding box (render once per group)
            root    = self._uf.find(oid)
            members = self.get_group_members(oid)
            if len(members) > 1 and root not in rendered_groups:
                rendered_groups.add(root)
                gbbox = self.get_group_bbox(oid)
                if gbbox:
                    gc = self._group_colors.get(root, (200, 200, 200))
                    pad = 10
                    overlay = frame.copy()
                    cv2.rectangle(overlay,
                                  (gbbox["x"]-pad, gbbox["y"]-pad),
                                  (gbbox["x"]+gbbox["w"]+pad, gbbox["y"]+gbbox["h"]+pad),
                                  gc, -1)
                    cv2.addWeighted(overlay, 0.08, frame, 0.92, 0, frame)
                    cv2.rectangle(frame,
                                  (gbbox["x"]-pad, gbbox["y"]-pad),
                                  (gbbox["x"]+gbbox["w"]+pad, gbbox["y"]+gbbox["h"]+pad),
                                  gc, 1, cv2.LINE_AA)

            # Debug: individual bboxes
            if debug and obj["bbox"]:
                b = obj["bbox"]
                cv2.rectangle(frame,
                              (b["x"], b["y"]),
                              (b["x"]+b["w"], b["y"]+b["h"]),
                              (60, 60, 60), 1)
