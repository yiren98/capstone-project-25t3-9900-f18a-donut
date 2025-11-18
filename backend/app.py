from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
from datetime import timedelta
from routes import register_routes
import os
import pathlib


# ===== Debug Logs (保留，但 Render 只会输出一次) =====
print("=== DEBUG: Current working directory ===")
print(os.getcwd())

print("=== DEBUG: Full /app directory tree ===")
for root, dirs, files in os.walk("/", topdown=True):
    print(root, dirs, files)
    if root.count("/") > 2:
        break

print("=== DEBUG: /app ===")
for root, dirs, files in os.walk("/app"):
    print(root, dirs, files)
    break


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "dev-secret-change-me"
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=14)

    # ========= 🚀 最关键的部分：CORS 修复 =========
    FRONTEND_URL = "https://capstone-project-25t3-9900-f18a-donut-fn.onrender.com"

    CORS(
        app,
        resources={r"/api/*": {"origins": [FRONTEND_URL]}},
        supports_credentials=True
    )
    # =============================================

    register_routes(app)

    @app.errorhandler(HTTPException)
    def handle_http_error(e):
        return jsonify({"code": e.code, "message": e.description}), e.code

    # Handle unexpected internal server errors
    @app.errorhandler(Exception)
    def handle_any_error(e):
        app.logger.exception(e)
        return jsonify({"code": 500, "message": str(e)}), 500

    return app


app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
