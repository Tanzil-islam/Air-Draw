"""
Phase 0 — Camera sanity test.
Run: python test_cam.py
Press Q to quit.
"""
import cv2
import time

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("[ERROR] Cannot open webcam. Check device index or permissions.")
    exit(1)

print("[OK] Webcam opened. Press Q to quit.")

prev_time = time.time()
while True:
    ret, frame = cap.read()
    if not ret:
        print("[ERROR] Failed to read frame.")
        break

    frame = cv2.flip(frame, 1)  # Mirror

    # FPS
    now = time.time()
    fps = 1.0 / (now - prev_time + 1e-9)
    prev_time = now

    cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    cv2.putText(frame, "Phase 0: Camera OK - Press Q to quit", (10, 65),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

    cv2.imshow("AirDraw AI - Camera Test", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print("[OK] Phase 0 complete.")
