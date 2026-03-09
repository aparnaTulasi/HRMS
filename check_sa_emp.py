from app import app, db
from models.user import User
from models.employee import Employee

with app.app_context():
    user = User.query.filter_by(email='dittakavijaya@gmail.com').first()
    if user:
        emp = Employee.query.filter_by(user_id=user.id).first()
        print(f"User ID: {user.id}, Role: {user.role}")
        print(f"Employee Record: {emp.id if emp else 'None'}")
    else:
        print("User not found")
