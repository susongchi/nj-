from db import get_db_connection
from facepro import REGISTERED_DIR, SIMILARITY_THRESHOLD
from utils import datetime, request, cv2, base64, np, face_recognition, os

def current_meeting_f():
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
                        return {
                            "status": "success",
                            "meeting_name": m["meeting_name"],
                            "timeslot": timeslot,
                            "users": users
                        }
        return{"status": "fail", "message": "目前無會議進行中"}

def login_status_f():
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
                    return{"status": "fail", "message": "無會議進行中"}

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
                return {
                    "status": "success",
                    "meeting_name": meeting["meeting_name"],
                    "logged_in": logged_in,
                    "not_logged_in": not_logged_in
                }
            
def auto_verify_f():
        data = request.get_json()
        image_data = data.get("image")
        if not image_data:
            return{"status": "fail", "message": "缺少影像資料"}, 400

        try:
            _, encoded = image_data.split(",", 1)
            img_bytes = base64.b64decode(encoded)
            img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        except:
            return{"status": "fail", "message": "解碼失敗"}, 400

        encodings = face_recognition.face_encodings(rgb_img)
        if not encodings:
            return{"status": "fail", "message": "無法偵測人臉"}, 400

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
                    return{"status": "fail", "message": "目前無進行中會議"}, 403

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
                    return{"status": "fail", "message": "找不到相符的臉部資料"}, 403

                uid, name = best_match

                # 5️⃣ 判斷是否在此會議排程中
                if uid not in allowed_ids:
                    return{"status": "fail", "message": f"{name} 不在此時段排程中"}, 403
                # 5.5️⃣ 檢查是否已登入
                cur.execute("""
                    SELECT * FROM login_records
                    WHERE user_id = %s AND meeting_id = %s
                """, (uid, meeting_id))
                already_logged_in = cur.fetchone()

                if already_logged_in:
                    return{
                        "status": "info",
                        "message": f"{name} 已於 {already_logged_in['login_time'].strftime('%H:%M')} 登入過",
                        "name": name,
                        "id": uid,
                        "similarity": round(best_sim, 3),
                        "meeting_name": active_meeting["meeting_name"],
                        "meeting_id": meeting_id
                }, 200

                # 6️⃣ 寫入登入紀錄（含會議 ID）
                cur.execute("""
                    INSERT INTO login_records (user_id, login_time, meeting_id)
                    VALUES (%s, %s, %s)
                """, (uid, now, meeting_id))
                conn.commit()

                return{
                    "status": "success",
                    "name": name,
                    "id": uid,
                    "similarity": round(best_sim, 3),
                    "meeting_name": active_meeting["meeting_name"],
                    "meeting_id": meeting_id
                }