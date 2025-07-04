from ultralytics import YOLO
import cv2

# 載入人臉模型
model = YOLO("yolov8n-face.pt")  # 或 yolov8m-face.pt

# 開啟攝影機
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # 偵測人臉
    results = model(frame)

    # 畫出人臉方框 + 關鍵點
    for result in results:
        boxes = result.boxes.xyxy.cpu().numpy()
        keypoints = result.keypoints.xy.cpu().numpy() if result.keypoints is not None else []

        for box in boxes:
            x1, y1, x2, y2 = map(int, box)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        for kp in keypoints:
            for x, y in kp:
                cv2.circle(frame, (int(x), int(y)), 2, (0, 0, 255), -1)

    cv2.imshow("YOLOv8 Face Detection", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()