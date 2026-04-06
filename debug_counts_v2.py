from app import app
from models import db
from models.user import User
from models.employee import Employee
from sqlalchemy import func

with app.app_context():
    roles = db.session.query(User.role, func.count(User.id)).group_by(User.role).all()
    print(f"Roles in User Table: {roles}")
    
    total_emp = Employee.query.count()
    print(f"Total Employees: {total_emp}")
    
    from models.company import Company
    from models.branch import Branch
    print(f"Total Companies: {Company.query.count()}")
    print(f"Total Branches: {Branch.query.count()}")
    
    # Check if there are any employees with role matching
    for role, count in roles:
        role_upper = role.upper()
        if role_upper == 'ADMIN':
            print(f"ADMIN count: {count}")
        elif role_upper == 'HR':
            print(f"HR count: {count}")
        elif role_upper == 'MANAGER':
            print(f"MANAGER count: {count}")
        elif role_upper == 'EMPLOYEE':
            print(f"EMPLOYEE count: {count}")
