from app import app
from models.employee import Employee
from models.company import Company
from models.branch import Branch
from sqlalchemy import func

with app.app_context():
    from models import db
    print("--- DATA PER COMPANY ---")
    results = db.session.query(
        Company.id, Company.company_name, 
        func.count(Employee.id)
    ).outerjoin(Employee, Company.id == Employee.company_id).group_by(Company.id).all()
    
    for cid, name, emp_count in results:
        branch_count = Branch.query.filter_by(company_id=cid).count()
        print(f"CID: {cid} | Name: {name} | Employees: {emp_count} | Branches: {branch_count}")
