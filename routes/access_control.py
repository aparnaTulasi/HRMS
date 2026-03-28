from flask import Blueprint, request, jsonify, g
from models import db
from models.user import User
from models.employee import Employee
from models.role import Role, RolePermission
from models.permission import Permission, UserPermission
from utils.audit_logger import log_action
from utils.decorators import token_required, role_required
from werkzeug.security import generate_password_hash
from datetime import datetime

access_control_bp = Blueprint('access_control', __name__)

@access_control_bp.route('/users', methods=['GET'])
@token_required
@role_required(['ADMIN', 'HR'])
def get_users_list():
    """
    Returns the list of users for the Access Control table.
    """
    try:
        users = User.query.filter_by(company_id=g.user.company_id).all()
        output = []
        for user in users:
            # Human-readable last login (simplified for now)
            last_login_str = "Never"
            if user.last_login:
                diff = datetime.utcnow() - user.last_login
                if diff.days == 0:
                    last_login_str = f"Today, {user.last_login.strftime('%I:%M %p')}"
                elif diff.days == 1:
                    last_login_str = f"Yesterday, {user.last_login.strftime('%I:%M %p')}"
                elif diff.days < 7:
                    last_login_str = f"{diff.days} days ago"
                else:
                    last_login_str = f"{diff.days // 7} weeks ago"

            output.append({
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'role': user.role,
                'status': user.status,
                'last_login': last_login_str,
                'username': user.username
            })
        return jsonify({'success': True, 'users': output}), 200
    except Exception as e:
        return jsonify({'message': 'Failed to fetch users', 'error': str(e)}), 500

