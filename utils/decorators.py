from flask import request, jsonify, g
import jwt
from functools import wraps
from config import Config
from models.user import User

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        
        if auth_header:
            if auth_header.startswith('Bearer '):
                parts = auth_header.split(' ')
                if len(parts) > 1:
                    token = parts[1]

        if not token or not token.strip() or token.lower() in ['null', 'undefined']:
            print(f"❌ Auth Failed: Token is missing. Header: {auth_header}", flush=True)
            return jsonify({'message': 'Token is missing'}), 401
        try:
            data = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
            g.user = User.query.get(data['user_id'])
            if not g.user:
                print(f"❌ Auth Failed: User {data['user_id']} not found", flush=True)
                return jsonify({'message': 'User not found'}), 401
        except Exception as e:
            print(f"❌ Auth Failed: {str(e)}", flush=True)
            return jsonify({'message': 'Token is invalid!', 'error': str(e)}), 401
        return f(*args, **kwargs)
    return decorated

def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if g.user.role not in allowed_roles:
                return jsonify({'message': 'Permission denied'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def permission_required(permission_code):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not g.user.has_permission(permission_code):
                return jsonify({'message': 'Insufficient permissions'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator