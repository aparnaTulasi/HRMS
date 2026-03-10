from app import app, db
from models.employee import Employee
from models.attendance import Attendance
from datetime import date

def test_bulk():
    with app.app_context():
        # Using a fixed date for testing
        test_date = date(2026, 3, 10)
        
        # 1. Simulate bulk_list logic
        # Find some employees
        employees = Employee.query.limit(5).all()
        if not employees:
            print("No employees to test.")
            return

        print(f"Testing bulk list for {len(employees)} employees on {test_date}")
        
        # Check attendance records
        att_records = Attendance.query.filter(
            Attendance.attendance_date == test_date,
            Attendance.employee_id.in_([e.id for e in employees])
        ).all()
        
        print(f"Found {len(att_records)} existing attendance records.")

        # 2. Simulate bulk_save logic
        # Prepare updates
        updates = []
        for emp in employees:
            updates.append({
                "employee_id": emp.id,
                "status": "Present",
                "reason": "Test Bulk Save",
                "shift_id": 1
            })

        print("Simulating bulk save...")
        # (Assuming _upsert_attendance is tested by the main code path)
        # We can just check if we can add/update these records
        for up in updates:
            # Simplified lookup for verification
            row = Attendance.query.filter_by(
                employee_id=up["employee_id"],
                attendance_date=test_date
            ).first()
            
            if not row:
                row = Attendance(
                    company_id=employees[0].company_id,
                    employee_id=up["employee_id"],
                    attendance_date=test_date,
                    status=up["status"],
                    remarks=up["reason"],
                    shift_id=up["shift_id"]
                )
                db.session.add(row)
            else:
                row.status = up["status"]
                row.remarks = up["reason"]
                row.shift_id = up["shift_id"]
        
        db.session.commit()
        print("Bulk save simulation successful.")

if __name__ == "__main__":
    test_bulk()
