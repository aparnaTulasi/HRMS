from app import app, db
from models.user import User
from models.company import Company

with app.app_context():
    print("=== HRMS SYSTEM CONTEXT ===")
    
    # Get any HR
    hr = User.query.filter_by(role='HR').first()
    if hr:
        print(f"HR: {hr.email}, Company ID: {hr.company_id}")
    
    # Get any MANAGER in same company
    if hr:
        mgr = User.query.filter_by(role='MANAGER', company_id=hr.company_id).first()
        if mgr:
            print(f"Manager: {mgr.email}, Company ID: {mgr.company_id}")
        else:
            print("No manager in same company found.")
    
    # Get Company
    if hr:
        comp = Company.query.get(hr.company_id)
        print(f"Company: {comp.company_name if comp else 'N/A'}")
