from flask import Blueprint, request, jsonify, g
from models.master import Company
from utils.auth_utils import login_required, get_tenant_db_connection
import sqlite3
from datetime import datetime

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
        
    try:
        conn = get_tenant_db_connection(company.db_name)
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
            
        cur = conn.cursor()
        
        # Fetch employee details joined with other tables
        query = """
            SELECT 
                e.id, e.first_name, e.last_name, e.email, e.phone_number, e.gender, e.date_of_birth, e.status,
                j.job_title, j.department, j.designation, j.join_date, j.salary,
                b.bank_name, b.account_number, b.ifsc_code,
                a.city, a.state, a.country, a.zip, a.address_type
            FROM hrms_employee e
            LEFT JOIN hrms_job_details j ON e.id = j.employee_id
            LEFT JOIN hrms_bank_details b ON e.id = b.employee_id
            LEFT JOIN hrms_address_details a ON e.id = a.employee_id
            WHERE e.user_id = ?
        """
        
        cur.execute(query, (g.user_id,))
        row = cur.fetchone()
        conn.close()
        
        if not row:
            return jsonify({"error": "Employee profile not found"}), 404
            
        profile = {
            "personal": {
                "id": row[0],
                "full_name": f"{row[1]} {row[2]}",
                "first_name": row[1],
                "last_name": row[2],
                "email": row[3],
                "phone": row[4],
                "gender": row[5],
                "dob": row[6],
                "status": row[7]
            },
            "job": {
                "title": row[8],
                "department": row[9],
                "designation": row[10],
                "join_date": row[11],
                "salary": row[12]
            },
            "bank": {
                "name": row[13],
                "account_number": row[14],
                "ifsc": row[15]
            },
            "address": {
                "city": row[16],
                "state": row[17],
                "country": row[18],
                "zip": row[19],
                "type": row[20]
            }
        }
        
        return jsonify(profile)
        
    except sqlite3.Error as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

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