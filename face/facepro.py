from utils import os, YOLO, generate_password_hash

new_password = "su-song-chi_monkey14"
hashed = generate_password_hash(new_password)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REGISTERED_DIR = os.path.join(BASE_DIR, "static", "registered_faces")
BASE_IP = "127.0.0.1"
BASE_PORT = 5000
BASE_URL = "https://b8a1bfc61afd.ngrok-free.app"

os.makedirs(REGISTERED_DIR, exist_ok=True)

model = YOLO("./yolov8-face.pt")

SIMILARITY_THRESHOLD = 0.5

if __name__ == "__main__":
    from apps import create_app
    app = create_app()

    from db import init_db
    init_db()

    # 印出註冊表
    for rule in app.url_map.iter_rules():
        print(f"{rule.endpoint:30s} ➜ {rule.methods} ➜ {rule.rule}")
    app.run(host=BASE_IP, port=BASE_PORT, debug=True)