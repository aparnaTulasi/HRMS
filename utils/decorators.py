from flask import request, jsonify, g
import jwt
from functools import wraps
from config import Config
from models.user import User

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        try:
            data = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
            g.user = User.query.get(data['user_id'])
            if not g.user:
                return jsonify({'message': 'User not found'}), 401
        except Exception as e:
            return jsonify({'message': 'Token is invalid!', 'error': str(e)}), 401
        return f(*args, **kwargs)
    return decorated

def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from utils.role_utils import normalize_role
            user_role = normalize_role(getattr(g.user, 'role', ''))
            allowed_normalized = [normalize_role(r) for r in allowed_roles]
            
            if user_role == 'SUPER_ADMIN':
                return f(*args, **kwargs)
            if user_role not in allowed_normalized:
                return jsonify({'message': 'Permission denied'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def permission_required(permission_code):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not g.user:
                return jsonify({'message': 'Unauthorized'}), 401
            
            from utils.role_utils import normalize_role
            if normalize_role(g.user.role) == 'SUPER_ADMIN':
                return f(*args, **kwargs)

            # Check granular permissions
            if not g.user.has_permission(permission_code):
                return jsonify({
                    'success': False,
                    'message': f"Insufficient permissions: Missing '{permission_code}'"
                }), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_company_url(f):
    @wraps(f)
    @token_required
    def decorated_function(username, company, *args, **kwargs):
        from utils.url_generator import clean_username
        from models.company import Company
        
        # 1. Recompute the "truth" from DB
        actual_username = clean_username(g.user.email)
        company_obj = Company.query.get(g.user.company_id) if g.user.company_id else None
        actual_company = company_obj.subdomain if company_obj else None
        
        # 2. Compare against URL parameters
        if username != actual_username or company != actual_company:
            return jsonify({
                "message": "Forbidden: URL mismatch",
                "error": "You are not authorized to access this specific dashboard URL."
            }), 403
            
        return f(username, company, *args, **kwargs)
    return decorated_function