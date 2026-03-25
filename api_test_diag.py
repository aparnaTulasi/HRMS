from app import app
from models.user import User
import json

def test_as_user(user_id, endpoint):
    with app.app_context():
        user = User.query.get(user_id)
        if not user:
            print(f"User {user_id} not found")
            return
            
        print(f"\n--- Testing {endpoint} as {user.email} ({user.role}) ---")
        client = app.test_client()
        # We need a token, but for internal test we can mock g.user
        from flask import g
        with app.test_request_context():
            g.user = user
            # Find the view function for the endpoint
            # Actually, simpler: just call the function directly if we can
            pass

        # Since we use @token_required decorators, we should use the client and provide a real token
        # Or mock the decorator.
        # For now, let's just use the real client if we have a token.
        # Let's try to get a token for this user.
        import jwt
        from config import Config
        from datetime import datetime, timedelta
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
                if len(data['data']) > 0:
                    print(f"First Item: {json.dumps(data['data'][0], indent=2)}")
            else:
                print(f"Response: {data}")
        except:
            print(f"Raw Body: {response.data}")

if __name__ == "__main__":
    # Test as Super Admin (ID 1)
    test_as_user(1, "/api/admin/employees")
    test_as_user(1, "/api/superadmin/companies")
    test_as_user(1, "/api/superadmin/branches/map")
    
    # Test as a regular Admin or HR if exists
    with app.app_context():
        u = User.query.filter(User.role != 'SUPER_ADMIN').first()
        if u:
            test_as_user(u.id, "/api/admin/employees")
            test_as_user(u.id, "/api/superadmin/companies")
            test_as_user(u.id, "/api/superadmin/branches/map")
