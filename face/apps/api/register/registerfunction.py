from db import get_db_connection
from facepro import model, REGISTERED_DIR
from utils import request, cv2, base64, np, os
def register_f():
        name = request.form.get("name") or (request.json.get("name") if request.is_json else None)
        file = request.files.get("photo")
        img = None

        if not name:
            return{"status": "fail", "message": "❌ 缺少姓名"}

        # 嘗試讀取圖像（支援檔案或 base64）
        if file:
            nparr = np.frombuffer(file.read(), np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        elif request.is_json and "image" in request.json:
            try:
                _, encoded = request.json["image"].split(",", 1)
                img_bytes = base64.b64decode(encoded)
                img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
            except:
                return{"status": "fail", "message": "❌ 圖片解碼錯誤"}

        if img is None:
            return{"status": "fail", "message": "❌ 未提供圖片"}

        # 使用 YOLO 偵測人臉
        results = model(img)
        face_crop = None
        face_count = 0

        for result in results:
            boxes = result.boxes.xyxy.cpu().numpy()
            face_count = len(boxes)

            # 判斷是否只有一張臉
            if face_count != 1:
                return{
                    "status": "fail",
                    "message": f"⚠️ 偵測到 {face_count} 張臉，請僅上傳一人照片"
                }

            # 只取第一張臉裁切
            x1, y1, x2, y2 = map(int, boxes[0])
            face_crop = img[y1:y2, x1:x2]
            break

        if face_crop is None:
            return{"status": "fail", "message": "❌ 未偵測到人臉"}

        # 檢查名稱是否重複並儲存資料
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE name=%s", (name,))
            if cur.fetchone():
                conn.close()
                return{"status": "fail", "message": f"⚠️ 使用者 {name} 已存在"}

            cur.execute("INSERT INTO users (name, image_path) VALUES (%s, '')", (name,))
            user_id = cur.lastrowid
            img_path = os.path.join(REGISTERED_DIR, f"{user_id}.jpg")
            cv2.imwrite(img_path, face_crop)
            relative_path = f"static/registered_faces/{user_id}.jpg"
            cur.execute("UPDATE users SET image_path=%s WHERE id=%s", (relative_path, user_id))
        conn.commit()
        conn.close()

        return{"status": "success", "message": f"✅ 已註冊 {name}", "id": user_id}