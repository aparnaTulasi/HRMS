from app import app, db
from models.user import User
from models.employee import Employee
from models.audit_log import AuditLog
from flask import g
import json
from unittest.mock import patch

# Mock the decorator to bypass token check for testing
def mock_token_required(f):
    return f

# Patch before importing routes
with patch('utils.decorators.token_required', mock_token_required):
    from routes.audit_logs import get_audit_logs

def verify_audit_tier(role_name, company_id=1, email=None):
    with app.app_context():
        # Find a user with this role
        user = User.query.filter_by(role=role_name, company_id=company_id).first()
        if not user and email:
            user = User.query.filter_by(email=email).first()
        
        if not user:
            print(f"FAIL: Could not find user for role {role_name} in company {company_id}")
            return
            
        print(f"\n--- Testing Role: {role_name} (User: {user.email}, Company: {user.company_id}) ---")
        
        # Simulate g.user
        g.user = user
        
        with app.test_request_context():
            g.user = user
            response = get_audit_logs()
            
            # Handle tuple response (data, status)
            if isinstance(response, tuple):
                res_obj, status = response
                data = res_obj.get_json()
            else:
                data = response.get_json()
                status = 200
            
            if status >= 400:
                print(f"FAILED: Request failed with status {status}: {data.get('message')}")
                return
                
            logs = data.get('data', [])
            total = data.get('total', 0)
            print(f"SUCCESS. Total logs visible: {total}")
            
            # Sample checks
            roles_found = set(l['role'] for l in logs)
            print(f"   Roles found in logs: {roles_found}")
            
            companies_found = set()
            log_ids = [l['id'] for l in logs[:10]]
            if log_ids:
                db_logs = AuditLog.query.filter(AuditLog.id.in_(log_ids)).all()
                companies_found = set(l.company_id for l in db_logs)
                print(f"   Company IDs found in logs: {companies_found}")

            # Hierarchy Assertions
            if role_name == 'HR':
                invalid = [r for r in roles_found if r in ['ADMIN', 'SUPER_ADMIN']]
                if invalid: print(f"   ERROR: HR found logs for restricted roles: {invalid}")
                else: print("   Verified: HR only sees Manager/Employee logs.")
                
            if role_name == 'ADMIN' and len(companies_found) > 1:
                print(f"   ERROR: Admin seeing multiple companies: {companies_found}")
            elif role_name == 'ADMIN':
                print("   Verified: Admin restricted to own company.")

            if role_name == 'MANAGER':
                manager_emp = Employee.query.filter_by(user_id=user.id).first()
                sub_ids = [e.user_id for e in Employee.query.filter_by(manager_id=manager_emp.id).all()] if manager_emp else []
                allowed = [user.id] + sub_ids
                
                log_performers = set()
                if log_ids:
                    log_performers = set(l.user_id for l in db_logs if l.user_id)
                
                leaks = [p for p in log_performers if p not in allowed]
                if leaks: print(f"   ERROR: Manager seeing logs for non-subordinates: {leaks}")
                else: print("   Verified: Manager restricted to self + subordinates.")

if __name__ == "__main__":
    verify_audit_tier('SUPER_ADMIN', company_id=None, email='superadmin@hrms.com')
    verify_audit_tier('ADMIN', company_id=1)
    verify_audit_tier('HR', company_id=1)
    verify_audit_tier('MANAGER', company_id=1)
