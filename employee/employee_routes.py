from flask import Blueprint, request, jsonify, g
from models.master import Company, UserMaster, db
from utils.auth_utils import login_required, get_tenant_db_connection
import sqlite3
from datetime import datetime
import os
from config import EMPLOYEE_DB_FOLDER
from models.master_employee import Employee

employee_bp = Blueprint("employee", __name__)

def ensure_attendance_schema(conn):
    """Ensure attendance table exists"""
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER,
            date DATE,
            clock_in TIME,
            clock_out TIME,
            status TEXT,
            FOREIGN KEY(employee_id) REFERENCES hrms_employee(id)
        )
    """)
    conn.commit()

@employee_bp.route("/profile", methods=["GET"])
@login_required
def get_profile():
    """Get logged-in employee's profile details"""
    company = Company.query.get(g.company_id)
    if not company:
        return jsonify({"error": "Company not found"}), 404
        
    # Find Employee ID from Master
    master_emp = Employee.query.filter_by(email=g.email).first()
    if not master_emp:
        return jsonify({"error": "Employee record not found"}), 404
        
    db_path = os.path.join(EMPLOYEE_DB_FOLDER, f"emp_{master_emp.id}.db")
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        cur.execute("SELECT * FROM personal_info LIMIT 1")
        p = cur.fetchone()
        cur.execute("SELECT * FROM job_details LIMIT 1")
        j = cur.fetchone()
        cur.execute("SELECT * FROM bank_details LIMIT 1")
        b = cur.fetchone()
        cur.execute("SELECT * FROM address_details LIMIT 1")
        a = cur.fetchone()
        
        conn.close()
        
        profile = {
            "personal": {
                "first_name": p[1] if p else "",
                "last_name": p[2] if p else "",
                "email": p[3] if p else "",
                "phone": p[4] if p else "",
                "status": p[7] if p else ""
            },
            "job": {
                "title": j[1] if j else "",
                "department": j[2] if j else "",
                "designation": j[3] if j else "",
                "salary": j[4] if j else 0
            },
            "bank": {
                "name": b[1] if b else "",
                "account_number": b[2] if b else ""
            },
            "address": {
                "city": a[2] if a else "",
                "country": a[5] if a else ""
            }
        }
        
        return jsonify(profile)
        
    except sqlite3.Error as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@employee_bp.route("/<int:user_id>", methods=["DELETE"])
@login_required
def delete_employee(user_id):
    current_user = UserMaster.query.get(g.user_id)

    # Only ADMIN or HR can delete employees
    if current_user.role not in ["ADMIN", "HR_MANAGER"]:
        return jsonify({"error": "Permission denied"}), 403

    user = UserMaster.query.get(user_id)

    if not user:
        return jsonify({"error": "Employee not found"}), 404

    if user.role != "EMPLOYEE":
        return jsonify({"error": "Only employees can be deleted"}), 400

    # Company check
    if user.company_id != current_user.company_id:
        return jsonify({"error": "Cross-company delete not allowed"}), 403

    # --- Tenant DB Cleanup ---
    try:
        company = Company.query.get(user.company_id)
        if company:
            conn = get_tenant_db_connection(company.db_name)
            if conn:
                cur = conn.cursor()
                # Get employee_id from user_id
                cur.execute("SELECT id FROM hrms_employee WHERE user_id = ?", (user_id,))
                row = cur.fetchone()
                if row:
                    emp_id = row[0]
                    cur.execute("DELETE FROM hrms_job_details WHERE employee_id = ?", (emp_id,))
                    cur.execute("DELETE FROM hrms_bank_details WHERE employee_id = ?", (emp_id,))
                    cur.execute("DELETE FROM hrms_address_details WHERE employee_id = ?", (emp_id,))
                    cur.execute("DELETE FROM attendance WHERE employee_id = ?", (emp_id,))
                    cur.execute("DELETE FROM hrms_employee WHERE id = ?", (emp_id,))
                
                # Delete from hrms_users in tenant DB
                cur.execute("DELETE FROM hrms_users WHERE email = ?", (user.email,))
                conn.commit()
                conn.close()
    except Exception as e:
        print(f"Error cleaning tenant DB: {e}")

    db.session.delete(user)
    db.session.commit()

    return jsonify({"message": "Employee deleted successfully"}), 200

@employee_bp.route("/attendance", methods=["POST"])
@login_required
def mark_attendance():
    """Mark attendance (Clock In / Clock Out)"""
    company = Company.query.get(g.company_id)
    
    try:
        conn = get_tenant_db_connection(company.db_name)
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
            
        ensure_attendance_schema(conn)
        cur = conn.cursor()
        
        # Get employee_id from user_id
        cur.execute("SELECT id FROM hrms_employee WHERE user_id = ?", (g.user_id,))
        emp_row = cur.fetchone()
        
        if not emp_row:
            conn.close()
            return jsonify({"error": "Employee record not found"}), 404
            
        employee_id = emp_row[0]
        today = datetime.now().strftime("%Y-%m-%d")
        now_time = datetime.now().strftime("%H:%M:%S")
        
        # Check existing record for today
        cur.execute("SELECT id, clock_in, clock_out FROM attendance WHERE employee_id = ? AND date = ?", (employee_id, today))
        record = cur.fetchone()
        
        response_data = {}
        status_code = 200
        
        if not record:
            # Clock In
            cur.execute("INSERT INTO attendance (employee_id, date, clock_in, status) VALUES (?, ?, ?, 'PRESENT')", 
                       (employee_id, today, now_time))
            response_data = {"message": "Clocked IN successfully", "time": now_time, "type": "CLOCK_IN"}
        elif record[1] and not record[2]:
            # Clock Out
            cur.execute("UPDATE attendance SET clock_out = ? WHERE id = ?", (now_time, record[0]))
            response_data = {"message": "Clocked OUT successfully", "time": now_time, "type": "CLOCK_OUT"}
        else:
            # Already completed
            response_data = {
                "message": "Attendance already completed for today", 
                "clock_in": record[1], 
                "clock_out": record[2]
            }
            status_code = 400
            
        conn.commit()
        conn.close()
        return jsonify(response_data), status_code
        
    except sqlite3.Error as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500