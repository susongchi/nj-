from utils.utils import BackgroundScheduler
from db import get_db_connection

def delete_expired_tokens():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM password_resets WHERE expires_at < NOW()")
            deleted = cur.rowcount
            conn.commit()
            print(f"APScheduler 刪除了 {deleted} 筆過期 token")

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(delete_expired_tokens, 'cron', hour=0, minute=0)  # 每天凌晨12:00
    scheduler.start()
