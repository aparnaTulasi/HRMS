from app import app
from flask import g
from models.user import User
from unittest.mock import patch

def test_apis():
    # Mock the decorators to bypass checks for testing
    def mock_decorator(f):
        return f

    with app.app_context():
        # Get a super admin
        user = User.query.filter_by(role='SUPER_ADMIN').first()
        if not user:
            print("No Super Admin found for testing")
            # Try any admin
            user = User.query.filter_by(role='ADMIN').first()
            
        if not user:
            print("No Admin found for testing")
            return
            
        print(f"Testing as User: {user.email} (Role: {user.role})")
        
        with patch('utils.decorators.token_required', mock_decorator), \
             patch('utils.decorators.role_required', lambda x: mock_decorator), \
             patch('utils.decorators.permission_required', lambda x: mock_decorator):
            
            from routes.company import list_companies
            from routes.admin import get_employees
            
            # Test Companies API
            with app.test_request_context():
                g.user = user
                response = list_companies()
                if isinstance(response, tuple):
                    res_obj, status = response
                    data = res_obj.get_json()
                else:
                    data = response.get_json()
                    status = 200
                
                print(f"\nGET /api/superadmin/companies Status: {status}")
                if status == 200:
                    companies = data.get('data', [])
                    print(f"Total Companies returned: {len(companies)}")
                    if companies:
                        print(f"Sample Company: {companies[0].get('company_name')}")
                else:
                    print(f"Error: {data.get('message')}")

            # Test Employees API
            with app.test_request_context():
                g.user = user
                response = get_employees()
                if isinstance(response, tuple):
                    res_obj, status = response
                    data = res_obj.get_json()
                else:
                    data = response.get_json()
                    status = 200
                
                print(f"\nGET /api/admin/employees Status: {status}")
                if status == 200:
                    employees = data.get('data', [])
                    print(f"Total Employees returned: {len(employees)}")
                    if employees:
                        print(f"Sample Employee: {employees[0].get('name')}")
                else:
                    print(f"Error: {data.get('message')}")

if __name__ == "__main__":
    test_apis()
