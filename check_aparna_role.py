from app import app
from models.user import User
from models.employee import Employee

with app.app_context():
    e = Employee.query.filter(Employee.full_name.like('%Aparna%')).first()
    if e:
        u = User.query.get(e.user_id)
        print(f"User: {u.email} | Role: {u.role} | Company ID: {u.company_id}")
    else:
        print("Employee 'Aparna' not found.")
        # Check all superadmins
        sas = User.query.filter_by(role='SUPER_ADMIN').all()
        for sa in sas:
            print(f"SA User: {sa.email} | ID: {sa.id}")
