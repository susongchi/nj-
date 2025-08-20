import cv2

# 讀取影片
cap = cv2.VideoCapture(0)

# 讓你用滑鼠選取目標物（第一次用手選）
ret, frame = cap.read()
bbox = cv2.selectROI("追蹤手", frame, False)

# 建立追蹤器
tracker = cv2.TrackerCSRT_create()
tracker.init(frame, bbox)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # 更新追蹤
    success, bbox = tracker.update(frame)

    if success:
        x, y, w, h = [int(v) for v in bbox]
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0,255,0), 2)
    else:
        cv2.putText(frame, "追蹤失敗", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)

    cv2.imshow("追蹤手", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()