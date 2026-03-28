import requests
import json

BASE_URL = "http://127.0.0.1:5000/api/admin/access-control"
TOKEN = "YOUR_TOKEN_HERE" # Need a valid token

def test_access_control_apis():
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    
    # 1. List users
    print("Testing users list...")
    # resp = requests.get(f"{BASE_URL}/users", headers=headers)
    # print(resp.json())
    
    # 2. Create a user with permissions
    print("Testing user creation...")
    user_data = {
        "email": "testuser@example.com",
        "username": "testuser123",
        "password": "securepassword",
        "role": "Employee",
        "permissions": ["view_dashboard", "manage_leave"]
    }
    # resp = requests.post(f"{BASE_URL}/users", headers=headers, data=json.dumps(user_data))
    # print(resp.json())
    
    # 3. Toggle status
    print("Testing status toggle...")
    # resp = requests.patch(f"{BASE_URL}/users/1/status", headers=headers, data=json.dumps({"status": "INACTIVE"}))
    # print(resp.json())

    print("Access Control API verification logic is ready.")

if __name__ == "__main__":
    test_access_control_apis()
