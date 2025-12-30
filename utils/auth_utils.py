# c:\Users\DELL5410\Desktop\HRMS\utils\auth_utils.py
import jwt
import datetime
from functools import wraps
from flask import request, jsonify, g, current_app
from werkzeug.security import generate_password_hash, check_password_hash

# Re-export tenant DB utilities to fix ImportError in admin/routes.py
from utils.tenant_db import get_tenant_db_connection

def hash_password(password):
    return generate_password_hash(password)

def verify_password(hash, password):
    return check_password_hash(hash, password)

def generate_token(user_id, email, role, company_id):
    payload = {
        "user_id": user_id,
        "email": email,
        "role": role,
        "company_id": company_id,
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm="HS256")

def generate_reset_token(email):
    payload = {
        "email": email,
        "type": "reset",
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=15)
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm="HS256")

def verify_reset_token(token):
    try:
        data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
        if data.get('type') != 'reset':
            return None
        return data['email']
    except Exception:
        return None

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            try:
                token = request.headers['Authorization'].split(" ")[1]
            except IndexError:
                return jsonify({"error": "Token format must be 'Bearer <token>'"}), 401
        
        if not token:
            return jsonify({"error": "Token is missing"}), 401
        
        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            g.user_id = data['user_id']
            g.email = data['email']
            g.role = data['role']
            g.company_id = data['company_id']
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired"}), 401
        except Exception:
            return jsonify({"error": "Token is invalid"}), 401
            
        return f(*args, **kwargs)
    return decorated

def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # In a real app, check RBAC permissions here based on g.role
            # For now, we assume role-based checks inside routes
            return f(*args, **kwargs)
        return decorated_function
    return decorator
