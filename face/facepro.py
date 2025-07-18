from flask import Flask, request, jsonify
import os
import cv2
import numpy as np
import base64
import face_recognition
import pymysql
from datetime import datetime
from ultralytics import YOLO
from flask_cors import CORS
from flask import session
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

app = Flask(__name__)
CORS(app, origins="*", supports_credentials=True)
app.secret_key = "su-song-chi_monkey14"
new_password = "su-song-chi_monkey14"
hashed = generate_password_hash(new_password)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REGISTERED_DIR = os.path.join(BASE_DIR, "static", "registered_faces")
BASE_IP = "127.0.0.1"
BASE_PORT = 5000
BASE_URL = "https://f3f0dd590a09.ngrok-free.app/api"
os.makedirs(REGISTERED_DIR, exist_ok=True)

model = YOLO("./yolov8-face.pt")

SIMILARITY_THRESHOLD = 0.5

def get_db_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="monkey14",
        database="face",
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def init_db():
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL,
                image_path VARCHAR(255)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS meetings (
                id INT AUTO_INCREMENT PRIMARY KEY,
                meeting_name VARCHAR(100) NOT NULL,
                time_start DATETIME NOT NULL,
                time_end DATETIME NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS meeting_name (
                id INT AUTO_INCREMENT PRIMARY KEY,
                meeting_id INT NOT NULL,
                user_id INT NOT NULL,
                FOREIGN KEY (meeting_id) REFERENCES meetings(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS login_records (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                login_time DATETIME NOT NULL,
                meeting_id INT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (meeting_id) REFERENCES meetings(id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS admin_users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL
            )
        """)
# 初始化 LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "/admin_login"
class AdminUser(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

    def get_id(self):
        return str(self.id)
@login_manager.user_loader
def load_user(user_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM admin_users WHERE id = %s", (user_id,))
            user = cur.fetchone()
            if user:
                return AdminUser(user["id"], user["username"])
    return None
@login_manager.unauthorized_handler
def unauthorized_callback():
    return jsonify({
        "status": "fail",
        "message": "❌ 尚未登入或登入已過期"
    }), 401
#=== 註冊功能 ===
@app.route("/register", methods=["POST"])
def register():
    name = request.form.get("name") or (request.json.get("name") if request.is_json else None)
    file = request.files.get("photo")
    img = None

    if not name:
        return jsonify({"status": "fail", "message": "❌ 缺少姓名"})

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
            return jsonify({"status": "fail", "message": "❌ 圖片解碼錯誤"})

    if img is None:
        return jsonify({"status": "fail", "message": "❌ 未提供圖片"})

    # 使用 YOLO 偵測人臉
    results = model(img)
    face_crop = None
    face_count = 0

    for result in results:
        boxes = result.boxes.xyxy.cpu().numpy()
        face_count = len(boxes)

        # 判斷是否只有一張臉
        if face_count != 1:
            return jsonify({
                "status": "fail",
                "message": f"⚠️ 偵測到 {face_count} 張臉，請僅上傳一人照片"
            })

        # 只取第一張臉裁切
        x1, y1, x2, y2 = map(int, boxes[0])
        face_crop = img[y1:y2, x1:x2]
        break

    if face_crop is None:
        return jsonify({"status": "fail", "message": "❌ 未偵測到人臉"})

    # 檢查名稱是否重複並儲存資料
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM users WHERE name=%s", (name,))
        if cur.fetchone():
            conn.close()
            return jsonify({"status": "fail", "message": f"⚠️ 使用者 {name} 已存在"})

        cur.execute("INSERT INTO users (name, image_path) VALUES (%s, '')", (name,))
        user_id = cur.lastrowid
        img_path = os.path.join(REGISTERED_DIR, f"{user_id}.jpg")
        cv2.imwrite(img_path, face_crop)
        relative_path = f"static/registered_faces/{user_id}.jpg"
        cur.execute("UPDATE users SET image_path=%s WHERE id=%s", (relative_path, user_id))
    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": f"✅ 已註冊 {name}", "id": user_id})
#=== 登入功能 ===
@app.route("/current_meeting")
def current_meeting():
    now = datetime.now()
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM meetings")
            for m in cur.fetchall():
                if m["time_start"] <= now <= m["time_end"]:
                    cur.execute("""
                        SELECT u.id, u.name FROM meeting_name mn
                        JOIN users u ON mn.user_id = u.id
                        WHERE mn.meeting_id = %s
                    """, (m["id"],))
                    users = cur.fetchall()
                    timeslot = f"{m['time_start'].strftime('%Y-%m-%d %H:%M')} - {m['time_end'].strftime('%H:%M')}"
                    return jsonify({
                        "status": "success",
                        "meeting_name": m["meeting_name"],
                        "timeslot": timeslot,
                        "users": users
                    })
    return jsonify({"status": "fail", "message": "目前無會議進行中"})

@app.route("/login_status")
def login_status():
    now = datetime.now()
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # 1️⃣ 找出目前進行中的會議
            cur.execute("SELECT * FROM meetings")
            meeting = None
            for m in cur.fetchall():
                if m["time_start"] <= now <= m["time_end"]:
                    meeting = m
                    break

            if not meeting:
                return jsonify({"status": "fail", "message": "無會議進行中"})

            meeting_id = meeting["id"]

            # 2️⃣ 取得與會者名單
            cur.execute("""
                SELECT u.id, u.name FROM meeting_name mn
                JOIN users u ON mn.user_id = u.id
                WHERE mn.meeting_id = %s
            """, (meeting_id,))
            users = cur.fetchall()

            # 3️⃣ 查詢登入紀錄（根據會議 ID）
            cur.execute("""
                SELECT user_id, login_time FROM login_records
                WHERE meeting_id = %s
            """, (meeting_id,))
            logs = cur.fetchall()

            # 4️⃣ 判斷誰登入了
            logged_in = {
                u["name"]: r["login_time"].strftime("%H:%M")
                for u in users for r in logs if u["id"] == r["user_id"]
            }
            not_logged_in = [u["name"] for u in users if u["name"] not in logged_in]

            return jsonify({
                "status": "success",
                "meeting_name": meeting["meeting_name"],
                "logged_in": logged_in,
                "not_logged_in": not_logged_in
            })

@app.route("/auto_verify", methods=["POST"])
def auto_verify():
    data = request.get_json()
    image_data = data.get("image")
    if not image_data:
        return jsonify({"status": "fail", "message": "缺少影像資料"}), 400

    try:
        _, encoded = image_data.split(",", 1)
        img_bytes = base64.b64decode(encoded)
        img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    except:
        return jsonify({"status": "fail", "message": "解碼失敗"}), 400

    encodings = face_recognition.face_encodings(rgb_img)
    if not encodings:
        return jsonify({"status": "fail", "message": "無法偵測人臉"}), 400

    live_encoding = encodings[0]
    best_match = None
    best_sim = 0

    now = datetime.now()
    with get_db_connection() as conn:
        with conn.cursor() as cur:

            # 1️⃣ 找出目前進行中的會議
            cur.execute("SELECT * FROM meetings")
            meetings = cur.fetchall()
            active_meeting = None
            for m in meetings:
                if m["time_start"] <= now <= m["time_end"]:
                    active_meeting = m
                    break

            if not active_meeting:
                return jsonify({"status": "fail", "message": "目前無進行中會議"}), 403

            meeting_id = active_meeting["id"]

            # 2️⃣ 取得當前會議允許的使用者 ID
            cur.execute("SELECT user_id FROM meeting_name WHERE meeting_id = %s", (meeting_id,))
            allowed_ids = [row["user_id"] for row in cur.fetchall()]

            # 3️⃣ 載入所有已註冊人臉，進行比對
            cur.execute("SELECT id, name FROM users")
            users = cur.fetchall()

            for u in users:
                uid, uname = u["id"], u["name"]
                img_path = os.path.join(REGISTERED_DIR, f"{uid}.jpg")
                if not os.path.exists(img_path):
                    continue
                known_img = face_recognition.load_image_file(img_path)
                known_enc = face_recognition.face_encodings(known_img)
                if not known_enc:
                    continue

                sim = 1 - face_recognition.face_distance([known_enc[0]], live_encoding)[0]
                if sim > best_sim:
                    best_sim = sim
                    best_match = (uid, uname)

            # 4️⃣ 判斷是否達相似度門檻
            if not best_match or best_sim < SIMILARITY_THRESHOLD:
                return jsonify({"status": "fail", "message": "找不到相符的臉部資料"}), 403

            uid, name = best_match

            # 5️⃣ 判斷是否在此會議排程中
            if uid not in allowed_ids:
                return jsonify({"status": "fail", "message": f"{name} 不在此時段排程中"}), 403

            # 6️⃣ 寫入登入紀錄（含會議 ID）
            cur.execute("""
                INSERT INTO login_records (user_id, login_time, meeting_id)
                VALUES (%s, %s, %s)
            """, (uid, now, meeting_id))
            conn.commit()

            return jsonify({
                "status": "success",
                "name": name,
                "id": uid,
                "similarity": round(best_sim, 3),
                "meeting_name": active_meeting["meeting_name"],
                "meeting_id": meeting_id
            })

# === 後臺管理 ===
@app.route("/admin_register", methods=["POST"])
def admin_register():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"status": "fail", "message": "❌ 使用者名稱或密碼不可為空"}), 400
    hashed_password = generate_password_hash(password)
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO admin_users (username, password) VALUES (%s, %s)", (username, hashed_password))
                conn.commit()
        return jsonify({"status": "success", "message": "✅ 管理員帳號已註冊"}),200
    except pymysql.IntegrityError:
        return jsonify({"status": "fail", "message": "❌ 使用者名稱已存在"}), 409
                
@app.route("/admin_login", methods=["POST"])
def admin_login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM admin_users WHERE username=%s", (username,))
            user = cur.fetchone()
            if user is None:
                return jsonify({"status": "fail", "message": "查無此資料"}), 401
            if check_password_hash(user["password"], password):
                login_user(AdminUser(user['id'], username))
                return jsonify({"status": "success", "message": "登入成功"})
            else:
                return jsonify({"status": "fail", "message": "帳號或密碼錯誤"}), 401

@app.route("/admin_login_status", methods=["GET"])
def admin_login_status():
    if current_user.is_authenticated:
        return jsonify({"status": "success","message": 
                        f"✅ 已登入：{current_user.username}","username": current_user.username})
    else:
        return jsonify({"status": "fail","message": "❌ 尚未登入"}), 401

@app.route("/faces", methods=["GET"])
@login_required
def list_faces():
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT id, name FROM users")
        users = cur.fetchall()
    conn.close()
    faces = [{"id": u["id"], "name": u["name"], "url": f"{BASE_URL}/static/registered_faces/{u['id']}.jpg"} for u in users]
    return jsonify({"status": "success", "faces": faces})

@app.route("/delete_user/<int:user_id>", methods=["DELETE"])
@login_required
def delete_user(user_id):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # 1. 刪除 user 對會議的關聯
                cur.execute("DELETE FROM meeting_name WHERE user_id=%s", (user_id,))

                # 2. 刪除登入紀錄
                cur.execute("DELETE FROM login_records WHERE user_id=%s", (user_id,))

                # 3. 刪除使用者人臉照片
                cur.execute("SELECT image_path FROM users WHERE id=%s", (user_id,))
                row = cur.fetchone()
                if row and row['image_path']:
                    try:
                        img_path = os.path.join(BASE_DIR, row['image_path'])
                        if os.path.exists(img_path):
                            os.remove(img_path)
                    except Exception as e:
                        print(f"[圖片刪除錯誤] {e}")

                # 4. 刪除使用者主資料
                cur.execute("DELETE FROM users WHERE id=%s", (user_id,))
            conn.commit()

        return jsonify({"status": "success", "message": "✅ 使用者已刪除"})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "fail", "message": f"❌ 刪除失敗：{str(e)}"}), 500

@app.route("/allowed_users_by_schedule", methods=["POST"])
@login_required
def save_schedule():
    new_data = request.get_json()
    if not isinstance(new_data, dict) or not new_data:
        return jsonify({"status": "fail", "message": "資料格式錯誤或為空"})

    time_slot = new_data.get('time_slot', '')
    meeting_name = new_data.get('meeting_name', '')
    names = new_data.get('names', [])

    if not time_slot or not meeting_name or not names:
        return jsonify({"status": "fail", "message": "缺少必要欄位"})

    try:
        date_part, time_part = time_slot.split(" ")
        start_str, end_str = time_part.split("-")
        new_start = datetime.strptime(f"{date_part} {start_str}", "%Y-%m-%d %H:%M")
        new_end = datetime.strptime(f"{date_part} {end_str}", "%Y-%m-%d %H:%M")
    except:
        return jsonify({"status": "fail", "message": "時間格式錯誤，請使用 YYYY-MM-DD HH:MM-HH:MM"})

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # 查詢所有排程，避免時間重疊
            cur.execute("SELECT meeting_name, time_start, time_end FROM meetings")
            for row in cur.fetchall():
                exist_start = row['time_start']
                exist_end = row['time_end']
                if max(new_start, exist_start) < min(new_end, exist_end):
                    return jsonify({"status": "fail", "message": f"❌ 此時段與『{row['meeting_name']}』的排程時間重疊"})

            # 新增會議
            cur.execute("INSERT INTO meetings (meeting_name, time_start, time_end) VALUES (%s, %s, %s)",
                        (meeting_name, new_start, new_end))
            meeting_id = cur.lastrowid

            for name in names:
                cur.execute("SELECT id FROM users WHERE name=%s", (name,))
                user = cur.fetchone()
                if not user:
                    conn.rollback()
                    return jsonify({"status": "fail", "message": f"使用者 {name} 不存在"})

                cur.execute("INSERT INTO meeting_name (meeting_id, user_id) VALUES (%s, %s)",
                            (meeting_id, user['id']))
        conn.commit()

    return jsonify({"status": "success", "message": "✅ 排程已成功儲存"})


@app.route("/get_schedules", methods=["GET"])
@login_required
def get_schedules():
    result = {}
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT m.id, m.meeting_name, m.time_start, m.time_end, u.name
                    FROM meetings m
                    JOIN meeting_name mn ON m.id = mn.meeting_id
                    JOIN users u ON mn.user_id = u.id
                    ORDER BY m.time_start
                """)
                rows = cur.fetchall()

                schedule_map = {}
                for row in rows:
                    start_str = row["time_start"].strftime("%Y-%m-%d %H:%M")
                    end_str = row["time_end"].strftime("%H:%M")
                    key = f"{row['meeting_name']}｜{start_str}-{end_str}"
                    if key not in schedule_map:
                        schedule_map[key] = []
                    schedule_map[key].append(row["name"])

                result = schedule_map

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "fail", "message": f"❌ 取得排程失敗：{str(e)}"}), 500

    return jsonify({"status": "success", "schedule": result})


@app.route("/delete_schedule", methods=["POST"])
@login_required
def delete_schedule():
    data = request.get_json()
    if not data or 'time_slot' not in data.keys() or 'meeting_name' not in data.keys():
        return jsonify({"status": "fail", "message": "缺少必要參數"}), 400

    time_slot = data["time_slot"]
    meeting_name = data["meeting_name"]

    try:
        date_part, time_part = time_slot.strip().split(" ")
        start_str, end_str = time_part.strip().split("-")
        new_start = datetime.strptime(f"{date_part} {start_str}", "%Y-%m-%d %H:%M")
        new_end = datetime.strptime(f"{date_part} {end_str}", "%Y-%m-%d %H:%M")
    except Exception as e:
        return jsonify({"status": "fail", "message": f"時間格式錯誤，請使用 YYYY-MM-DD HH:MM-HH:MM：{str(e)}"}), 400

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # 找到該會議 ID
            cur.execute("""
                SELECT id FROM meetings
                WHERE meeting_name = %s AND time_start = %s AND time_end = %s
            """, (meeting_name, new_start, new_end))
            meeting = cur.fetchone()
            if not meeting:
                return jsonify({"status": "fail", "message": "❌ 找不到指定排程，請確認時間格式與會議名稱是否完全一致"}), 404

            meeting_id = meeting['id']

            cur.execute("DELETE FROM login_records WHERE meeting_id = %s", (meeting_id,))
            cur.execute("DELETE FROM meeting_name WHERE meeting_id = %s", (meeting_id,))
            cur.execute("DELETE FROM meetings WHERE id = %s", (meeting_id,))
        conn.commit()

    return jsonify({"status": "success", "message": f"✅ 已刪除排程：{meeting_name}｜{time_slot}"})

@app.route("/admin_logout", methods=["POST"])
def admin_logout():
    logout_user()
    return jsonify({"status": "success", "message": "✅ 已登出"})

if __name__ == "__main__":
    init_db()
    app.run(host=BASE_IP, port=BASE_PORT, debug=True)