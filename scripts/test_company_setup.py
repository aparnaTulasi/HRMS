import requests
import json

BASE_URL = "http://127.0.0.1:5000/api"

# Configuration - Update these to match what you created in Phase 1
COMPANY_ADMIN_EMAIL = "admin@techsol.com" # Or admin@futureinvo.com
COMPANY_ADMIN_PASSWORD = "admin123"
COMPANY_ID = 1  # The ID of the company created in Phase 1

def run_company_setup():
    print("🚀 Starting Phase 2: Company Setup...")
    
    # 1. Login as Company Admin
    print(f"\n1️⃣  Logging in as Company Admin ({COMPANY_ADMIN_EMAIL})...")
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json={
            "email": COMPANY_ADMIN_EMAIL,
            "password": COMPANY_ADMIN_PASSWORD
        })
        
        if response.status_code == 200:
            print("   ✅ Login Successful!")
            admin_token = response.json().get('token')
        else:
            print(f"   ❌ Login Failed: {response.text}")
            return
    except Exception as e:
        print(f"   ❌ Connection Error: {e}")
        return

    # 2. Register HR
    print(f"\n2️⃣  Registering HR User for Company ID {COMPANY_ID}...")
    hr_data = {
        "email": "hr@techsol.com",
        "password": "hrpassword123",
        "role": "HR",
        "first_name": "Human",
        "last_name": "Resource",
        "company_id": COMPANY_ID
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/register", json=hr_data)
        if response.status_code in [200, 201]:
            print("   ✅ HR Registration Successful!")
        elif response.status_code == 409:
            print("   ⚠️  HR User already exists.")
        else:
            print(f"   ❌ Registration Failed: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # 3. Login as HR
    print("\n3️⃣  Logging in as HR...")
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json={"email": hr_data['email'], "password": hr_data['password']})
        if response.status_code == 200:
            print(f"   ✅ HR Login Successful! Token: {response.json().get('token')[:20]}...")
        else:
            print(f"   ❌ HR Login Failed: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    run_company_setup()