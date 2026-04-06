from app import app
from models.user import User
from models.employee import Employee
from models.branch import Branch

with app.app_context():
    cid = 3
    print(f"--- Stats for Company ID {cid} ---")
    print(f"Admins: {User.query.filter_by(company_id=cid, role='ADMIN').count()}")
    print(f"HRs: {User.query.filter_by(company_id=cid, role='HR').count()}")
    print(f"Managers: {User.query.filter_by(company_id=cid, role='MANAGER').count()}")
    print(f"Employees: {Employee.query.filter_by(company_id=cid).count()}")
    print(f"Branches: {Branch.query.filter_by(company_id=cid).count()}")
