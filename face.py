from flask import Flask, request, jsonify, render_template_string
import os
import cv2
from ultralytics import YOLO

app = Flask(__name__)

# ==== 設定參數 ====
SAVE_DIR = "static/registered_faces"
model = YOLO("./yolov8-face.pt")
os.makedirs(SAVE_DIR, exist_ok=True)

HTML_FORM = """
<!DOCTYPE html>
<html>
<head><title>註冊臉部</title></head>
<body>
  <h2>人臉註冊系統</h2>
  <form method="POST" action="/register">
    姓名: <input type="text" name="name" required>
    <input type="submit" value="立即註冊">
  </form>
  <h4>{{ message }}</h4>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML_FORM, message="")

@app.route("/register", methods=["POST"])
def register():
    name = request.form.get("name") or (request.json.get("name") if request.is_json else None)
    is_api = request.content_type == 'application/json'

    if not name:
        message = "❌ 請輸入姓名"
        if is_api:
            return jsonify({"status": "error", "message": message}), 400
        return render_template_string(HTML_FORM, message=message)

    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        message = "❌ 無法取得影像"
        if is_api:
            return jsonify({"status": "fail", "message": message}), 500
        return render_template_string(HTML_FORM, message=message)

    results = model(frame)
    face_saved = False

    for result in results:
        boxes = result.boxes.xyxy.cpu().numpy()
        for box in boxes:
            x1, y1, x2, y2 = map(int, box)
            face_crop = frame[y1:y2, x1:x2]
            filename = os.path.join(SAVE_DIR, f"{name}.jpg")
            cv2.imwrite(filename, face_crop)
            face_saved = True
            print(f"✅ 已註冊：{filename}")
            break
        if face_saved:
            break

    cv2.destroyAllWindows()

    if face_saved:
        message = f"✅ 已註冊 {name}！"
        if is_api:
            return jsonify({"status": "success", "name": name, "path": f"{SAVE_DIR}/{name}.jpg"}), 200
        return render_template_string(HTML_FORM, message=message)
    else:
        message = "❌ 未偵測到任何人臉"
        if is_api:
            return jsonify({"status": "fail", "message": message}), 404
        return render_template_string(HTML_FORM, message=message)

if __name__ == "__main__":
    app.run(debug=True)