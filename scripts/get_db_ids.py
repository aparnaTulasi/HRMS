from models import db
from models.company import Company
from models.employee import Employee
from app import app

with app.app_context():
    company = Company.query.first()
    if company:
        print(f"Company ID: {company.id}")
        emp = Employee.query.filter_by(company_id=company.id).first()
        if emp:
            print(f"Employee ID: {emp.id}")
            print(f"Employee Name: {emp.full_name}")
        else:
            print("No employees found for this company.")
    else:
        print("No companies found in the database.")
