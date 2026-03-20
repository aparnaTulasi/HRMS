from flask import Blueprint, jsonify, g, request
from models import db
from models.user import User
from models.employee import Employee
from models.super_admin import SuperAdmin
from utils.decorators import token_required
from datetime import datetime

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/api/me/profile', methods=['GET'])
@token_required
def get_my_profile():
    user = g.user
    profile_data = {
        "user_id": user.id,
        "email": user.email,
        "role": user.role,
        "status": user.status,
        "username": user.username
    }

    if user.role == 'SUPER_ADMIN':
        sa = SuperAdmin.query.filter_by(user_id=user.id).first()
        if sa:
            profile_data.update({
                "name": f"{sa.first_name or ''} {sa.last_name or ''}".strip() or "Super Admin",
                "phone": sa.phone_number,
                "address": sa.address,
                "bio": getattr(sa, 'bio', None),
                "emergency_contact": getattr(sa, 'emergency_contact', None),
                "department": getattr(sa, 'department', 'Management'),
                "designation": sa.designation or "Super Admin",
                "joining_date": sa.joining_date.isoformat() if sa.joining_date else None,
                "employee_id": "SA-001" # Static or from model?
            })
    else:
        emp = Employee.query.filter_by(user_id=user.id).first()
        if emp:
            profile_data.update({
                "name": emp.full_name,
                "phone": emp.phone_number,
                "address": emp.address.address_line1 if emp.address else None,
                "bio": getattr(emp, 'bio', None),
                "emergency_contact": getattr(emp, 'emergency_contact', None),
                "department": emp.department,
                "designation": emp.designation,
                "joining_date": emp.date_of_joining.isoformat() if emp.date_of_joining else None,
                "employee_id": emp.employee_id,
                # Add manager name if exists
                "manager": f"{emp.manager.full_name}" if emp.manager else "N/A"
            })

    return jsonify({"success": True, "data": profile_data}), 200

@profile_bp.route('/api/me/profile', methods=['PATCH'])
@token_required
def update_my_profile():
    user = g.user
    data = request.get_json()
    
    # Fields that can be updated from the profile page
    updateable_fields = ['name', 'phone', 'address', 'bio', 'emergency_contact']
    
    if user.role == 'SUPER_ADMIN':
        sa = SuperAdmin.query.filter_by(user_id=user.id).first()
        if not sa:
            return jsonify({"message": "SuperAdmin record not found"}), 404
        
        if 'name' in data:
            parts = data['name'].split(' ', 1)
            sa.first_name = parts[0]
            sa.last_name = parts[1] if len(parts) > 1 else ""
        
        if 'phone' in data: sa.phone_number = data['phone']
        if 'address' in data: sa.address = data['address']
        if 'bio' in data: sa.bio = data['bio']
        if 'emergency_contact' in data: sa.emergency_contact = data['emergency_contact']
        
    else:
        emp = Employee.query.filter_by(user_id=user.id).first()
        if not emp:
            return jsonify({"message": "Employee record not found"}), 404
            
        if 'name' in data: emp.full_name = data['name']
        if 'phone' in data: emp.phone_number = data['phone']
        if 'address' in data:
            # For simplicity, we assume address_line1 for now if they only provide a string
            from models.employee import EmployeeAddress
            if not emp.address:
                emp.address = EmployeeAddress(employee_id=emp.id, company_id=emp.company_id)
                db.session.add(emp.address)
            emp.address.address_line1 = data['address']
            
        if 'bio' in data: emp.bio = data['bio']
        if 'emergency_contact' in data: emp.emergency_contact = data['emergency_contact']

    db.session.commit()
    return jsonify({"success": True, "message": "Profile updated successfully"}), 200