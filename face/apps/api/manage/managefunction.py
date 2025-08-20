from db import get_db_connection, AdminUser
from facepro import BASE_URL, REGISTERED_DIR, BASE_DIR
from utils.utils import datetime, os, send_from_directory, logout_user, secrets, timedelta, cv2, np
from utils.utils import generate_password_hash, pymysql, check_password_hash, login_user, current_user, request
from utils.mail_utils import send_reset_email

def admin_register_post_f(username, password, email):
    if not username or not password or not email:
        return{"status": "fail", "message": "❌ 使用者名稱或密碼不可為空"}, 400
    hashed_password = generate_password_hash(password)
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO admin_users (username, password, email) VALUES (%s, %s, %s)", (username, hashed_password, email))
                conn.commit()
        return{"status": "success", "message": "✅ 管理員帳號已註冊"},200
    except pymysql.IntegrityError as e:
        if "username" in str(e):
            return{"status": "fail", "message": "❌ 使用者名稱已存在"}, 409
        elif "email" in str(e):
            return{"status": "fail", "message": "此信箱已註冊"}, 409
        else:
            return{"status": "fail", "message": "註冊失敗，請稍後再試"}, 500 
    
    
def admin_login_post_f(username, password):
    with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM admin_users WHERE username=%s", (username,))
                user = cur.fetchone()
                if user is None:
                    return{"status": "fail", "message": "查無此資料"}, 401
                if check_password_hash(user["password"], password):
                    login_user(AdminUser(user['id'], username))
                    return{"status": "success", "message": "登入成功"}
                else:
                    return{"status": "fail", "message": "帳號或密碼錯誤"}, 401

def admin_forget_password_f(email):
    if not email:
        return {"status": "fail", "message": "請輸入信箱"}, 400
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # 查詢使用者
            cur.execute("SELECT * FROM admin_users WHERE email=%s", (email,))

            user = cur.fetchone()
            if not user:
                return {"status": "fail", "message": "未找到此信箱"}, 404
            
            # 產生 token 與過期時間
            token = secrets.token_urlsafe(32)
            expiry = datetime.now() + timedelta(minutes=30)
            user_id = user["id"]

            # 寫入 password_resets 資料表（如有則更新）
            cur.execute("""
                INSERT INTO password_resets (user_id, token, expires_at)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE token = VALUES(token), expires_at = VALUES(expires_at)
            """, (user_id, token, expiry))
            conn.commit()

    reset_link = f"{BASE_URL}/reset_password?token={token}&uid={user_id}"
    result = send_reset_email(email, reset_link)
    if result:
        return {"status": "success", "message": "已寄送重設密碼連結至您的信箱"}
    else:
        return{"status": "fail","message": "未發送信件"}, 500

def admin_login_status_f():
    if current_user.is_authenticated:
            return{"status": "success","message": 
            f"已登入：{current_user.username}","username": current_user.username}
    else:
            return{"status": "fail","message": "尚未登入"}, 401
    
def face_f():
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT id, name FROM users")
        users = cur.fetchall()
    conn.close()
    faces = [{"id": u["id"], "name": u["name"], "url": f"{BASE_URL}/api/get_face?filename={u['id']}.jpg"} for u in users]
    return{"status": "success", "faces": faces}

def check_name_exists_f():
    name = request.args.get("name", "")
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as count FROM users WHERE name = %s", (name,))
            result = cur.fetchone()
            return{"exists": result["count"] > 0}
        
def get_face_f():
        filename = request.args.get("filename")
        if not filename:
            return{"status": "fail", "message": "缺少 filename"}, 400

        try:
            file_path = os.path.join(REGISTERED_DIR, filename)
            if not os.path.exists(file_path):
                return{"status": "fail", "message": "找不到圖片"}, 404

            return send_from_directory(REGISTERED_DIR, filename)
        
        except Exception as e:
            return{"status": "error", "message": str(e)}, 500
        
def register_face_f():
    try:
        image = request.files.get("image")
        user_id = request.form.get("user_id")
        name = request.form.get("name")

        if not image or not user_id or not name:
            return {"status": "fail", "message": "缺少必要欄位"}, 400

        filename = f"{user_id}.jpg"
        save_path = os.path.join(REGISTERED_DIR, filename)
        image.save(save_path)

        # 更新使用者資料表中的 image_path 欄位
        rel_path = os.path.relpath(save_path, BASE_DIR)  # 儲存相對路徑
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE users SET image_path = %s WHERE id = %s", (rel_path, user_id))
                conn.commit()

        return {"status": "success", "message": f"使用者 {name} 的照片已更新"}, 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "fail", "message": f"錯誤：{str(e)}"}, 500
        
def delete_user_f(user_id):
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

            return{"status": "success", "message": "使用者已刪除"}

        except Exception as e:
            import traceback
            traceback.print_exc()
            return{"status": "fail", "message": f"刪除失敗：{str(e)}"}, 500
        
