# 🗺️ AirDraw AI — Phased Execution Plan

> Based on: `prd.md` | Stack: **Python · OpenCV · MediaPipe · NumPy**

---

## 📁 Project File Structure

```
Air-Draw/
├── prd.md
├── PHASES.md                  ← This file
├── main.py                    ← Entry point / app loop
├── modules/
│   ├── camera.py              ← Webcam capture + frame management
│   ├── hand_tracker.py        ← MediaPipe hands integration
│   ├── gesture.py             ← Gesture classification logic
│   ├── drawing.py             ← Stroke capture + rendering
│   ├── shape_detector.py      ← Closed loop → shape recognition
│   ├── object_store.py        ← Object state, bounding boxes, groups
│   ├── interaction.py         ← Grab/move + delete logic
│   └── ui.py                  ← HUD overlays, color themes
├── utils/
│   ├── geometry.py            ← BBox intersection, point math helpers
│   └── smoothing.py           ← Rolling average, interpolation
└── assets/
    └── (optional icons/fonts)
```

---

## ✅ Phase Overview

| Phase | Name | Features | Est. Time |
|-------|------|----------|-----------|
| **0** | Environment Setup | Python env, dependencies, webcam test | ~30 min |
| **1** | Hand Tracking Core | Camera loop, MediaPipe, landmark overlay | ~1–2 hr |
| **2** | Gesture Recognition | Draw / Pinch / Palm / Idle classifier | ~1–2 hr |
| **3** | Air Drawing Engine | Stroke capture, rendering, persistence | ~2–3 hr |
| **4** | Shape Detection | Closed shape → rectangle snap | ~2 hr |
| **5** | Object Store | Object state, bounding boxes, IDs | ~1–2 hr |
| **6** | Object Grouping | Intersection logic, group IDs (Union-Find) | ~2 hr |
| **7** | Grab & Move | Pinch-to-select, drag with hand | ~2 hr |
| **8** | Delete Gesture | Palm hold → confirm → remove object | ~1–2 hr |
| **9** | Visual Polish | HUD, colors, animations, cursor dot | ~2–3 hr |
| **10** | Optimization | FPS tuning, memory, edge cases | ~2 hr |

---

## 🔧 Phase 0 — Environment Setup

**Goal**: Confirm Python environment works and all dependencies install cleanly.

### Tasks
- [ ] **0.1** Create virtual environment: `python -m venv venv`
- [ ] **0.2** Install dependencies:
  ```
  pip install opencv-python mediapipe numpy
  ```
- [ ] **0.3** Write `requirements.txt`
- [ ] **0.4** Create minimal test script `test_cam.py` — opens webcam and shows live feed
- [ ] **0.5** Verify MediaPipe imports without error

### ✅ Done When
- Webcam opens and shows live feed at ≥ 20 FPS
- No import errors

---

## 📸 Phase 1 — Hand Tracking Core

**Files**: `main.py`, `modules/camera.py`, `modules/hand_tracker.py`

**Goal**: Real-time webcam feed with 21 hand landmarks drawn on screen.

### Tasks
- [ ] **1.1** `camera.py` — wrap `cv2.VideoCapture(0)`, expose `read_frame()` returning a mirrored BGR frame
- [ ] **1.2** `hand_tracker.py` — initialize `mp.solutions.hands.Hands()` with:
  - `max_num_hands=1`
  - `model_complexity=1`
  - `min_detection_confidence=0.7`
  - `min_tracking_confidence=0.5`
- [ ] **1.3** `hand_tracker.py` — expose `process(frame)` returning landmark list (21 points each as `(x, y)` in pixel coords)
- [ ] **1.4** `main.py` — main loop: read frame → track → draw landmarks → `cv2.imshow`
- [ ] **1.5** Draw landmark connections using `mp.solutions.drawing_utils`
- [ ] **1.6** Show FPS counter in top-left corner (calculate from `time.time()` delta)

### Key Landmarks Used

| Index | Landmark | Used For |
|-------|----------|----------|
| 4 | Thumb tip | Pinch detection |
| 6 | Index PIP | Finger-up check |
| 8 | Index tip | Draw position |
| 10  | Middle PIP | Finger-up check |
| 12 | Middle tip | Gesture classification |
| 16 | Ring tip | Palm detection |
| 20 | Pinky tip | Palm detection |

