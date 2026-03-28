"""
main.py — AirDraw AI entry point.
Integrates all phases (Tracking, Gestures, Drawing, Shapes, Objects, Interaction, UI).

Controls:
  Q — quit
  C — clear all
  D — toggle debug overlay
"""
import cv2
import time

from modules.camera         import Camera
from modules.hand_tracker   import HandTracker
from modules.gesture        import GestureClassifier
from modules.drawing        import DrawingEngine
from modules.object_store   import ObjectStore
from modules.interaction    import InteractionEngine
from modules.shape_detector import detect_shape
from modules.ui             import (
    ModeFlash, ToastManager, DeleteFlash,
    draw_hud, draw_gesture_label, draw_finger_cursor,
    draw_no_hand_prompt, draw_legend
)

# ── Constants ─────────────────────────────────────────────────────────────────
WIN_NAME = "AirDraw AI"
DEBUG    = False

# ── Environment ───────────────────────────────────────────────────────────────
def check_lighting(frame, toast: ToastManager):
    """Warn user if environment is too dark."""
    # very basic brightness check
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    mean_val = gray.mean()
    if mean_val < 40: # Quite dark
        toast.show("Warning: Low lighting!", (0, 0, 255))

def commit_drawing(drawing: DrawingEngine, store: ObjectStore, toast: ToastManager, force: bool = False):
    """Saves the current active stroke into the object store."""
    if drawing.is_drawing:
        pts = drawing.force_finalize_stroke() if force else drawing.try_finalize_stroke()
        if pts and len(pts) > 5:
            shape = detect_shape(pts)
            store.add("stroke", pts, shape)
            if shape:
                toast.show(f"Created {shape['type'].capitalize()}", (0, 255, 0))

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    global DEBUG

    # Initialize subsystems
    cam          = Camera(device_index=0)
    tracker      = HandTracker(max_num_hands=1, model_complexity=1)
    classifier   = GestureClassifier(buffer_size=5)
    
    drawing      = DrawingEngine()
    store        = ObjectStore()
    interaction  = InteractionEngine(store)
    
    flash_mode   = ModeFlash()
    toast        = ToastManager()
    flash_del    = DeleteFlash()

    cv2.namedWindow(WIN_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WIN_NAME, cam.width, cam.height)

    prev_time    = time.time()
    fps          = 0.0
    last_gesture = "IDLE"
    frame_count  = 0

    print("[Main] AirDraw AI starting...")

    while True:
        frame = cam.read_frame()
        if frame is None:
            continue
            
        frame_count += 1
        
        # Check lighting periodically
        if frame_count % 60 == 0:
            check_lighting(frame, toast)

        # ── 1. Hand Tracking & Gestures ──────────────────────────────────────
        landmarks = tracker.process(frame)
        gesture   = "IDLE"

        if landmarks:
            # Always draw skeleton tracking for better user feedback
            tracker.draw_landmarks(frame, landmarks)
                
            gesture = classifier.update(landmarks)
            flash_mode.on_gesture(gesture)
        else:
            classifier.reset()
            commit_drawing(drawing, store, toast)
            interaction.release_pinch()
            interaction.release_palm()
            draw_no_hand_prompt(frame)

        # Index finger tip
        idx_tip = landmarks[8] if landmarks else None

        # ── 2. Interaction State Machine ─────────────────────────────────────
        if gesture == "DRAW" and idx_tip:
            # Cancel interactions
            interaction.release_pinch()
            interaction.release_palm()
            
            # Start/continue drawing
            if not drawing.is_drawing:
                drawing.start_stroke(idx_tip)
            else:
                drawing.add_point(idx_tip)
                
        elif gesture == "FIST" and landmarks:
            # Deal with completed drawing
            if classifier.frames_in_state("FIST") > 3:
                commit_drawing(drawing, store, toast, force=True)
                    
            # Update fist grab/drag
            interaction.release_palm()
            
            # center of fist using knuckles
            px = int(sum(landmarks[i][0] for i in [5, 9, 13, 17]) / 4)
            py = int(sum(landmarks[i][1] for i in [5, 9, 13, 17]) / 4)

            interaction.update_pinch(px, py)
            
        elif gesture == "V_SIGN":
            commit_drawing(drawing, store, toast, force=True)
            interaction.release_pinch()
            interaction.release_palm()
            
        elif gesture == "PALM" and idx_tip:
            # Deal with completed drawing
            commit_drawing(drawing, store, toast)
                    
            # Update palm hold to delete
            interaction.release_pinch()
            # average of all landmarks for palm center roughly
            px = int(sum(pt[0] for pt in landmarks) / len(landmarks))
            py = int(sum(pt[1] for pt in landmarks) / len(landmarks))
            
            deleted = interaction.update_palm(px, py)
            if deleted:
                toast.show("Deleted object", (0, 0, 255))
                flash_del.trigger()
                
        elif gesture == "IDLE":
            # do nothing – keep stroke alive
            pass
        else:
            commit_drawing(drawing, store, toast)
            interaction.release_pinch()
            interaction.release_palm()

        # ── 3. Rendering ─────────────────────────────────────────────────────
        # Render stored objects
        selected = interaction.grabbed_members()
        store.render(frame, debug=DEBUG, selected_ids=selected)
        
        # Render active drawing
        drawing.render_active(frame)
        
        # Render interaction cursors/progress
        if gesture == "FIST" and landmarks:
            px = int(sum(landmarks[i][0] for i in [5, 9, 13, 17]) / 4)
            py = int(sum(landmarks[i][1] for i in [5, 9, 13, 17]) / 4)
            interaction.render_grab_cursor(frame, px, py)
        if gesture == "PALM":
            interaction.render_delete_arc(frame)
            
        # Draw base finger cursor
        if idx_tip:
            draw_finger_cursor(frame, landmarks, gesture)

        # UI Overlays
        flash_del.render(frame)
        flash_mode.render(frame)
        toast.render(frame)
        draw_legend(frame)
        draw_gesture_label(frame, gesture)
        
        now       = time.time()
        fps       = 0.9 * fps + 0.1 * (1.0 / (now - prev_time + 1e-9))
        prev_time = now
        draw_hud(frame, fps, store.count(), DEBUG)

        # ── 4. Final compositing ─────────────────────────────────────────────
        cv2.imshow(WIN_NAME, frame)

        # ── Key handling ─────────────────────────────────────────────────────
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('d'):
            DEBUG = not DEBUG
        elif key == ord('c'):
            # Clear all
            for obj in store.get_all():
                store.remove(obj["id"])
            toast.show("Canvas cleared", (255, 255, 255))

    # ── Cleanup ──────────────────────────────────────────────────────────────
    tracker.close()
    cam.release()
    cv2.destroyAllWindows()
    print("[Main] Exited cleanly.")


if __name__ == "__main__":
    main()
