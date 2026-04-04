from app import app, db
from models.user import User
from models.company import Company
import requests
import json
import traceback

def test_rbac():
    with app.app_context():
        # 1. Get or Create Super Admin
        sa = User.query.filter_by(role='SUPER_ADMIN').first()
        if not sa:
            print("No Super Admin found. Creating one...")
            sa = User(email='superadmin@test.com', password='password', role='SUPER_ADMIN', status='ACTIVE')
            db.session.add(sa)
            db.session.commit()
        
        # 2. Get a Company
        company = Company.query.first()
        if not company:
            print("No Company found. Creating one...")
            company = Company(company_name='Test Co', company_code='TC', subdomain='test')
            db.session.add(company)
            db.session.commit()

        # 3. Create Token
        import jwt
        from config import Config
        from datetime import datetime, timedelta
        
        token = jwt.encode({
            'user_id': sa.id,
            'role': sa.role,
            'company_id': sa.company_id,
            'exp': datetime.utcnow() + timedelta(hours=24)
        }, Config.SECRET_KEY, algorithm="HS256")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        print(f"Testing with Token: {token[:20]}...")

        # 4. Test GET Modules
        print("\n--- Testing GET Modules ---")
        with app.test_client() as client:
            resp = client.get('/api/superadmin/permissions/modules', headers=headers)
            print(f"Status: {resp.status_code}")
            print(f"Data: {json.dumps(resp.get_json(), indent=2)}")

        try:
            # 5. Test POST Invite
            print("\n--- Testing POST Invite ---")
            payload = {
                "full_name": "Test Member",
                "email": "testmember@example.com",
                "password": "member_password",
                "role": "ADMIN",
                "company_id": company.id,
                "permissions": {
                    "Dashboard": ["VIEW"],
                    "Payroll": ["VIEW", "EDIT"]
                }
            }
            with app.test_client() as client:
                resp = client.post('/api/superadmin/invite-member-with-permissions', 
                                   headers=headers, 
                                   json=payload)
                print(f"Status: {resp.status_code}")
                data = resp.get_json()
                print(f"Data: {json.dumps(data, indent=2)}")
                
                if resp.status_code == 201:
                    user_id = data['data']['user_id']
                    
                    # 6. Test GET User Permissions
                    print(f"\n--- Testing GET User Permissions for ID {user_id} ---")
                    resp = client.get(f'/api/superadmin/user-permissions/{user_id}', headers=headers)
                    print(f"Status: {resp.status_code}")
                    print(f"Data: {json.dumps(resp.get_json(), indent=2)}")
        except Exception:
            traceback.print_exc()

if __name__ == "__main__":
    test_rbac()
