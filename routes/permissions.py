from flask import Blueprint, request, jsonify, g
from models import db
from models.user import User
from models.permission import UserPermission
from utils.decorators import token_required, role_required

permissions_bp = Blueprint('permissions', __name__)

@permissions_bp.route('/assign', methods=['POST'])
@token_required
@role_required(['SUPER_ADMIN', 'ADMIN'])
def assign_permission():
    data = request.get_json()
    user = User.query.get(data['user_id'])
    if not user: return jsonify({'message': 'User not found'}), 404
    
    # Admin check: Can only assign to users in their company
    if g.user.role == 'ADMIN' and user.company_id != g.user.company_id:
        return jsonify({'message': 'Unauthorized to assign permissions to this user'}), 403

    UserPermission.query.filter_by(user_id=user.id, permission_code=data['permission_code']).delete()
    user_perm = UserPermission(user_id=user.id, permission_code=data['permission_code'], granted_by=g.user.id)
    db.session.add(user_perm)
    db.session.commit()
    return jsonify({'message': 'Permission assigned successfully'})
