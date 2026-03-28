from app import app, db
from models.employee import Employee
from models.user import User

def check_employees():
    with app.app_context():
        print("Checking Employees in MySQL...")
        emps = Employee.query.all()
        for emp in emps:
            user = User.query.get(emp.user_id)
            print(f"ID: {emp.id}, Name: {emp.full_name}, Email: {user.email if user else 'N/A'}")

if __name__ == "__main__":
    check_employees()
