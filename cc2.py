import cv2
import mediapipe as mp

# Mediapipe 設定
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_holistic = mp.solutions.holistic

# Pose 支點名稱對照表
pose_names = [
    "Nose", "Left Eye Inner", "Left Eye", "Left Eye Outer", "Right Eye Inner", "Right Eye", "Right Eye Outer",
    "Left Ear", "Right Ear", "Mouth Left", "Mouth Right", "Left Shoulder", "Right Shoulder", "Left Elbow", 
    "Right Elbow", "Left Wrist", "Right Wrist", "Left Pinky", "Right Pinky", "Left Index", "Right Index", 
    "Left Thumb", "Right Thumb", "Left Hip", "Right Hip", "Left Knee", "Right Knee", "Left Ankle", 
    "Right Ankle", "Left Heel", "Right Heel", "Left Foot Index", "Right Foot Index"
]

# 🔥 自動分類的函式
def get_body_part_type(index):
    if index in [13,14,15,16,17,18,19,20,21,22]:
        return "hand"
    elif index in [23,24,25,26,27,28,29,30,31,32]:
        return "leg"
    elif index in [0,1,2,3,4,5,6,7,8,9,10]:
        return "face"
    elif index in [11,12]:
        return "shoulder"
    else:
        return "torso"  # 頸部、胸部或其他未分類

# 開啟攝影機
cap = cv2.VideoCapture(0)

with mp_holistic.Holistic(
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5) as holistic:

    if not cap.isOpened():
        print("Cannot open camera")
        exit()

    while True:
        ret, img = cap.read()
        if not ret:
            print("Cannot receive frame")
            break

        img = cv2.resize(img, (520, 300))
        img2 = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = holistic.process(img2)

        img_h, img_w = img.shape[:2]

        # 畫臉部網格
        if results.face_landmarks:
            mp_drawing.draw_landmarks(
                img,
                results.face_landmarks,
                mp_holistic.FACEMESH_CONTOURS,
                landmark_drawing_spec=None,
                connection_drawing_spec=mp_drawing_styles.get_default_face_mesh_contours_style())

        # 畫身體骨架並印出支點名稱與座標
        if results.pose_landmarks:
            mp_drawing.draw_landmarks(
                img,
                results.pose_landmarks,
                mp_holistic.POSE_CONNECTIONS,
                landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style())

            for idx, lm in enumerate(results.pose_landmarks.landmark):
                cx, cy = int(lm.x * img_w), int(lm.y * img_h)
                part = pose_names[idx] if idx < len(pose_names) else f"Point {idx}"
                part_type = get_body_part_type(idx)

                # 標記畫面上的支點位置與編號
                cv2.circle(img, (cx, cy), 3, (0, 0, 255), -1)
                cv2.putText(img, f"{idx}", (cx, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)

                # 印出資訊到終端機
                print(f"[{part_type.upper()}] {part} (Point {idx}): x={lm.x:.3f}, y={lm.y:.3f}, z={lm.z:.3f}, vis={lm.visibility:.2f}")

        cv2.imshow('oxxostudio', img)
        if cv2.waitKey(5) == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()