from db import get_db_connection
from utils.utils import generate_password_hash

def reset_password_post_f(uid, token, new_password):
    if not uid or not token or not new_password:
        return{"status": "fail", "message": "資料不完整"}, 400

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # 查詢 token 是否有效
            cur.execute("""
                SELECT * FROM password_resets
                WHERE user_id = %s AND token = %s AND expires_at > NOW()
            """, (uid, token))
            token_data = cur.fetchone()

            if not token_data:
                return{"status": "fail", "message": "連結無效或已過期"}, 400

            # 將密碼加密並更新
            hashed_pw = generate_password_hash(new_password)
            cur.execute("""
                UPDATE admin_users SET password = %s WHERE id = %s
            """, (hashed_pw, uid))

            # 作廢 token
            cur.execute("DELETE FROM password_resets WHERE user_id = %s", (uid,))
            conn.commit()

        return{"status": "success", "message": "密碼已成功重設，請重新登入"}
