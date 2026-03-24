from app import app
from models import db
from models.company import Company
from flask import g

class MockUser:
    def __init__(self, id, role, company_id):
        self.id = id
        self.role = role
        self.company_id = company_id

with app.app_context():
    # Simulate Super Admin (User 1)
    g.user = MockUser(1, 'SUPER_ADMIN', None)
    
    if g.user.role in ['ADMIN', 'HR']:
        companies = Company.query.filter_by(id=g.user.company_id).all()
        print("Role: ADMIN/HR - Filtered")
    else:
        companies = Company.query.order_by(Company.id.desc()).all()
        print("Role: SUPER_ADMIN - All")
        
    print(f"Count: {len(companies)}")
    for c in companies:
        print(f" - Company: {c.company_name} (ID: {c.id})")
        
    # Simulate Admin (User 6)
    g.user = MockUser(6, 'ADMIN', 1)
    if g.user.role in ['ADMIN', 'HR']:
        companies = Company.query.filter_by(id=g.user.company_id).all()
        print("\nRole: ADMIN - Filtered")
    else:
        companies = Company.query.order_by(Company.id.desc()).all()
        print("\nRole: SUPER_ADMIN - All")
        
    print(f"Count: {len(companies)}")
    for c in companies:
        print(f" - Company: {c.company_name} (ID: {c.id})")
