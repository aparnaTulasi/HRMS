from flask import Blueprint, request, jsonify, g, current_app
from models import db
from models.user import User
from models.employee import Employee
from models.permission import UserPermission
from models.company import Company
from constants.permissions import MODULES, ACTIONS, get_permission_code
from routes.auth import auth_bp
from utils.decorators import token_required
from utils.permission_checker import super_admin_required
from werkzeug.security import generate_password_hash
import logging
from utils.date_utils import parse_date

permissions_bp = Blueprint('permissions', __name__)

@permissions_bp.route('/api/superadmin/permissions/modules', methods=['GET'])
@token_required
@super_admin_required
def get_permission_modules():
    """Returns list of modules and available actions to populate the UI matrix."""
    return jsonify({
        "success": True,
        "data": {
            "modules": MODULES,
            "actions": ACTIONS
        }
    })

@permissions_bp.route('/api/superadmin/invite-member-with-permissions', methods=['POST'])
@token_required
@super_admin_required
def invite_member_with_permissions():
    """
    Creates User, Employee, and assigns granular permissions.
    Only Super Admin can access this.
    """
    data = request.get_json() or {}
    
    # Validation
    required = ["full_name", "email", "password", "role", "company_id"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"success": False, "message": f"Missing fields: {', '.join(missing)}"}), 400

    email = data['email'].strip().lower()
    if User.query.filter_by(email=email).first():
        return jsonify({"success": False, "message": "Email already exists"}), 409

    company = Company.query.get(data['company_id'])
    if not company:
        return jsonify({"success": False, "message": "Company not found"}), 404

    try:
        # 1. Create User
        new_user = User(
            email=email,
            password=generate_password_hash(data['password']),
            role=data['role'].upper(),
            company_id=company.id,
            status='ACTIVE',
            must_change_password=True  # Safety rule: first login must change
        )
        db.session.add(new_user)
        db.session.flush()

        # 2. Create Employee Profile
        # Helper to generate employee ID (simplified version of admin.py logic)
        prefix = company.company_code or "EMP"
        count = Employee.query.filter_by(company_id=company.id).count() + 1
        emp_id = f"{prefix}-{count:04d}"

        new_employee = Employee(
            user_id=new_user.id,
            company_id=company.id,
            employee_id=emp_id,
            full_name=data['full_name'],
            company_email=email,
            status='ACTIVE',
            is_active=True,
            date_of_joining=parse_date(data.get('joining_date'))
        )
        db.session.add(new_employee)

        # 3. Assign Permissions
        # Input format: {"Dashboard": ["VIEW", "CREATE"], "Employees": ["VIEW"]}
        matrix = data.get('permissions', {})
        for module, actions in matrix.items():
            if module in MODULES:
                for action in actions:
                    if action in ACTIONS:
                        perm_code = get_permission_code(module, action)
                        user_perm = UserPermission(
                            user_id=new_user.id,
                            permission_code=perm_code,
                            granted_by=g.user.id
                        )
                        db.session.add(user_perm)

        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Member {data['full_name']} invited successfully with permissions.",
            "data": {
                "user_id": new_user.id,
                "employee_id": new_employee.employee_id
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        logging.error(f"Invite with permissions error: {str(e)}")
        return jsonify({"success": False, "message": f"Failed to invite member: {str(e)}"}), 500

@permissions_bp.route('/api/superadmin/user-permissions/<int:user_id>', methods=['GET'])
@token_required
@super_admin_required
def get_user_permissions(user_id):
    """Fetch all permissions assigned to a specific user."""
    user = User.query.get_or_404(user_id)
    perms = UserPermission.query.filter_by(user_id=user_id).all()
    
    # Group by module for the UI matrix
    grouped = {}
    for p in perms:
        code = p.permission_code
        # Code is like MODULE_ACTION (e.g. DASHBOARD_VIEW)
        # We need to map it back to Module and Action
        # This is slightly tricky if module names have underscores, 
        # but our get_permission_code uses UPPERCASE and replaces spaces with underscores.
        # Since we have the MODULES list, we can find the match.
        
        for module in MODULES:
            clean_module = module.upper().replace(" ", "_").replace("&", "AND")
            if code.startswith(clean_module + "_"):
                action = code.replace(clean_module + "_", "")
                if module not in grouped:
                    grouped[module] = []
                grouped[module].append(action)
                break

    return jsonify({
        "success": True,
        "data": {
            "user_id": user_id,
            "email": user.email,
            "role": user.role,
            "permissions": grouped
        }
    })