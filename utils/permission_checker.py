from flask import g, jsonify
from functools import wraps
from constants.permissions import get_permission_code
from utils.role_utils import normalize_role

def has_permission(user, module, action):
    """
    Checks if a user has a specific permission.
    Super Admin always has all permissions.
    """
    if not user:
        return False
    
    if normalize_role(user.role) == 'SUPER_ADMIN':
        return True
    
    permission_code = get_permission_code(module, action)
    
    # Check if this code exists in user's permissions
    return any(p.permission_code == permission_code for p in user.permissions)

def super_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not g.user or normalize_role(g.user.role) != 'SUPER_ADMIN':
            return jsonify({
                "success": False,
                "message": "Forbidden: Super Admin access required"
            }), 403
        return f(*args, **kwargs)
    return decorated_function

def require_permission(module, action):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not g.user:
                return jsonify({
                    "success": False,
                    "message": "Unauthorized"
                }), 401
            
            if not has_permission(g.user, module, action):
                return jsonify({
                    "success": False,
                    "message": f"Forbidden: Missing {action} permission for {module}"
                }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
