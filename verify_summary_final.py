from app import app, db
from models.user import User
from models.employee import Employee
from models.attendance import Attendance
from datetime import date, datetime, timedelta
from flask import g
import json

def verify_summary_api():
    with app.app_context():
        # Setup SA
        sa = User.query.filter_by(role='SUPER_ADMIN').first()
        if not sa:
            print("No Super Admin found.")
            return
        
        g.user = sa
        emp = Employee.query.filter_by(user_id=sa.id).first()
        if not emp:
            print("SA has no employee profile, creating one...")
            from models.company import Company
            co = Company.query.first()
            emp = Employee(user_id=sa.id, company_id=co.id if co else 1, employee_id="SA-001", full_name="Super Admin")
            db.session.add(emp)
            db.session.commit()

        # Add some records
        today = date.today()
        for i in range(3):
            d = today - timedelta(days=i)
            if not Attendance.query.filter_by(employee_id=emp.id, attendance_date=d).first():
                att = Attendance(
                    company_id=emp.company_id,
                    employee_id=emp.id,
                    attendance_date=d,
                    status="Present",
                    punch_in_time=datetime.combine(d, datetime.min.time()).replace(hour=9),
                    punch_out_time=datetime.combine(d, datetime.min.time()).replace(hour=18)
                )
                db.session.add(att)
        db.session.commit()

        from routes.attendance import get_my_attendance_summary
        with app.test_request_context('/api/attendance/my-summary'):
            resp_data = get_my_attendance_summary()
            if isinstance(resp_data, tuple): resp = resp_data[0]
            else: resp = resp_data
            
            data = resp.get_json()
            print("\n--- Summary API Response Verification ---")
            print(f"Success: {data.get('success')}")
            if data.get('data'):
                s = data['data']['summary']
                print(f"Monthly Summary: {s}")
                print(f"Trend Labels: {data['data']['trend']['labels']}")
                print(f"Trend Present: {data['data']['trend']['present']}")
                print(f"Overview Count: {len(data['data']['overview'])}")
            else:
                print("Error: 'data' field missing in response")

if __name__ == "__main__":
    verify_summary_api()
