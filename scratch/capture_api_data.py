from app import app
from flask import g
from models.user import User
from unittest.mock import patch
import json

def capture_api_data():
    def mock_decorator(f):
        return f

    with app.app_context():
        user = User.query.filter_by(role='SUPER_ADMIN').first()
        if not user:
            user = User.query.filter_by(role='ADMIN').first()
            
        if not user:
            print("No Admin found")
            return
            
        with patch('utils.decorators.token_required', mock_decorator), \
             patch('utils.decorators.role_required', lambda x: mock_decorator), \
             patch('utils.decorators.permission_required', lambda x: mock_decorator):
            
            from routes.admin import get_employees
            with app.test_request_context():
                g.user = user
                response = get_employees()
                if isinstance(response, tuple):
                    res_obj, status = response
                    data = res_obj.get_json()
                else:
                    data = response.get_json()
                
                with open('scratch/employees_api_response.json', 'w') as f:
                    json.dump(data, f, indent=2)
                print(f"Captured {len(data.get('data', []))} employees to scratch/employees_api_response.json")

            from routes.company import list_companies
            with app.test_request_context():
                g.user = user
                response = list_companies()
                if isinstance(response, tuple):
                    res_obj, status = response
                    data = res_obj.get_json()
                else:
                    data = response.get_json()
                
                with open('scratch/companies_api_response.json', 'w') as f:
                    json.dump(data, f, indent=2)
                print(f"Captured {len(data.get('data', []))} companies to scratch/companies_api_response.json")

if __name__ == "__main__":
    capture_api_data()
