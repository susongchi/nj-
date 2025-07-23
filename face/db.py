from utils import pymysql, UserMixin

class AdminUser(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

    def get_id(self):
        return str(self.id)

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