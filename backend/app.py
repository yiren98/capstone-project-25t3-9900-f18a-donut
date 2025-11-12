from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
from datetime import timedelta
from routes import register_routes

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "dev-secret-change-me"
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=14)
    CORS(app, resources={r"/api/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173"]}}, supports_credentials=True)

    register_routes(app)
    @app.errorhandler(HTTPException)
    def handle_http_error(e):
        return jsonify({"code": e.code, "message": e.description}), e.code

    @app.errorhandler(Exception)
    def handle_any_error(e):
        app.logger.exception(e)
        return jsonify({"code": 500, "message": str(e)}), 500

    return app

app = create_app()

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)