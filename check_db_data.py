from app import app
from models import db
from models.employee import Employee
from models.company import Company
from models.branch import Branch

with app.app_context():
    print("--- COMPANIES ---")
    companies = Company.query.all()
    for c in companies:
        print(f"ID: {c.id}, Name: {c.company_name}, Code: {c.company_code}")
    
    print("\n--- EMPLOYEES ---")
    employees = Employee.query.limit(10).all()
    for e in employees:
        print(f"ID: {e.id}, CID: {e.company_id}, Name: {e.full_name}, Email: {e.company_email}")

    print("\n--- BRANCHES ---")
    branches = Branch.query.all()
    for b in branches:
        print(f"ID: {b.id}, CID: {b.company_id}, Name: {b.branch_name}, Lat: {b.latitude}, Lng: {b.longitude}")
