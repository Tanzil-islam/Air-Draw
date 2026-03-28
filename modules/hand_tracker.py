"""
hand_tracker.py — Phase 1
MediaPipe Hands wrapper: returns 21 landmarks as pixel (x, y) tuples.
"""
import cv2
import mediapipe as mp
from mediapipe.framework.formats import landmark_pb2
from typing import Optional


class HandTracker:
    # All 21 landmark indices for reference
    WRIST           = 0
    THUMB_TIP       = 4
    INDEX_MCP       = 5
    INDEX_PIP       = 6
    INDEX_TIP       = 8
    MIDDLE_PIP      = 10
    MIDDLE_TIP      = 12
    RING_PIP        = 14
    RING_TIP        = 16
    PINKY_PIP       = 18
    PINKY_TIP       = 20

    def __init__(
        self,
        max_num_hands: int = 1,
        model_complexity: int = 1,
        min_detection_confidence: float = 0.7,
        min_tracking_confidence: float = 0.5,
    ):
        self.mp_hands    = mp.solutions.hands
        self.mp_draw     = mp.solutions.drawing_utils
        self.mp_styles   = mp.solutions.drawing_styles

        self.hands = self.mp_hands.Hands(
            max_num_hands=max_num_hands,
            model_complexity=model_complexity,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self._complexity = model_complexity
        print("[HandTracker] Initialized.")

    def process(self, frame) -> Optional[list[tuple[int, int]]]:
        """
        Process a BGR frame.
        Returns list of 21 (x, y) pixel tuples for the first detected hand,
        or None if no hand found.
        """
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self.hands.process(rgb)
        rgb.flags.writeable = True

        if not results.multi_hand_landmarks:
            return None

        # Pick first hand (already limited to max_num_hands=1)
        hand_lm = results.multi_hand_landmarks[0]
        landmarks = [(lm.x * w, lm.y * h) for lm in hand_lm.landmark]
        return landmarks

    def draw_landmarks(self, frame, landmarks: list[tuple[int, int]]):
        """Draw the 21-point skeleton onto the frame (in-place)."""
        h, w = frame.shape[:2]

        mp_landmark = landmark_pb2.NormalizedLandmarkList()

        for (px, py) in landmarks:
            lm = mp_landmark.landmark.add()
            lm.x = px / w
            lm.y = py / h
            lm.z = 0.0

        self.mp_draw.draw_landmarks(
            frame,
            mp_landmark,
            self.mp_hands.HAND_CONNECTIONS,
            self.mp_styles.get_default_hand_landmarks_style(),
            self.mp_styles.get_default_hand_connections_style(),
        )

    def set_complexity(self, level: int):
        """Dynamically adjust model complexity (0=fast, 1=balanced)."""
        if level != self._complexity:
            self._complexity = level
            self.hands.model_complexity = level  # type: ignore

    def close(self):
        self.hands.close()
