from flask import Blueprint, request, jsonify, g
import sqlite3
import os
from models.master import db, UserMaster, Company
from models.rbac import Role
from utils.decorators import jwt_required

hr_bp = Blueprint("hr", __name__)

def get_tenant_conn(db_name):
    """Helper to connect to tenant database"""
    db_path = os.path.join("tenants", f"{db_name}.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# -------------------------
# VIEW ALL EMPLOYEES
# -------------------------
@hr_bp.route("/employees", methods=["GET"])
@jwt_required(roles=[Role.HR_MANAGER.value, Role.ADMIN.value])
def get_employees():
    user = UserMaster.query.get(g.user_id)
    company = Company.query.get(user.company_id)
    
    conn = get_tenant_conn(company.db_name)
    cursor = conn.cursor()
    
    query = """
        SELECT e.id, e.first_name, e.last_name, e.email, e.phone_number, e.status, 
               j.department, j.designation
        FROM hrms_employee e
        LEFT JOIN hrms_job_details j ON e.id = j.employee_id
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        result.append({
            "id": row["id"],
            "first_name": row["first_name"],
            "last_name": row["last_name"],
            "email": row["email"],
            "phone": row["phone_number"],
            "status": row["status"],
            "department": row["department"],
            "designation": row["designation"]
        })
    
    return jsonify(result), 200

# -------------------------
# VIEW SINGLE EMPLOYEE
# -------------------------
@hr_bp.route("/employee/<int:emp_id>", methods=["GET"])
@jwt_required(roles=[Role.HR_MANAGER.value, Role.ADMIN.value])
def get_employee(emp_id):
    user = UserMaster.query.get(g.user_id)
    company = Company.query.get(user.company_id)
    
    conn = get_tenant_conn(company.db_name)
    cursor = conn.cursor()
    
    query = """
        SELECT e.id, e.first_name, e.last_name, e.email, e.phone_number, e.status, e.date_of_birth, e.gender,
               j.department, j.designation, j.salary, j.join_date, j.job_title
        FROM hrms_employee e
        LEFT JOIN hrms_job_details j ON e.id = j.employee_id
        WHERE e.id = ?
    """
    cursor.execute(query, (emp_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return jsonify({"error": "Employee not found"}), 404
        
    data = {
        "id": row["id"],
        "first_name": row["first_name"],
        "last_name": row["last_name"],
        "email": row["email"],
        "phone": row["phone_number"],
        "status": row["status"],
        "dob": row["date_of_birth"],
        "gender": row["gender"],
        "department": row["department"],
        "designation": row["designation"],
        "salary": row["salary"],
        "join_date": row["join_date"],
        "job_title": row["job_title"]
    }
    return jsonify(data), 200

# -------------------------
# UPDATE EMPLOYEE
# -------------------------
@hr_bp.route("/employee/<int:emp_id>", methods=["PUT"])
@jwt_required(roles=[Role.HR_MANAGER.value, Role.ADMIN.value])
def update_employee(emp_id):
    data = request.get_json()
    user = UserMaster.query.get(g.user_id)
    company = Company.query.get(user.company_id)
    
    conn = get_tenant_conn(company.db_name)
    cursor = conn.cursor()
    
    try:
        # Update Employee Basic Info
        if any(k in data for k in ['first_name', 'last_name', 'phone', 'dob', 'gender']):
            fields = []
            values = []
            if 'first_name' in data: fields.append("first_name = ?"); values.append(data['first_name'])
            if 'last_name' in data: fields.append("last_name = ?"); values.append(data['last_name'])
            if 'phone' in data: fields.append("phone_number = ?"); values.append(data['phone'])
            if 'dob' in data: fields.append("date_of_birth = ?"); values.append(data['dob'])
            if 'gender' in data: fields.append("gender = ?"); values.append(data['gender'])
            
            values.append(emp_id)
            cursor.execute(f"UPDATE hrms_employee SET {', '.join(fields)} WHERE id = ?", tuple(values))
            
        # Update Job Details
        if any(k in data for k in ['department', 'designation', 'salary', 'join_date', 'job_title']):
            fields = []
            values = []
            if 'department' in data: fields.append("department = ?"); values.append(data['department'])
            if 'designation' in data: fields.append("designation = ?"); values.append(data['designation'])
            if 'salary' in data: fields.append("salary = ?"); values.append(data['salary'])
            if 'join_date' in data: fields.append("join_date = ?"); values.append(data['join_date'])
            if 'job_title' in data: fields.append("job_title = ?"); values.append(data['job_title'])
            
            values.append(emp_id)
            
            # Check if job details exist
            cursor.execute("SELECT job_id FROM hrms_job_details WHERE employee_id = ?", (emp_id,))
            if cursor.fetchone():
                cursor.execute(f"UPDATE hrms_job_details SET {', '.join(fields)} WHERE employee_id = ?", tuple(values))
        
        conn.commit()
        return jsonify({"message": "Employee updated successfully"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

# -------------------------
# DELETE EMPLOYEE
# -------------------------
@hr_bp.route("/employee/<int:emp_id>", methods=["DELETE"])
@jwt_required(roles=[Role.HR_MANAGER.value, Role.ADMIN.value])
def delete_employee(emp_id):
    user = UserMaster.query.get(g.user_id)
    company = Company.query.get(user.company_id)
    
    conn = get_tenant_conn(company.db_name)
    cursor = conn.cursor()
    
    try:
        # Get email to delete from Master DB
        cursor.execute("SELECT email FROM hrms_employee WHERE id = ?", (emp_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Employee not found"}), 404
        
        email = row["email"]
        
        # Delete from Tenant DB (Cascade manually if needed)
        cursor.execute("DELETE FROM hrms_job_details WHERE employee_id = ?", (emp_id,))
        cursor.execute("DELETE FROM hrms_bank_details WHERE employee_id = ?", (emp_id,))
        cursor.execute("DELETE FROM hrms_address_details WHERE employee_id = ?", (emp_id,))
        cursor.execute("DELETE FROM hrms_employee WHERE id = ?", (emp_id,))
        cursor.execute("DELETE FROM hrms_users WHERE email = ?", (email,))
        
        # Delete from Master DB
        master_user = UserMaster.query.filter_by(email=email).first()
        if master_user:
            db.session.delete(master_user)
            db.session.commit()
            
        conn.commit()
        return jsonify({"message": "Employee deleted successfully"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()