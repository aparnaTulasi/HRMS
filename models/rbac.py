from functools import wraps
from flask import jsonify, g

def require_roles(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = getattr(g, "user", None)
            if not user:
                return jsonify({"success": False, "message": "Unauthorized"}), 401

            if user.role not in roles:
                return jsonify({"success": False, "message": "Permission denied"}), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator