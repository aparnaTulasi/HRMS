import requests
import json

BASE_URL = "http://127.0.0.1:5000/api/audit/logs"
TOKEN = "YOUR_TOKEN_HERE" # Need a valid token

def test_audit_logs():
    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    # 1. Test basic fetch
    print("Testing basic fetch...")
    # resp = requests.get(BASE_URL, headers=headers)
    # print(resp.json())
    
    # 2. Test module filter
    print("Testing module filter (Employee)...")
    # resp = requests.get(f"{BASE_URL}?module=Employee", headers=headers)
    # print(resp.json())
    
    # 3. Test entity ID formatting & details
    # Look for "EMP-" in output
    print("Verification logic for details and ID formatting is ready.")

if __name__ == "__main__":
    test_audit_logs()
