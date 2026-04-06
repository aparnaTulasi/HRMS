from app import app, db
from models.user import User
from models.company import Company
from flask import g
import json
from sqlalchemy.exc import IntegrityError

def verify_fix():
    with app.app_context():
        # Setup test company
        company = Company.query.first()
        if not company:
            print("No company found.")
            return
            
        test_email = "test_duplicate@gmail.com"
        
        # Ensure user exists for first test
        existing = User.query.filter_by(email=test_email, company_id=company.id).first()
        if not existing:
            from werkzeug.security import generate_password_hash
            u = User(email=test_email, company_id=company.id, role="EMPLOYEE", password=generate_password_hash("pass123"))
            db.session.add(u)
            db.session.commit()
            print(f"Created initial user {test_email}")
        
        from routes.permissions import invite_member_with_permissions
        with app.test_request_context('/api/superadmin/invite-member-with-permissions', 
                                      method='POST',
                                      json={
                                          "full_name": "Test User",
                                          "email": test_email,
                                          "password": "pass",
                                          "role": "EMPLOYEE",
                                          "company_id": company.id
                                      }):
            # Mock g.user
            sa = User.query.filter_by(role='SUPER_ADMIN').first()
            g.user = sa
            
            resp_data = invite_member_with_permissions()
            if isinstance(resp_data, tuple): resp = resp_data[0]
            else: resp = resp_data
            
            data = resp.get_json()
            print("\n--- Duplicate Invitation Check ---")
            print(f"Status Code: {resp.status_code}") # Should be 409
            print(f"Message: {data.get('message')}") # Should be friendly message
            
        # Verify 404 is fixed by checking route availability
        print("\n--- Route Availability Check ---")
        for rule in app.url_map.iter_rules():
            if 'invite-member-with-permissions' in rule.rule:
                print(f"Found Route: {rule.rule} (Methods: {rule.methods})")

if __name__ == "__main__":
    verify_fix()
