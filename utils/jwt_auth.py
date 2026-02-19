from functools import wraps
from flask import request, jsonify, g, current_app
import jwt

from models.user import User

def jwt_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"success": False, "message": "Authentication required"}), 401

        token = auth.split(" ", 1)[1].strip()
        try:
            payload = jwt.decode(
                token,
                current_app.config["SECRET_KEY"],
                algorithms=["HS256"]
            )
        except jwt.ExpiredSignatureError:
            return jsonify({"success": False, "message": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"success": False, "message": "Invalid token"}), 401

        user = User.query.get(payload.get("user_id"))
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 401

        g.user = user
        g.jwt_payload = payload
        return fn(*args, **kwargs)
    return wrapper