from utils import Flask, jsonify, CORS, LoginManager
from apps.api import api_bp
from db import get_db_connection, AdminUser

login_manager = ''
def create_app():
    global login_manager
    
    app = Flask(__name__, static_folder='static')
    CORS(app, origins="*", supports_credentials=True)
    app.secret_key = "su-song-chi_monkey14"

    # 初始化 LoginManager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "/admin_login"

    @login_manager.unauthorized_handler
    def unauthorized_callback():
        return jsonify({
            "status": "fail",
            "message": "❌ 尚未登入或登入已過期"
        }), 401
    
    @login_manager.user_loader
    def load_user(user_id):
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM admin_users WHERE id = %s", (user_id,))
                user = cur.fetchone()
                if user:
                    return AdminUser(user["id"], user["username"])
        return None

    app.register_blueprint(api_bp)

    return app