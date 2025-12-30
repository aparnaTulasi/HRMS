import requests
import json
import uuid
import sys

# Configuration
BASE_URL = "http://127.0.0.1:5000/api"

def print_header(title):
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def print_response(response, action):
    status_emoji = "✅" if response.status_code in [200, 201] else "❌"
    print(f"\n{status_emoji} --- {action} ---")
    print(f"Status: {response.status_code}")
    try:
        # Try to parse JSON, otherwise print text
        print(f"Body: {json.dumps(response.json(), indent=2)}")
    except:
        print(f"Body: {response.text}")
    return response

def run_tests():
    session = requests.Session()
    
    # ==========================================
    # 1. AUTHENTICATION (Login as Company Admin)
    # ==========================================
    print_header("TESTING AUTHENTICATION")
    
    login_payload = {
        "email": "adminaparna@gmail.com",
        "password": "admin123"
    }
    resp = session.post(f"{BASE_URL}/auth/login", json=login_payload)
    print_response(resp, "Login as Admin")
    
    if resp.status_code != 200:
        print("❌ Login failed. Aborting tests. (Is the server running?)")
        return

    token = resp.json().get("token")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get Profile
    resp = session.get(f"{BASE_URL}/auth/profile", headers=headers)
    print_response(resp, "Get Profile")

    # ==========================================
    # 2. ADMIN OPERATIONS
    # ==========================================
    print_header("TESTING ADMIN ENDPOINTS")

    # Get All Employees
    resp = session.get(f"{BASE_URL}/admin/employees", headers=headers)
    print_response(resp, "Get All Employees")

    # Create New Employee (using random email to avoid conflicts)
    random_str = uuid.uuid4().hex[:6]
    new_emp = {
        "first_name": "Test",
        "last_name": f"User {random_str}",
        "email": f"test_{random_str}@aparna.com",
        "password": "password123",
        "role": "EMPLOYEE",
        "gender": "Male",
        "date_of_birth": "1995-05-10",
        "job": {
            "department": "IT",
            "designation": "Junior Dev",
            "salary": 50000,
            "join_date": "2024-01-01",
            "job_title": "Software Engineer"
        },
        "bank": {
            "bank_name": "HDFC Bank",
            "account_number": "12345678901",
            "ifsc_code": "HDFC0001234",
            "branch_name": "Hyderabad"
        },
        "address": {
            "address_line1": "Tech Park, Street 1",
            "city": "Hyderabad",
            "state": "Telangana",
            "zip_code": "500081",
            "country": "India",
            "address_type": "CURRENT"
        }
    }
    resp = session.post(f"{BASE_URL}/admin/employee", json=new_emp, headers=headers)
    print_response(resp, "Create Employee")
    
    emp_id = None
    if resp.status_code in [200, 201]:
        data = resp.json()
        # Try to get ID from response, or fallback to fetching list
        emp_id = data.get("employee_id")
        
        if not emp_id:
            # Fallback: fetch list and find the user we just created
            list_resp = session.get(f"{BASE_URL}/admin/employees", headers=headers)
            if list_resp.status_code == 200:
                employees = list_resp.json().get("employees", [])
                for emp in employees:
                    if emp.get('email') == new_emp['email']:
                        emp_id = emp.get('id')
                        break

    if emp_id:
        print(f"\nℹ️  Targeting Employee ID: {emp_id}")
        
        # Update Employee
        update_data = {"department": "Engineering", "status": "ACTIVE"}
        resp = session.put(f"{BASE_URL}/admin/employee/{emp_id}", json=update_data, headers=headers)
        print_response(resp, f"Update Employee {emp_id}")
        
        # Get Specific Employee
        resp = session.get(f"{BASE_URL}/admin/employee/{emp_id}", headers=headers)
        print_response(resp, f"Get Employee {emp_id}")
        
        # Delete Employee
        resp = session.delete(f"{BASE_URL}/admin/employee/{emp_id}", headers=headers)
        print_response(resp, f"Delete Employee {emp_id}")
    else:
        print("\n⚠️ Could not retrieve Employee ID to test Update/Delete")

    # ==========================================
    # 3. SUPER ADMIN OPERATIONS
    # ==========================================
    print_header("TESTING SUPER ADMIN ENDPOINTS")
    
    sa_login = {
        "email": "superadmin@hrms.com",
        "password": "superadmin123"
    }
    resp = session.post(f"{BASE_URL}/auth/login", json=sa_login)
    print_response(resp, "Login as Super Admin")
    
    if resp.status_code == 200:
        sa_token = resp.json().get("token")
        sa_headers = {"Authorization": f"Bearer {sa_token}"}
        
        # Get Companies
        resp = session.get(f"{BASE_URL}/superadmin/companies", headers=sa_headers)
        print_response(resp, "Get Companies")

    # ==========================================
    # 4. EMPLOYEE OPERATIONS
    # ==========================================
    print_header("TESTING EMPLOYEE ENDPOINTS")
    
    # Login as Employee (created in seed_data.py)
    emp_login = {
        "email": "employee@aparna.com",
        "password": "emp123"
    }
    resp = session.post(f"{BASE_URL}/auth/login", json=emp_login)
    print_response(resp, "Login as Employee")
    
    if resp.status_code == 200:
        emp_token = resp.json().get("token")
        emp_headers = {"Authorization": f"Bearer {emp_token}"}
        
        # Get Profile
        resp = session.get(f"{BASE_URL}/employee/profile", headers=emp_headers)
        print_response(resp, "Get Employee Profile")
        
        # Mark Attendance (Clock In)
        resp = session.post(f"{BASE_URL}/employee/attendance", headers=emp_headers)
        print_response(resp, "Clock In / Out")

if __name__ == "__main__":
    try:
        run_tests()
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to server. Please ensure 'python app.py' is running in another terminal.")