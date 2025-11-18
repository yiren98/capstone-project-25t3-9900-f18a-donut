from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
from datetime import timedelta
from routes import register_routes
import os
import pathlib

# ===== Debug logs (will appear only once on Render) =====
print("=== DEBUG: Current working directory ===")
print(os.getcwd())

print("=== DEBUG: Root directory tree (first 2 levels) ===")
for root, dirs, files in os.walk("/", topdown=True):
    print(root, dirs, files)
    if root.count("/") > 2:
        break

print("=== DEBUG: /app directory ===")
for root, dirs, files in os.walk("/app"):
    print(root, dirs, files)
    break


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "dev-secret-change-me"
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=14)

    # ========= CORS auto-switch for local & Render environments =========
    LOCAL_ORIGINS = [
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ]

    RENDER_FRONTEND = "https://capstone-project-25t3-9900-f18a-donut-fn.onrender.com"

    # If running on Render, the environment variable "RENDER" should be set.
    if os.environ.get("RENDER"):
        allowed_origins = [RENDER_FRONTEND]
        print("=== Running on Render → Using production CORS ===")
    else:
        allowed_origins = LOCAL_ORIGINS
        print("=== Running locally → Using localhost CORS ===")

    CORS(
        app,
        resources={r"/api/*": {"origins": allowed_origins}},
        supports_credentials=True
    )
    # ====================================================================

    register_routes(app)

    # Handle known HTTP exceptions (e.g., 404, 403)
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

    # Enable debug mode locally, disable on Render
    debug_mode = not bool(os.environ.get("RENDER"))

    app.run(host='0.0.0.0', port=port, debug=debug_mode)





# from flask import Flask, jsonify
# from flask_cors import CORS
# from werkzeug.exceptions import HTTPException
# from datetime import timedelta
# from routes import register_routes

# def create_app():
#     app = Flask(__name__)

#     # Secret key for sessions (replace in production)
#     app.config["SECRET_KEY"] = "dev-secret-change-me"

#     # How long user sessions remain valid
#     app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=14)

#     # Enable CORS for frontend dev environment
#     # Allows cookies (credentials) to be included
#     CORS(
#         app,
#         resources={r"/api/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173"]}},
#         supports_credentials=True
#     )

#     # Register all API routes (kept in routes/)
#     register_routes(app)

#     # Handle expected HTTP errors (e.g., 404, 403, etc.)
#     @app.errorhandler(HTTPException)
#     def handle_http_error(e):
#         return jsonify({"code": e.code, "message": e.description}), e.code

#     # Global fallback for any unexpected server-side errors
#     @app.errorhandler(Exception)
#     def handle_any_error(e):
#         app.logger.exception(e)  # Log full stack trace for debugging
#         return jsonify({"code": 500, "message": str(e)}), 500

#     return app

# if __name__ == "__main__":
#     # Run development server
#     app = create_app()
#     app.run(host="0.0.0.0", port=5000, debug=True)
