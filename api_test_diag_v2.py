from app import app
from models.user import User
import json
import jwt
from config import Config
from datetime import datetime, timedelta

def test_as_user(user_id, endpoint):
    with app.app_context():
        user = User.query.get(user_id)
        if not user:
            print(f"User {user_id} not found")
            return
            
        print(f"\n--- Testing {endpoint} as {user.email} (Role: {user.role}, CoID: {user.company_id}) ---")
        client = app.test_client()
        
        token = jwt.encode({
            'user_id': user.id,
            'role': user.role,
            'company_id': user.company_id,
            'exp': datetime.utcnow() + timedelta(hours=1)
        }, Config.SECRET_KEY, algorithm="HS256")
        
        headers = {'Authorization': f'Bearer {token}'}
        response = client.get(endpoint, headers=headers)
        print(f"Status: {response.status_code}")
        try:
            data = response.get_json()
            if data and 'data' in data:
                print(f"Count: {len(data['data'])}")
            else:
                print(f"Response: {data}")
        except:
            print(f"Raw Body: {response.data}")

if __name__ == "__main__":
    # Test as ADMIN of CID 1 (ID 6)
    test_as_user(6, "/api/admin/employees")
    test_as_user(6, "/api/superadmin/companies")
    test_as_user(6, "/api/superadmin/branches/map")
