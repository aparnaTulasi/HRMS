import jwt
from functools import wraps
from flask import request, jsonify, current_app
from models.user import User

def jwt_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"message": "Authentication required"}), 401

        token = auth.split(" ", 1)[1].strip()
        if not token:
            return jsonify({"message": "Authentication required"}), 401

        try:
            payload = jwt.decode(
                token,
                current_app.config["SECRET_KEY"],
                algorithms=["HS256"]
            )
            user_id = payload.get("user_id")
            if not user_id:
                return jsonify({"message": "Invalid token"}), 401

            user = User.query.get(int(user_id))
            if not user or user.status != "ACTIVE":
                return jsonify({"message": "User not found or inactive"}), 401

            # attach to request
            request.current_user = user

        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token expired"}), 401
        except Exception:
            return jsonify({"message": "Invalid token"}), 401

        return fn(*args, **kwargs)
    return wrapper


def get_current_user():
    return getattr(request, "current_user", None)