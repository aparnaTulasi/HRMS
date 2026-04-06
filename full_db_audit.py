from app import app
from models import db
from models.user import User
from models.employee import Employee
from models.company import Company
from models.branch import Branch
from sqlalchemy import func

with app.app_context():
    print(f"--- DB Audit ---")
    print(f"Company Count: {Company.query.count()}")
    print(f"Branch Count: {Branch.query.count()}")
    print(f"User Count: {User.query.count()}")
    print(f"Employee Count: {Employee.query.count()}")
    
    roles = db.session.query(User.role, func.count(User.id)).group_by(User.role).all()
    print(f"Roles in DB: {[ (role, '|' + role + '|') for role, count in roles ]}")
    
    admins = User.query.filter_by(role='ADMIN').count()
    print(f"Count of role='ADMIN': {admins}")
    
    hrs = User.query.filter_by(role='HR').count()
    print(f"Count of role='HR': {hrs}")
    
    # Check if 'ADMIN' or 'admin' or 'Admin'
    for r in ['ADMIN', 'admin', 'Admin', 'HR', 'hr', 'Hr', 'SUPER_ADMIN', 'super_admin']:
        count = User.query.filter_by(role=r).count()
        if count > 0:
            print(f"Count for role='{r}': {count}")

    # Check Attendance
    from models.attendance import Attendance
    from datetime import date
    today = date.today()
    att_count = Attendance.query.filter_by(attendance_date=today).count()
    print(f"Attendance Today ({today}): {att_count}")
    
    all_att = Attendance.query.count()
    print(f"Total Attendance Records: {all_att}")