@access_control_bp.route('/users', methods=['POST'])
@token_required
@role_required(['ADMIN', 'HR'])
def create_access_user():
    data = request.get_json()
    try:
        # Check if email exists
        if User.query.filter_by(email=data['email'], company_id=g.user.company_id).first():
            return jsonify({'message': 'Email already exists for this company'}), 400
            
        new_user = User(
            email=data['email'],
            username=data.get('username', data['email'].split('@')[0]),
            password=generate_password_hash(data['password']),
            role=data['role'],
            company_id=g.user.company_id,
            status=data.get('status', 'ACTIVE')
        )
        db.session.add(new_user)
        db.session.flush() # Get user ID
        
        # Add granular permissions
        permissions = data.get('permissions', [])
        for perm_code in permissions:
            up = UserPermission(
                user_id=new_user.id,
                permission_code=perm_code,
                granted_by=g.user.id
            )
            db.session.add(up)
            
        db.session.commit()
        return jsonify({'message': 'User created successfully', 'user_id': new_user.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to create user', 'error': str(e)}), 500

@access_control_bp.route('/users/<int:user_id>', methods=['PUT'])
@token_required
@role_required(['ADMIN', 'HR'])
def update_access_user(user_id):
    data = request.get_json()
    try:
        user = User.query.get_or_404(user_id)
        if user.company_id != g.user.company_id:
            return jsonify({'message': 'Unauthorized'}), 403
            
        if 'role' in data:
            user.role = data['role']
        if 'status' in data:
            user.status = data['status']
        if 'email' in data:
            user.email = data['email']
            
        # Update permissions
        if 'permissions' in data:
            # Delete old permissions
            UserPermission.query.filter_by(user_id=user.id).delete()
            # Add new ones
            for perm_code in data['permissions']:
                up = UserPermission(
                    user_id=user.id,
                    permission_code=perm_code,
                    granted_by=g.user.id
                )
                db.session.add(up)
                
        db.session.commit()
        return jsonify({'message': 'User updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to update user', 'error': str(e)}), 500

@access_control_bp.route('/users/<int:user_id>/status', methods=['PATCH'])
@token_required
@role_required(['ADMIN', 'HR'])
def toggle_user_status(user_id):
    data = request.get_json()
    try:
        user = User.query.get_or_404(user_id)
        if user.company_id != g.user.company_id:
            return jsonify({'message': 'Unauthorized'}), 403
            
        user.status = data.get('status', 'ACTIVE' if user.status == 'INACTIVE' else 'INACTIVE')
        db.session.commit()
        return jsonify({'message': 'Status updated', 'status': user.status}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to update status', 'error': str(e)}), 500

@access_control_bp.route('/users/<int:user_id>', methods=['DELETE'])
@token_required
@role_required(['ADMIN', 'HR'])
def delete_access_user(user_id):
    try:
        user = User.query.get_or_404(user_id)
        if user.company_id != g.user.company_id:
            return jsonify({'message': 'Unauthorized'}), 403
            
        # Optional: Delete permissions first if not using cascade
        UserPermission.query.filter_by(user_id=user.id).delete()
        db.session.delete(user)
        db.session.commit()
        return jsonify({'message': 'User deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to delete user', 'error': str(e)}), 500

@access_control_bp.route('/roles', methods=['GET'])
@token_required
@role_required(['ADMIN', 'HR'])
def get_roles():
    """
    Returns all roles for the company including their permission matrix.
    """
    try:
        roles = Role.query.filter_by(company_id=g.user.company_id).all()
        # Fallback to static roles if none in DB for this company
        if not roles:
            # Seed default roles if needed? For now just return empty
            pass
            
        return jsonify({'success': True, 'roles': [r.to_dict() for r in roles]}), 200
    except Exception as e:
        return jsonify({'message': 'Failed to fetch roles', 'error': str(e)}), 500

@access_control_bp.route('/roles', methods=['POST'])
@token_required
@role_required(['ADMIN', 'HR'])
def create_role():
    data = request.get_json()
    try:
        # Check if role exists
        if Role.query.filter_by(name=data['name'], company_id=g.user.company_id).first():
            return jsonify({'message': 'Role already exists'}), 400
            
        new_role = Role(
            name=data['name'],
            description=data.get('description'),
            company_id=g.user.company_id
        )
        db.session.add(new_role)
        db.session.flush()
        
        # Save permissions (Matrix)
        permissions = data.get('permissions', [])
        for perm_code in permissions:
            rp = RolePermission(role_id=new_role.id, permission_code=perm_code)
            db.session.add(rp)
            
        # Log Action
        log_action(
            user_id=g.user.id,
            action="Created Role",
            module="Auth",
            target_entity="Role",
            entity_id=new_role.id,
            meta_data={'role_name': new_role.name}
        )
        
        db.session.commit()
        return jsonify({'message': 'Role created successfully', 'role_id': new_role.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to create role', 'error': str(e)}), 500

@access_control_bp.route('/roles/<int:role_id>', methods=['PUT'])
@token_required
@role_required(['ADMIN', 'HR'])
def update_role(role_id):
    data = request.get_json()
    try:
        role = Role.query.get_or_404(role_id)
        if role.company_id != g.user.company_id:
            return jsonify({'message': 'Unauthorized'}), 403
            
        if 'name' in data:
            role.name = data['name']
        if 'description' in data:
            role.description = data['description']
            
        if 'permissions' in data:
            # Delete old permissions
            RolePermission.query.filter_by(role_id=role.id).delete()
            # Add new ones
            for perm_code in data['permissions']:
                rp = RolePermission(role_id=role.id, permission_code=perm_code)
                db.session.add(rp)
                
        # Log Action
        log_action(
            user_id=g.user.id,
            action="Updated Role",
            module="Auth",
            target_entity="Role",
            entity_id=role.id,
            meta_data={'role_name': role.name}
        )
        
        db.session.commit()
        return jsonify({'message': 'Role updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to update role', 'error': str(e)}), 500

@access_control_bp.route('/roles/<int:role_id>', methods=['DELETE'])
@token_required
@role_required(['ADMIN', 'HR'])
def delete_role(role_id):
    try:
        role = Role.query.get_or_404(role_id)
        if role.company_id != g.user.company_id:
            return jsonify({'message': 'Unauthorized'}), 403
            
        # Log Action
        log_action(
            user_id=g.user.id,
            action="Deleted Role",
            module="Auth",
            target_entity="Role",
            entity_id=role.id,
            meta_data={'role_name': role.name}
        )
        
        db.session.delete(role)
        db.session.commit()
        return jsonify({'message': 'Role deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to delete role', 'error': str(e)}), 500