### ✅ Done When
- Landmarks appear accurately on hand in real-time
- FPS ≥ 20 displayed in corner
- Works when hand is partially off-screen (no crash)

---

## 🤚 Phase 2 — Gesture Recognition

**Files**: `modules/gesture.py`, `utils/smoothing.py`

**Goal**: Reliably classify the current hand state into one of 4 modes.

### Gestures to Detect

| Gesture | Condition | Result |
|---------|-----------|--------|
| `DRAW` | Index tip (8) above Index PIP (6) AND middle tip (12) below middle PIP (10) | Drawing mode ON |
| `IDLE` | Index tip (8) below Index PIP (6) | Drawing mode OFF |
| `PINCH` | Distance(thumb tip 4, index tip 8) < 40px | Grab mode |
| `PALM` | All 5 fingertips above their PIP joints | Delete mode |

### Tasks
- [ ] **2.1** `gesture.py` — `classify(landmarks) → str` function returning `"DRAW"`, `"IDLE"`, `"PINCH"`, or `"PALM"`
- [ ] **2.2** Implement **is_finger_up(landmarks, finger_tip_idx, finger_pip_idx)** helper
- [ ] **2.3** Implement **pinch_distance(landmarks)** → pixel distance between pts 4 and 8
- [ ] **2.4** `smoothing.py` — `GestureBuffer(size=5)` class: store last N gestures, return most frequent (majority vote) to prevent flickering
- [ ] **2.5** Integrate buffer into main loop
- [ ] **2.6** Display current gesture as text on screen (debug mode toggle with `D` key)

### ✅ Done When
- Each gesture reliably triggers with < 2 frames of lag
- No rapid flickering between states
- Debug overlay shows correct gesture label

---

## ✏️ Phase 3 — Air Drawing Engine

**Files**: `modules/drawing.py`, `utils/geometry.py`

**Goal**: Index finger tip leaves persistent colored strokes on canvas.

### Tasks
- [ ] **3.1** `drawing.py` — maintain `current_stroke: list[tuple]` and `completed_strokes: list[list[tuple]]`
- [ ] **3.2** Each frame in DRAW mode: append `(x, y)` of landmark 8 to `current_stroke`
- [ ] **3.3** On gesture change away from DRAW: finalize stroke — push to `completed_strokes`, reset `current_stroke`
- [ ] **3.4** `render(frame)` — draw all completed strokes + current in-progress stroke using `cv2.polylines()`
- [ ] **3.5** Style:
  - Active stroke: cyan `(255, 255, 0)` in BGR, thickness=3, with glow (draw thicker blurred copy first)
  - Completed strokes: white `(200, 200, 200)`, thickness=2
- [ ] **3.6** `utils/geometry.py` — `interpolate_points(p1, p2, max_gap=10)` inserts intermediate points if distance > threshold (prevents gaps on fast movement)
- [ ] **3.7** Apply interpolation on each new point added

### ✅ Done When
- Drawing a slow curve produces a smooth, continuous line
- Fast movement produces no visible gaps
- Strokes persist after lifting finger

---

## 🔲 Phase 4 — Shape Detection (Rectangle MVP)

**Files**: `modules/shape_detector.py`, `utils/geometry.py`

**Goal**: When a stroke forms a rough closed rectangle, snap it to a clean rectangle object.

### Tasks
- [ ] **4.1** `shape_detector.py` — `is_closed(stroke, threshold=40) → bool`: check if distance between first and last point < threshold
- [ ] **4.2** `simplify_stroke(stroke, epsilon=5) → list[tuple]`: implement **Ramer–Douglas–Peucker** (RDP) algorithm to reduce points to key vertices
- [ ] **4.3** `detect_rectangle(simplified_pts) → bbox | None`: if 4 vertices remain after simplification AND all corner angles are ~90° (±25°), return bounding box `{x, y, w, h}`
- [ ] **4.4** On stroke finalization: run detection pipeline → if rectangle detected, replace raw stroke with a clean rectangle
- [ ] **4.5** Render detected rectangles with `cv2.rectangle()` using a distinct color (green)
- [ ] **4.6** Brief label flash — show `"Rectangle"` text near the detected shape for 60 frames

### ✅ Done When
- Drawing a rough box auto-snaps to a clean rectangle
- Open/irregular strokes are left as freehand
- Rectangle label briefly appears on detection

---

## 🗃️ Phase 5 — Object Store

**Files**: `modules/object_store.py`

