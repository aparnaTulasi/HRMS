import jwt
from datetime import datetime, timedelta
import requests
import json
import sys
import os

# Adjust paths to match project structure
sys.path.append(os.getcwd())
from app import app
from config import Config

def test():
    with app.app_context():
        from models.user import User
        # Find any super admin
        sa = User.query.filter_by(role='SUPER_ADMIN').first()
        if not sa:
            print("No Super Admin found in DB.")
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
            if resp.status_code != 200:
                print(f"Error Response: {resp.text}")
                return
                
            data = resp.json()
            # print(json.dumps(data, indent=2))
            
            if data.get('success'):
                d = data['data']
                print("\n--- Verification Results ---")
                
                # Check for new keys
                checks = [
                    ('userName', d.get('userName')),
                    ('systemAlerts', d.get('systemAlerts')),
                    ('departmentData', d.get('departmentData')),
                    ('pendingRequests', d.get('pendingRequests'))
                ]
                
                all_pass = True
                for key, val in checks:
                    if val is not None:
                        print(f"✅ {key}: Present (Count: {len(val) if isinstance(val, list) else 'Value exists'})")
                    else:
                        print(f"❌ {key}: MISSING")
                        all_pass = False
                
                if all_pass:
                    print("\n🚀 ALL DASHBOARD KEYS VERIFIED SUCCESSFULLY!")
                    if d.get('systemAlerts'):
                        print("\nSample Alerts:")
                        for a in d['systemAlerts']:
                            print(f"- [{a['type']}] {a['message']}")
                else:
                    print("\n⚠️ SOME KEYS ARE MISSING!")
            
        except Exception as e:
            print(f"Error testing API: {e}")

if __name__ == "__main__":
    test()
