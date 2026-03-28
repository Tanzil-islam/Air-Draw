"""
smoothing.py — Phase 2
Rolling gesture buffer (majority vote) & linear interpolation helpers.
"""
from collections import deque
from typing import Any
import math


class GestureBuffer:
    """
    Stores the last `size` gesture strings.
    Returns the most-common one (majority vote) to reduce flickering.
    """
    def __init__(self, size: int = 5):
        self._buf  = deque(maxlen=size)
        self._size = size

    def update(self, gesture: str) -> str:
        self._buf.append(gesture)
        # Majority vote
        counts: dict[str, int] = {}
        for g in self._buf:
            counts[g] = counts.get(g, 0) + 1
        return max(counts, key=counts.get)   # type: ignore

    def clear(self):
        self._buf.clear()


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between a and b by factor t ∈ [0, 1]."""
    return a + (b - a) * t


def lerp_point(p1: tuple, p2: tuple, t: float) -> tuple:
    return (lerp(p1[0], p2[0], t), lerp(p1[1], p2[1], t))


def distance(p1: tuple, p2: tuple) -> float:
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])
