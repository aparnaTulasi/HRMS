from app import app, db
from models.user import User
from models.employee import Employee
from models.attendance import Attendance
from datetime import date, datetime
from flask import g
import json

def verify_my_attendance():
    with app.app_context():
        # 1. Setup
        sa = User.query.filter_by(role='SUPER_ADMIN').first()
        if not sa:
            print("No Super Admin found.")
            return

        g.user = sa
        emp = Employee.query.filter_by(user_id=sa.id).first()
        
        # Create a dummy employee record if none exists for SA
        if not emp:
            print("Creating dummy employee profile for Super Admin for testing...")
            from models.company import Company
            co = Company.query.first()
            emp = Employee(
                user_id=sa.id,
                company_id=co.id if co else 1,
                employee_id="SA-TEST",
                full_name="Super Admin",
                company_email=sa.email
            )
            db.session.add(emp)
            db.session.commit()

        # Create a dummy attendance record for today
        today = date.today()
        att = Attendance.query.filter_by(employee_id=emp.id, attendance_date=today).first()
        if not att:
            att = Attendance(
                company_id=emp.company_id,
                employee_id=emp.id,
                attendance_date=today,
                status="Present",
                punch_in_time=datetime.now().replace(hour=9, minute=0),
                punch_out_time=datetime.now().replace(hour=18, minute=0)
            )
            db.session.add(att)
            db.session.commit()

        # 2. Test the API logic
        from routes.attendance import my_attendance
        with app.test_request_context('/api/attendance/me'):
            resp_data = my_attendance()
            # If it returns a tuple (response, status_code)
            if isinstance(resp_data, tuple):
                resp, code = resp_data
            else:
                resp = resp_data
                code = 200
                
            data = resp.get_json()
            
            print("\n--- API Response Verification ---")
            print(f"Status Code: {code}")
            print(f"Success: {data.get('success')}")
            print(f"Records Count: {len(data.get('attendance', []))}")
            if data.get('attendance'):
                first = data['attendance'][0]
                print(f"Sample Record: {json.dumps(first, indent=2)}")
                
                # Check formatting
                print(f"\nVerification:")
                print(f"  - LoginAt format: {first.get('loginAt')}")
                print(f"  - Date format: {first.get('date')}")
                print(f"  - LoggedTime format: {first.get('loggedTime')}")

if __name__ == "__main__":
    verify_my_attendance()
