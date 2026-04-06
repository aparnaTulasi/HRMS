from flask import Blueprint, jsonify, g, request
from models import db
from models.user import User
from models.employee import Employee
from models.super_admin import SuperAdmin
from models.profile_change_request import ProfileChangeRequest
from models.profile_change_request_item import ProfileChangeRequestItem
from constants.profile_fields import ALLOWED_PROFILE_FIELDS, ROLE_ESCALATION, FIELD_DISPLAY_NAMES
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
    
    if user.role == 'SUPER_ADMIN':
        record = SuperAdmin.query.filter_by(user_id=user.id).first()
        model_name = "SuperAdmin"
    else:
        record = Employee.query.filter_by(user_id=user.id).first()
        model_name = "Employee"

    if not record:
        return jsonify({"message": f"{model_name} record not found"}), 404

    # 1. Check if profile is locked
    is_locked = getattr(user, 'profile_locked', False)

    allowed_fields = ALLOWED_PROFILE_FIELDS.get(model_name, [])
    changes = []

    # Helper for difference detection
    def get_diffs(obj, fields, data_dict, m_name):
        diffs = []
        for field in fields:
            # Map frontend keys to model keys if necessary
            data_key = field
            if field == 'full_name' and 'name' in data_dict: data_key = 'name'
            if field == 'phone_number' and 'phone' in data_dict: data_key = 'phone'
            
            if data_key in data_dict:
                old_val = getattr(obj, field, None)
                new_val = data_dict[data_key]
                
                # Null-safe comparison
                if str(old_val or "").strip() != str(new_val or "").strip():
                    diffs.append({
                        "field_key": field,
                        "field_name": FIELD_DISPLAY_NAMES.get(field, field.replace('_', ' ').title()),
                        "model_name": m_name,
                        "old_value": str(old_val) if old_val is not None else None,
                        "new_value": str(new_val) if new_val is not None else None
                    })
        return diffs

    # Main record diffs
    changes.extend(get_diffs(record, allowed_fields, data, model_name))

    # Address diffs (if Employee)
    if model_name == "Employee" and 'address' in data:
        from models.employee_address import EmployeeAddress
        addr = record.address
        if not addr:
            # If no address exists, we'll treat it as a change if data['address'] isn't empty
            if data['address']:
                changes.append({
                    "field_key": "address_line1",
                    "field_name": "Address Line 1",
                    "model_name": "EmployeeAddress",
                    "old_value": None,
                    "new_value": data['address']
                })
        else:
            changes.extend(get_diffs(addr, ALLOWED_PROFILE_FIELDS.get("EmployeeAddress", []), {"address_line1": data['address']}, "EmployeeAddress"))

    if not changes:
        return jsonify({"success": True, "message": "No changes detected"}), 200

    # 2. Case A: Not Locked -> Direct Update
    if not is_locked:
        try:
            for change in changes:
                target_obj = record
                if change['model_name'] == "EmployeeAddress":
                    from models.employee_address import EmployeeAddress
                    if not record.address:
                        record.address = EmployeeAddress(employee_id=record.id)
                        db.session.add(record.address)
                    target_obj = record.address
                
                setattr(target_obj, change['field_key'], data.get('name') if change['field_key'] == 'full_name' else (data.get('phone') if change['field_key'] == 'phone_number' else change['new_value']))
            
            user.profile_locked = True
            db.session.commit()
            return jsonify({"success": True, "message": "Profile updated successfully (Initial Update)"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"success": False, "message": str(e)}), 500

    # 3. Case B: Locked -> Create Request
    try:
        next_approver_role = ROLE_ESCALATION.get(user.role, "HR")
        
        request_obj = ProfileChangeRequest(
            company_id=user.company_id or 1,
            requester_user_id=user.id,
            target_user_id=user.id,
            status="PENDING",
            requested_by_role=user.role,
            current_approver_role=next_approver_role,
            flow_type=f"{user.role}_TO_{next_approver_role}",
            reason=data.get('reason', 'Profile Correction')
        )
        db.session.add(request_obj)
        db.session.flush()

        for change in changes:
            item = ProfileChangeRequestItem(
                request_id=request_obj.id,
                field_key=change['field_key'],
                field_name=change['field_name'],
                model_name=change['model_name'],
                old_value=change['old_value'],
                new_value=change['new_value']
            )
            db.session.add(item)
        
        db.session.commit()
        return jsonify({
            "success": True, 
            "message": f"Profile correction request sent to {next_approver_role} for approval.",
            "request_id": request_obj.id
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500