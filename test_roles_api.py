import requests
import json

BASE_URL = "http://127.0.0.1:5000/api/admin/access-control"
TOKEN = "YOUR_TOKEN_HERE" # Need a valid token

def test_roles_apis():
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    
    # 1. Create a role with permission matrix
    print("Testing role creation...")
    role_data = {
        "name": "Project Manager",
        "description": "Manages team and projects",
        "permissions": [
            "employees.view", "employees.edit",
            "attendance.view", "attendance.approve",
            "leave.view", "leave.approve"
        ]
    }
    # resp = requests.post(f"{BASE_URL}/roles", headers=headers, data=json.dumps(role_data))
    # print(resp.json())
    
    # 2. List roles
    print("Testing roles list...")
    # resp = requests.get(f"{BASE_URL}/roles", headers=headers)
    # print(resp.json())
    
    # 3. Update role
    print("Testing role update...")
    update_data = {
        "description": "Updated description",
        "permissions": ["employees.view", "payroll.view"]
    }
    # resp = requests.put(f"{BASE_URL}/roles/1", headers=headers, data=json.dumps(update_data))
    # print(resp.json())

    print("Roles & Permissions API verification logic is ready.")

if __name__ == "__main__":
    test_roles_apis()
