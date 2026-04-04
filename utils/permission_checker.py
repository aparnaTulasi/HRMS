from flask import g, jsonify
from functools import wraps
from constants.permissions import get_permission_code

def has_permission(user, module, action):
    """
    Checks if a user has a specific permission.
    Super Admin always has all permissions.
    """
    if not user:
        return False
    
    if (user.role or "").upper() == 'SUPER_ADMIN':
        return True
    
    permission_code = get_permission_code(module, action)
    
    # Check if this code exists in user's permissions
    # Assuming user.permissions is a list of objects with permission_code attribute
    return any(p.permission_code == permission_code for p in user.permissions)

def super_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not g.user or (g.user.role or "").upper() != 'SUPER_ADMIN':
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
