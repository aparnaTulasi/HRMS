from functools import wraps
from flask import request, jsonify, g
import jwt
from config import SECRET_KEY

def jwt_required(roles=None):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            auth_header = request.headers.get("Authorization")

            if not auth_header or not auth_header.startswith("Bearer "):
                return jsonify({"error": "Token missing"}), 401

            token = auth_header.split(" ")[1]

            try:
                payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
                g.user_id = payload["user_id"]
                g.user_role = payload["role"]

                if roles and g.user_role not in roles:
                    return jsonify({"error": "Forbidden"}), 403

            except jwt.ExpiredSignatureError:
                return jsonify({"error": "Token expired"}), 401
            except jwt.InvalidTokenError:
                return jsonify({"error": "Invalid token"}), 401

            return f(*args, **kwargs)
        return wrapper
    return decorator