**Goal**: All drawn strokes and shapes are stored as discrete objects with unique IDs and bounding boxes.

### Tasks
- [ ] **5.1** `ObjectStore` class with internal dict `{id: object}`
- [ ] **5.2** Object schema:
  ```python
  {
    "id": str,         # uuid4
    "type": str,       # "stroke" | "rectangle" | "circle"
    "points": list,    # raw points
    "bbox": dict,      # {x, y, w, h}
    "group_id": str,   # None or group uuid
    "color": tuple,    # BGR
    "z_index": int,
    "visible": bool
  }
  ```
- [ ] **5.3** Methods: `add(obj)`, `remove(id)`, `get_all()`, `find_at_point(x, y) → id | None`, `update_bbox(id)`,  `get_group(group_id) → list`
- [ ] **5.4** `find_at_point` — returns object whose bounding box contains `(x,y)`, highest z_index wins
- [ ] **5.5** `utils/geometry.py` — `bbox_intersects(a, b) → bool`
- [ ] **5.6** Render all objects from store (replace direct rendering in Phase 3)

### ✅ Done When
- Every stroke/shape lands in the store
- Objects can be individually identified by clicking (test with mouse for now)
- Bounding boxes render as dashed overlays (debug mode)

---

## 🔗 Phase 6 — Object Grouping

**Files**: `modules/object_store.py` (extend), `utils/geometry.py` (extend)

**Goal**: When a new drawing overlaps an existing object, they share a group ID and are treated as a unit.

### Tasks
- [ ] **6.1** Implement **Union-Find** (Disjoint Set Union) in `utils/geometry.py` for efficient group merging
- [ ] **6.2** After each new object is added to store: check all existing objects for bounding box intersection
- [ ] **6.3** If intersection found:
  - Assign same `group_id` to both objects
  - If intersecting object already in a group → merge the two groups
- [ ] **6.4** `get_group_bbox(group_id)` — return union bounding box of all members
- [ ] **6.5** Render a semi-transparent filled rect around each group using group's shared color
- [ ] **6.6** Assign each group a unique pastel color from a curated palette

### Edge Cases
- [ ] **6.7** Test: drawing that touches 2 separate groups → merges all three into one

### ✅ Done When
- Drawing that overlaps another auto-groups them
- Group bounding box visually wraps all members
- Merging across multiple groups works correctly

---

## 🤏 Phase 7 — Grab & Move (Pinch Gesture)

**Files**: `modules/interaction.py`

**Goal**: Pinching near an object selects it (or its group) and lets the user drag it with their hand.

### Tasks
- [ ] **7.1** `interaction.py` — state machine: `IDLE → SELECTING → DRAGGING → IDLE`
- [ ] **7.2** On PINCH gesture start: call `object_store.find_at_point(pinch_x, pinch_y)` → store `selected_id`
- [ ] **7.3** If `selected_id` is in a group → select entire group
- [ ] **7.4** Each frame while PINCH:
  - Calculate delta: `(current_pinch_x - last_pinch_x, current_pinch_y - last_pinch_y)`
  - Apply delta to all points of selected object(s)
  - Update bounding boxes
- [ ] **7.5** Apply **lerp smoothing**: `display_pos = lerp(display_pos, actual_pos, 0.35)` per frame for smooth drag feel
- [ ] **7.6** Visual: selected object glows brighter; show pinch-cursor icon (small circle with cross)
- [ ] **7.7** On PINCH release → deselect, clear state

### ✅ Done When
- Pinching near an object highlights it
- Moving hand drags the object smoothly
- Grouped objects move together
- Releasing pinch drops object in new position

---

## ✋ Phase 8 — Delete Gesture (Palm Hold)

**Files**: `modules/interaction.py` (extend)

**Goal**: Holding an open palm over an object for 1 second deletes it with visual confirmation.

### Tasks
- [ ] **8.1** On PALM gesture: find the object under palm center (avg of all landmark coords)
- [ ] **8.2** Start a `delete_timer` (0 → 1.0 seconds) while palm stays over same object
- [ ] **8.3** If palm moves off object → reset timer
- [ ] **8.4** Render a **radial progress arc** around palm center using `cv2.ellipse()`, filling proportionally with timer progress
- [ ] **8.5** At timer = 1.0s: call `object_store.remove(id)` (or remove entire group if grouped)
- [ ] **8.6** On deletion: play a brief **flash animation** — white overlay fading over 10 frames
- [ ] **8.7** If object is a group member → confirm with user (via on-screen prompt): "Delete group? [Yes=hold / No=move away]"

