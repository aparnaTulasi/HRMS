from app import app, db
from models.employee import Employee
from models.user import User
from models.shift import Shift, ShiftAssignment
from datetime import date, time

def test_details():
    with app.app_context():
        # Find a real employee to test with
        emp = Employee.query.first()
        if not emp:
            print("No employees found to test.")
            return

        print(f"Found employee: {emp.full_name} (Code: {emp.employee_id})")
        
        # Check if they have a shift assignment
        assignment = ShiftAssignment.query.filter_by(employee_id=emp.id).first()
        if not assignment:
            # Create a dummy shift if none exists
            shift = Shift.query.first()
            if not shift:
                shift = Shift(
                    company_id=emp.company_id,
                    shift_name="General Shift",
                    start_time=time(9, 0),
                    end_time=time(18, 0)
                )
                db.session.add(shift)
                db.session.flush()
            
            assignment = ShiftAssignment(
                company_id=emp.company_id,
                employee_id=emp.id,
                shift_id=shift.shift_id,
                start_date=date(2025, 1, 1)
            )
            db.session.add(assignment)
            db.session.commit()
            print(f"Created dummy shift assignment for {emp.full_name}")

        # Now we can test the logic (simulating the route logic)
        today = date.today()
        assignment = ShiftAssignment.query.filter(
            ShiftAssignment.employee_id == emp.id,
            ShiftAssignment.start_date <= today,
            (ShiftAssignment.end_date == None) | (ShiftAssignment.end_date >= today)
        ).first()

        if assignment:
            print(f"Current Shift: {assignment.shift.shift_name} ({assignment.shift.start_time}-{assignment.shift.end_time})")
        else:
            print("No active shift assignment found for today.")

if __name__ == "__main__":
    test_details()
