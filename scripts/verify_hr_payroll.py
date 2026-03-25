import requests
import json

BASE_URL = "http://localhost:5000/api"

def login(email, password):
    resp = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
    if resp.status_code == 200:
        return resp.json().get("token")
    return None

def test_hr_access(token):
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Test Listing Payslips
    print("Testing HR List Payslips...")
    resp = requests.get(f"{BASE_URL}/admin/payslips", headers=headers)
    if resp.status_code == 200:
        data = resp.json().get("data", [])
        print(f"Found {len(data)} payslips.")
        # Check if any Admin/SuperAdmin payslips are returned
        # This requires knowing the roles of the owners, which we'll check via detail API if possible
    else:
        print(f"Failed to list payslips: {resp.status_code}")

    # 2. Test Salary Register
    print("\nTesting HR Salary Register...")
    resp = requests.get(f"{BASE_URL}/payroll/reports/salary-register", headers=headers)
    if resp.status_code == 200:
        print("Salary register fetched successfully.")
    else:
        print(f"Failed to fetch salary register: {resp.status_code}")

    # 4. Test New Reports
    reports = ["income-tax", "professional-tax", "general-ledger", "accounts-payable"]
    for report in reports:
        print(f"\nTesting HR {report.replace('-', ' ').title()} Report...")
        resp = requests.get(f"{BASE_URL}/payroll/reports/{report}", headers=headers)
        if resp.status_code == 200:
            print(f"{report.replace('-', ' ').title()} report fetched successfully.")
        else:
            print(f"Failed to fetch {report}: {resp.status_code}")

if __name__ == "__main__":
    # Note: This script assumes a local server is running and an HR user exists.
    # Replace with valid credentials for automated verification if needed.
    # hr_token = login("hr@example.com", "password")
    # if hr_token:
    #     test_hr_access(hr_token)
    print("Verification script ready. Please run manually or provide credentials.")