### ✅ Done When
- Palm over object shows a progress arc
- After 1 second, object is removed with a flash
- Moving palm away cancels deletion cleanly

---

## 🎨 Phase 9 — Visual Polish & HUD

**Files**: `modules/ui.py`, `main.py`

**Goal**: The app looks premium — dark themed, glowing strokes, clear gesture indicators, smooth feel.

### Tasks
- [ ] **9.1** **Background**: pure black canvas `(0, 0, 0)` composited over webcam feed at ~30% opacity (`cv2.addWeighted`)
- [ ] **9.2** **HUD Panel** (top-left):
  - Current mode: icon emoji + label + color-coded border
  - FPS counter
  - Object count / Group count
- [ ] **9.3** **Finger Cursor Dot**: glowing filled circle at landmark 8
  - DRAW → cyan
  - PINCH → yellow
  - PALM → red
  - IDLE → dim white
- [ ] **9.4** **Gesture Legend** (bottom): small semi-transparent strip showing all 4 gestures with icons
- [ ] **9.5** **Mode Flash**: large centered text briefly shows when gesture changes (fade in/out over 30 frames)
- [ ] **9.6** **Glow Effect**: simulate glow by drawing each stroke twice — once thick+blurred then sharp on top (`cv2.GaussianBlur`)
- [ ] **9.7** Keyboard shortcut: `Q` = quit, `C` = clear all, `D` = toggle debug bounding boxes

### Color Palette
| Role | BGR Color |
|------|-----------|
| Active stroke | `(255, 230, 0)` (cyan-yellow) |
| Complete stroke | `(200, 200, 200)` |
| Rectangle snap | `(0, 255, 150)` |
| Group highlight | `(180, 100, 255)` |
| Delete warning | `(0, 60, 255)` |
| Pinch cursor | `(0, 230, 255)` |

### ✅ Done When
- App looks visually impressive at first glance
- HUD is always readable without blocking drawing area
- Gesture transitions feel smooth

---

## ⚡ Phase 10 — Optimization & Edge Cases

**Files**: All modules

**Goal**: Stable ≥ 20 FPS, handles edge cases from PRD section 9.

### Tasks
- [ ] **10.1** **Multi-hand guard**: if `results.multi_hand_landmarks` has > 1 hand, use only the one with highest landmark confidence
- [ ] **10.2** **False pinch smoothing**: require pinch distance < threshold for 3 consecutive frames before triggering
- [ ] **10.3** **Z-index handling**: clicking overlapping objects selects the topmost (highest z_index); each new object increments z_index
- [ ] **10.4** **Fast movement interpolation**: already done in Phase 3 — verify works under fast swings
- [ ] **10.5** **FPS monitor**: if FPS < 20, dynamically set `model_complexity=0`
- [ ] **10.6** **Memory**: cap each stroke at 500 points max (downsample older points)
- [ ] **10.7** **No hand detected**: show gentle "Show your hand 👋" prompt
- [ ] **10.8** **Lighting warning**: if frame is too dark (avg brightness < 50), show lighting warning overlay

### ✅ Done When
- App runs at ≥ 20 FPS with 15+ objects on screen
- No crashes during 10-minute stress test session
- All PRD edge cases addressed

---

## 🏁 Final Checklist (vs PRD Requirements)

| Requirement | Phase | Status |
|-------------|-------|--------|
| FR1: Real-time hand tracking | 1 | ⬜ |
| FR2: Air drawing | 3 | ⬜ |
| FR3: Shape recognition (rectangle) | 4 | ⬜ |
| FR4: Object grouping | 6 | ⬜ |
| FR5: Pinch grab & move | 7 | ⬜ |
| FR6: Palm delete | 8 | ⬜ |
| NFR: Latency < 100ms | 10 | ⬜ |
| NFR: FPS ≥ 20 | 10 | ⬜ |
| NFR: Laptop webcam compatible | 0 | ⬜ |
| Visual feedback & HUD | 9 | ⬜ |

---

## 🚀 Suggested Execution Order

```
Phase 0 → 1 → 2 → 3 → 5 → 4 → 6 → 7 → 8 → 9 → 10
```
> Phases 4 (shape detection) and 5 (object store) can be swapped — implementing the store first makes shape integration cleaner.
