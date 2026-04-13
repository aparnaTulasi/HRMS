from app import app
from flask import g
from models.user import User
from unittest.mock import patch
import json

# Define mock before imports
def mock_decorator(f):
    return f

def verify_audit_fields():
    with app.app_context(), \
         patch('utils.decorators.token_required', mock_decorator), \
         patch('utils.decorators.role_required', lambda x: mock_decorator), \
         patch('utils.decorators.permission_required', lambda x: mock_decorator):
        
        # IMPORT ROUTES INSIDE THE PATCH
        from routes.audit_logs import get_audit_logs
        
        user = User.query.filter_by(role='SUPER_ADMIN').first()
        if not user:
            print("No Super Admin found")
            return
            
        print(f"Verifying as User: {user.email}")
        
        with app.test_request_context():
            g.user = user
            response = get_audit_logs()
            if isinstance(response, tuple):
                res_obj, status = response
                data = res_obj.get_json()
            else:
                data = response.get_json()
            
            print(f"API Response Status Code: 200 (Mocked)")
            if data.get('success'):
                logs = data.get('data', [])
                print(f"Total Logs Found: {len(logs)}")
                if logs:
                    log = logs[0]
                    print("\nSample Log Details:")
                    print(f"  - Performed By (performed_by): {log.get('performed_by')}")
                    print(f"  - Date & Time (date_time): {log.get('date_time')}")
                    print(f"  - IP Address (ip_address): {log.get('ip_address')}")
                    print(f"  - Details (details): {log.get('details')}")
                    
                    # Check critical fields
                    required = ['performed_by', 'date_time', 'ip_address', 'details']
                    missing = [f for f in required if f not in log]
                    if not missing:
                        print("\n✅ All requested fields are present in the JSON response.")
                    else:
                        print(f"\n❌ Missing fields: {missing}")
                else:
                    print("No logs found in DB to verify.")
            else:
                print(f"API Error: {data.get('message')}")

if __name__ == "__main__":
    verify_audit_fields()
