import asyncio
from ultralytics import YOLO
import cv2
import time
from PIL import ImageFont, ImageDraw, Image
import numpy as np
import torch

# ==== Config ====
MODEL_PATH = 'yolov8m-pose.pt'
CONFIDENCE_THRESHOLD = 0.15
LINE_SENSITIVITY = 120
CROSS_COOLDOWN = 0.1
FONT_PATH = 'C:/Windows/Fonts/msjh.ttc'
BRIGHTNESS_ALPHA = 1.2
BRIGHTNESS_BETA = 10
WINDOW_NAME = '手勢紅線偵測器 v6.9'

# ==== 裝置判斷 ====
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"🖥️ 使用裝置：{device.upper()} ({torch.cuda.get_device_name(0) if device == 'cuda' else 'CPU 執行'})")

# ==== 初始化 ====
model = YOLO(MODEL_PATH)
model.to(device)
cap = cv2.VideoCapture(0)

# ==== 狀態 ====
cross_count = {"total": 0, "left_to_right": 0, "right_to_left": 0}
in_zone, last_cross_time, prev_x = {}, {}, {}
tip_text = ""
tip_expire = 0

# ==== 功能函數 ====
def put_chinese_text(img, text, pos, font_size=36, color=(255, 255, 0)):
    try:
        font = ImageFont.truetype(FONT_PATH, font_size)
        img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil)
        draw.text(pos, text, font=font, fill=color)
        return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
    except Exception as e:
        print(f"中文字體載入失敗：{e}")
        return img

def draw_ui(frame, center_x):
    cv2.line(frame, (center_x, 0), (center_x, frame.shape[0]), (0, 0, 255), 2)
    frame = put_chinese_text(frame, f"總穿越次數：{cross_count['total']}", (10, 10), 30, (0, 0, 255))
    frame = put_chinese_text(frame, f"左 → 右：{cross_count['left_to_right']}", (10, 50), 28, (0, 255, 0))
    frame = put_chinese_text(frame, f"右 → 左：{cross_count['right_to_left']}", (10, 90), 28, (255, 0, 0))
    return frame

def get_direction(prev_x, curr_x, center_x):
    if prev_x < center_x <= curr_x:
        return "left_to_right"
    elif prev_x > center_x >= curr_x:
        return "right_to_left"
    return None

def process_joint(joint_idx, pts, confs, center_x, frame, now):
    global tip_text, tip_expire
    if joint_idx >= len(pts) or confs[joint_idx] < CONFIDENCE_THRESHOLD:
        return

    x, y = map(int, pts[joint_idx])
    key = joint_idx
    in_now = abs(x - center_x) <= LINE_SENSITIVITY
    was_in = in_zone.get(key, False)
    last_time = last_cross_time.get(key, 0)
    prev = prev_x.get(key, x)

    if not was_in and in_now and (now - last_time > CROSS_COOLDOWN):
        direction = get_direction(prev, x, center_x)
        if direction:
            cross_count["total"] += 1
            cross_count[direction] += 1
            last_cross_time[key] = now
            tip_text = "從左邊穿越！" if direction == "left_to_right" else "從右邊穿越！"
            tip_expire = now + 1
            print(f"關節 {key} 穿越紅線 ➜ {tip_text}")

    in_zone[key] = in_now
    prev_x[key] = x

    # 畫框與提示
    cv2.rectangle(frame, (x - 12, y - 12), (x + 12, y + 12), (0, 255, 0), 2)
    cv2.circle(frame, (x, y), 5, (0, 0, 255), -1)
    cv2.putText(frame, "✋", (x + 8, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

# 非同步包裝函式
async def process_joint_async(joint_idx, pts, confs, center_x, frame, now):
    process_joint(joint_idx, pts, confs, center_x, frame, now)

# 非同步任務：讀影像 + 偵測
async def capture_and_detect(queue):
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.convertScaleAbs(frame, alpha=BRIGHTNESS_ALPHA, beta=BRIGHTNESS_BETA)
        center_x = frame.shape[1] // 2
        now = time.time()

        results = model.predict(frame, save=False, conf=CONFIDENCE_THRESHOLD, device=device)
        annotated = results[0].plot()
        annotated = draw_ui(annotated, center_x)

        if len(results[0].keypoints.xy) > 0:
            pts = results[0].keypoints.xy[0]
            confs = results[0].keypoints.conf[0]

            tasks = [
                process_joint_async(point_idx, pts, confs, center_x, annotated, now)
                for point_idx in [7, 8, 9, 10]
            ]
            await asyncio.gather(*tasks)

        if tip_text and now < tip_expire:
            annotated = put_chinese_text(annotated, tip_text, (center_x - 100, 150), 42, (0, 255, 255))

        await queue.put(annotated)
        await asyncio.sleep(0)

# 非同步任務：顯示畫面
async def display(queue):
    while True:
        frame = await queue.get()
        cv2.imshow(WINDOW_NAME, frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()

# 主程式
async def main():
    queue = asyncio.Queue(maxsize=2)
    producer = asyncio.create_task(capture_and_detect(queue))
    consumer = asyncio.create_task(display(queue))
    await asyncio.gather(producer, consumer)

if __name__ == '__main__':
    asyncio.run(main())