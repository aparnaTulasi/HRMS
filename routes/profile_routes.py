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
    
    # Common Header / Summary Data (Matches UI Labels)
    profile_data = {
        "success": True,
        "data": {
            "name": user.name,
            "username": user.username,
            "email": user.email,
            "employee_id": "N/A",
            "department": "N/A",
            "joined": "N/A",
            "status": user.status,
            "role": user.role,
            "designation": "N/A",
            "overview": {
                "contact_information": {
                    "email_address": user.email,
                    "phone_number": "Not set",
                    "address_location": "Not set"
                },
                "work_snapshot": {
                    "role_designation": "Not set",
                    "department": "N/A",
                    "reporting_manager": "N/A"
                },
                "about_bio": "No bio added yet."
            },
            "work_info": {},
            "personal": {},
            "security": {}
        }
    }

    if user.role == 'SUPER_ADMIN':
        sa = SuperAdmin.query.filter_by(user_id=user.id).first()
        if sa:
            profile_data["data"].update({
                "name": f"{sa.first_name} {sa.last_name}".strip(),
                "designation": sa.designation or "Super Admin",
                "department": sa.department or "N/A",
                "employee_id": "SA-001",
                "joined": sa.joining_date.strftime("%d %b %Y") if sa.joining_date else "N/A",
                "role": "superadmin"
            })
            profile_data["data"]["overview"].update({
                "contact_information": {
                    "email_address": sa.email or user.email,
                    "phone_number": sa.phone_number or "Not set",
                    "address_location": sa.address or "Not set"
                },
                "work_snapshot": {
                    "role_designation": sa.designation or "superadmin",
                    "department": sa.department or "N/A",
                    "reporting_manager": "N/A"
                },
                "about_bio": sa.bio or "No bio added yet."
            })
    else:
        emp = Employee.query.filter_by(user_id=user.id).first()
        if emp:
            profile_data["data"].update({
                "name": emp.full_name,
                "designation": emp.designation or "Employee",
                "department": emp.department or "N/A",
                "employee_id": emp.employee_id or str(emp.id),
                "joined": emp.date_of_joining.strftime("%d %b %Y") if emp.date_of_joining else "N/A",
                "role": user.role.lower()
            })
            profile_data["data"]["overview"] = {
                "contact_information": {
                    "email_address": emp.company_email or user.email,
                    "phone_number": emp.phone_number or "Not set",
                    "address_location": emp.address.address_line1 if emp.address else "Not set"
                },
                "work_snapshot": {
                    "role_designation": emp.designation or user.role.lower(),
                    "department": emp.department or "N/A",
                    "reporting_manager": emp.manager.full_name if emp.manager else "N/A"
                },
                "about_bio": emp.bio or "No bio added yet."
            }
            # For other tabs, we keep common keys but can expand if needed
            profile_data["data"]["work_info"] = {
                "Employment Type": emp.employment_type or "N/A",
                "Pay Grade": emp.pay_grade or "N/A"
            }
            profile_data["data"]["personal"] = {
                "Gender": emp.gender or "N/A",
                "DOB": emp.date_of_birth.isoformat() if emp.date_of_birth else "N/A"
            }

    return jsonify(profile_data), 200

@profile_bp.route('/api/me/profile', methods=['PATCH'])
@token_required
def update_my_profile():
    user = g.user
    data = request.get_json()
    
    # Fields that can be updated from the profile page
    updateable_fields = [
        'name', 'phone', 'address', 'bio', 'emergency_contact',
        'employee_id', 'designation', 'department'
    ]
    
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
        if 'designation' in data: sa.designation = data['designation']
        if 'department' in data: sa.department = data['department']
        
    else:
        emp = Employee.query.filter_by(user_id=user.id).first()
        if not emp:
            return jsonify({"message": "Employee record not found"}), 404
            
        if 'name' in data: emp.full_name = data['name']
        if 'phone' in data: emp.phone_number = data['phone']
        if 'employee_id' in data: emp.employee_id = data['employee_id']
        if 'designation' in data: emp.designation = data['designation']
        if 'department' in data: emp.department = data['department']
        
        if 'address' in data:
            # For simplicity, we assume address_line1 for now if they only provide a string
            from models.employee_address import EmployeeAddress
            if not emp.address:
                emp.address = EmployeeAddress(employee_id=emp.id)
                db.session.add(emp.address)
            emp.address.address_line1 = data['address']
            
        if 'bio' in data: emp.bio = data['bio']
        if 'emergency_contact' in data: emp.emergency_contact = data['emergency_contact']

    db.session.commit()
    return jsonify({"success": True, "message": "Profile updated successfully"}), 200