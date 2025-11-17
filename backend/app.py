from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
from datetime import timedelta
from routes import register_routes

def create_app():
    app = Flask(__name__)

    # Secret key for sessions (replace in production)
    app.config["SECRET_KEY"] = "dev-secret-change-me"

    # How long user sessions remain valid
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=14)

    # Enable CORS for frontend dev environment
    # Allows cookies (credentials) to be included
    CORS(
        app,
        resources={r"/api/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173"]}},
        supports_credentials=True
    )

    # Register all API routes (kept in routes/)
    register_routes(app)

    # Handle expected HTTP errors (e.g., 404, 403, etc.)
    @app.errorhandler(HTTPException)
    def handle_http_error(e):
        return jsonify({"code": e.code, "message": e.description}), e.code

    # Global fallback for any unexpected server-side errors
    @app.errorhandler(Exception)
    def handle_any_error(e):
        app.logger.exception(e)  # Log full stack trace for debugging
        return jsonify({"code": 500, "message": str(e)}), 500

    return app

if __name__ == "__main__":
    # Run development server
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
