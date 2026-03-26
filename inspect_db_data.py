from app import app
from models import db
from models.user import User
from models.employee import Employee

with app.app_context():
    print("\n--- Current Users ---")
    users = User.query.all()
    for u in users:
        print(f"ID: {u.id}, Email: {u.email}, Role: {u.role}")

    print("\n--- Current Employees ---")
    employees = Employee.query.all()
    for e in employees:
        print(f"ID: {e.id}, User ID: {e.user_id}, Employee ID: {e.employee_id}, Name: {e.full_name}, Email: {e.company_email}")
