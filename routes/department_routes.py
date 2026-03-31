from flask import Blueprint, request, jsonify, g
from models import db
from models.department import Department
from models.company import Company
from models.employee import Employee
from utils.decorators import token_required, role_required
import logging

dept_bp = Blueprint('department_management', __name__)

@dept_bp.route('/departments', methods=['GET'])
@token_required
@role_required(['SUPER_ADMIN', 'ADMIN', 'HR'])
def list_departments():
    try:
        if g.user.role == 'SUPER_ADMIN':
            company_id = request.args.get('company_id')
            query = Department.query
            if company_id:
                query = query.filter_by(company_id=company_id)
        else:
            query = Department.query.filter_by(company_id=g.user.company_id)
        
        # Default filter: only active
        include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
        if not include_inactive:
            query = query.filter(Department.is_active == True)
            
        departments = query.all()

        return jsonify({
            "success": True,
            "data": [
                {
                    "id": d.id,
                    "department_name": d.department_name,
                    "department_code": d.department_code,
                    "company_id": d.company_id,
                    "company_name": Company.query.get(d.company_id).company_name if Company.query.get(d.company_id) else "N/A",
                    "location": d.location or "N/A",
                    "department_head": Employee.query.get(d.manager_id).full_name if d.manager_id and Employee.query.get(d.manager_id) else "N/A",
                    "manager_id": d.manager_id,
                    "is_active": d.is_active,
                    "status": d.status,
                    "description": d.description
                } for d in departments
            ]
        }), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@dept_bp.route('/departments', methods=['POST'])
@token_required
@role_required(['SUPER_ADMIN', 'ADMIN', 'HR'])
def create_department():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "No data provided"}), 400

        dept_name = data.get('department_name')
        if not dept_name:
            return jsonify({"success": False, "message": "Department name is required"}), 400

        # Determine company_id
        if g.user.role == 'SUPER_ADMIN':
            company_id = data.get('company_id')
            if not company_id:
                return jsonify({"success": False, "message": "company_id is required for Super Admin"}), 400
        else:
            company_id = g.user.company_id

        # Location and Head
        location = data.get('location')
        manager_id = data.get('manager_id') or data.get('department_head_id')

        new_dept = Department(
            department_name=dept_name,
            company_id=company_id,
            location=location,
            manager_id=manager_id,
            description=data.get('description'),
            department_code=data.get('department_code')
        )

        db.session.add(new_dept)
        db.session.commit()

        return jsonify({
            "success": True, 
            "message": "Department created successfully",
            "id": new_dept.id
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

@dept_bp.route('/departments/<int:dept_id>', methods=['PUT', 'PATCH'])
@token_required
@role_required(['SUPER_ADMIN', 'ADMIN', 'HR'])
def update_department(dept_id):
    try:
        dept = Department.query.get(dept_id)
        if not dept:
            return jsonify({"success": False, "message": "Department not found"}), 404

        # Access check
        if g.user.role != 'SUPER_ADMIN' and dept.company_id != g.user.company_id:
            return jsonify({"success": False, "message": "Unauthorized"}), 403

        data = request.get_json()
        if 'department_name' in data:
            dept.department_name = data['department_name']
        if 'location' in data:
            dept.location = data['location']
        if 'manager_id' in data:
            dept.manager_id = data['manager_id']
        if 'department_code' in data:
            dept.department_code = data['department_code']
        if 'description' in data:
            dept.description = data['description']
        if 'is_active' in data:
            dept.is_active = data['is_active']

        db.session.commit()
        return jsonify({"success": True, "message": "Department updated successfully"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

@dept_bp.route('/departments/<int:dept_id>', methods=['DELETE'])
@token_required
@role_required(['SUPER_ADMIN', 'ADMIN', 'HR'])
def deactivate_department(dept_id):
    """Mark a department as INACTIVE instead of deleting."""
    try:
        dept = Department.query.get(dept_id)
        if not dept:
            return jsonify({"success": False, "message": "Department not found"}), 404

        # Access check
        if g.user.role != 'SUPER_ADMIN' and dept.company_id != g.user.company_id:
            return jsonify({"success": False, "message": "Unauthorized"}), 403

        dept.is_active = False
        dept.status = "INACTIVE"
        db.session.commit()
        
        from utils.audit_logger import log_action
        log_action("DEACTIVATE_DEPARTMENT", "Department", dept.id, 200, meta={"name": dept.department_name})
        
        return jsonify({"success": True, "message": f"Department '{dept.department_name}' deactivated successfully"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500