def allowed_users_by_schedule_f():
    new_data = request.get_json()
    if not isinstance(new_data, dict) or not new_data:
        return {"status": "fail", "message": "資料格式錯誤或為空"}

    time_slot = new_data.get('time_slot', '')
    meeting_name = new_data.get('meeting_name', '')
    names = new_data.get('names', [])

    if not time_slot or not meeting_name or not names:
        return {"status": "fail", "message": "缺少必要欄位"}

    try:
        date_part, time_part = time_slot.split(" ")
        start_str, end_str = time_part.split("-")
        new_start = datetime.strptime(f"{date_part} {start_str}", "%Y-%m-%d %H:%M")
        new_end = datetime.strptime(f"{date_part} {end_str}", "%Y-%m-%d %H:%M")
    except:
        return {"status": "fail", "message": "時間格式錯誤，請使用 YYYY-MM-DD HH:MM-HH:MM"}

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            #  先檢查所有排程是否有重疊
            cur.execute("SELECT meeting_name, time_start, time_end FROM meetings")
            for row in cur.fetchall():
                exist_start = row['time_start']
                exist_end = row['time_end']
                if max(new_start, exist_start) < min(new_end, exist_end):
                    return {"status": "fail", "message": f"此時段與『{row['meeting_name']}』的排程時間重疊"}

            # 沒衝突，正式寫入排程
            cur.execute("INSERT INTO meetings (meeting_name, time_start, time_end) VALUES (%s, %s, %s)",
                        (meeting_name, new_start, new_end))
            meeting_id = cur.lastrowid

            for name in names:
                cur.execute("SELECT id FROM users WHERE name=%s", (name,))
                user = cur.fetchone()
                if not user:
                    conn.rollback()
                    return {"status": "fail", "message": f"使用者 {name} 不存在"}

                cur.execute("INSERT INTO meeting_name (meeting_id, user_id) VALUES (%s, %s)",
                            (meeting_id, user['id']))

            conn.commit()

    return {"status": "success", "message": "排程已成功儲存"}

def face_count_f():
    """
    接收 multipart/form-data 的 image 檔案，回傳臉部數量。
    回傳格式：{"status":"success","count": <int>}
    """
    try:
        file = request.files.get("image")
        if not file:
            return {"status": "fail", "message": "缺少 image 檔案"}, 400

        # 讀成 OpenCV 影像
        buf = np.frombuffer(file.read(), dtype=np.uint8)
        img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        if img is None:
            return {"status": "fail", "message": "圖片解析失敗"}, 400

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 使用 OpenCV 內建的正臉分類器
        cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        faces = cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,      # 可視需求微調
            minNeighbors=5,
            minSize=(60, 60)      # 臉太小容易誤判；可改 80x80 試試
        )
        return {"status": "success", "count": int(len(faces))}, 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}, 500

def get_schedules_f():
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
        return{"status": "fail", "message": f"取得排程失敗：{str(e)}"}, 500

    return{"status": "success", "schedule": result}

def delete_schedule_f():
    data = request.get_json()
    if not data or 'time_slot' not in data.keys() or 'meeting_name' not in data.keys():
        return {"status": "fail", "message": "缺少必要參數"}, 400

    time_slot = data["time_slot"]
    meeting_name = data["meeting_name"]

    try:
        date_part, time_part = time_slot.strip().split(" ")
        start_str, end_str = time_part.strip().split("-")
        new_start = datetime.strptime(f"{date_part} {start_str}", "%Y-%m-%d %H:%M")
        new_end = datetime.strptime(f"{date_part} {end_str}", "%Y-%m-%d %H:%M")
    except Exception as e:
        return{"status": "fail", "message": f"時間格式錯誤，請使用 YYYY-MM-DD HH:MM-HH:MM：{str(e)}"}, 400

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # 找到該會議 ID
            cur.execute("""
                SELECT id FROM meetings
                WHERE meeting_name = %s AND time_start = %s AND time_end = %s
            """, (meeting_name, new_start, new_end))
            meeting = cur.fetchone()
            if not meeting:
                return{"status": "fail", "message": "❌ 找不到指定排程，請確認時間格式與會議名稱是否完全一致"}, 404

            meeting_id = meeting['id']

            cur.execute("DELETE FROM login_records WHERE meeting_id = %s", (meeting_id,))
            cur.execute("DELETE FROM meeting_name WHERE meeting_id = %s", (meeting_id,))
            cur.execute("DELETE FROM meetings WHERE id = %s", (meeting_id,))
        conn.commit()

    return{"status": "success", "message": f"✅ 已刪除排程：{meeting_name}｜{time_slot}"}

def admin_logout_f():
    logout_user()
    return{"status": "success", "message": "✅ 已登出"}