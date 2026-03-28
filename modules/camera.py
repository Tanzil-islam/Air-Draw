"""
camera.py — Phase 1
Webcam capture with frame mirroring.
"""
import cv2


class Camera:
    def __init__(self, device_index: int = 0, width: int = 1280, height: int = 720):
        self.cap = cv2.VideoCapture(device_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open webcam at index {device_index}.")

        # Read actual resolution (may differ from requested)
        self.width  = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"[Camera] Opened: {self.width}x{self.height}")

    def read_frame(self):
        """Return a mirrored BGR frame, or None on failure."""
        ret, frame = self.cap.read()
        if not ret:
            return None
        return cv2.flip(frame, 1)   # Mirror horizontally

    def release(self):
        self.cap.release()
