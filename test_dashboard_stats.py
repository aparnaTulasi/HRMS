import jwt
from datetime import datetime, timedelta
import requests
import json
import sys

# Get secret key from config directly or hardcode fallback from config.py typically "hrms_secret_key!@#"
# But we can import it
sys.path.append('.')
from app import app
from config import Config

# Need a user id of superadmin. Let's get it from DB.
def test():
    with app.app_context():
        from models.user import User
        # Find any super admin
        sa = User.query.filter_by(role='SUPER_ADMIN').first()
        if not sa:
            print("No Super Admin found.")
            return

        print(f"Testing with Super Admin ID: {sa.id}, Email: {sa.email}")
        
        token = jwt.encode({
            'user_id': sa.id,
            'role': sa.role,
            'company_id': sa.company_id,
            'exp': datetime.utcnow() + timedelta(hours=24)
        }, Config.SECRET_KEY, algorithm="HS256")
        
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        url = "http://127.0.0.1:5000/api/superadmin/dashboard-stats"
        print(f"Making GET request to {url}")
        
        try:
            resp = requests.get(url, headers=headers)
            print(f"Status Code: {resp.status_code}")
            data = resp.json()
            print(json.dumps(data, indent=2))
            
            if data.get('success'):
                stats = data['data']['stats']
                print("\n--- Keys in Stats ---")
                print("total_companies:", stats.get('total_companies'))
                print("totalCompanies (camelCase):", stats.get('totalCompanies'))
                
                if 'totalCompanies' in stats:
                    print("\n✅ SUCCESS: camelCase keys are present in the response.")
                else:
                    print("\n❌ FAILURE: camelCase keys are missing.")
            
        except Exception as e:
            print(f"Error testing API: {e}")

if __name__ == "__main__":
    test()
