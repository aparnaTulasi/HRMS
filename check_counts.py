from app import app
from models.employee import Employee
from datetime import datetime

with app.app_context():
    print(f"Total Employees in DB: {Employee.query.count()}")
    now = datetime.utcnow()
    start_of_month = datetime(now.year, now.month, 1).date()
    
    employees = Employee.query.all()
    print("Employee Details:")
    new_count = 0
    for emp in employees:
        is_new = emp.date_of_joining >= start_of_month if emp.date_of_joining else False
        if is_new: new_count += 1
        print(f"- ID: {emp.id}, Name: {emp.full_name}, Dept: {emp.department}, Joined: {emp.date_of_joining}, New: {is_new}")
    
    print(f"Calculated New This Month: {new_count}")
