from app import app, db
from models.employee import Employee
from sqlalchemy import func

with app.app_context():
    depts = db.session.query(Employee.department, func.count(Employee.id)).group_by(Employee.department).all()
    print("\nDepartments found in DB:")
    for d, c in depts:
        print(f" - {d}: {c}")
