import sys
from app import create_app
from models import db
from models.user import User
from models.employee import Employee
from config import Config

app = create_app(Config)

with app.app_context():
    # Update employee 13 (Vemireddy)
    emp = Employee.query.get(13)
    if emp:
        print(f"Current state: Name={emp.full_name}, Designation={emp.designation}, Role={emp.user.role}")
        
        # Designation: "fulltimeADMIN" as requested
        emp.designation = 'fulltimeADMIN'
        emp.employment_type = 'fulltime'
        
        # System Role: "ADMIN" so they see the sidebar change
        if emp.user:
            emp.user.role = 'ADMIN'
            emp.user.status = 'ACTIVE'
            print(f"Updating User ID {emp.user_id} to ADMIN role")
        
        db.session.commit()
        print(f"SUCCESS: Updated {emp.full_name} to fulltimeADMIN / ADMIN")
    else:
        print("ERROR: Employee 13 not found")
