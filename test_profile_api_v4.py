import requests
import json

BASE_URL = "http://127.0.0.1:5000/api/me/profile"

TOKENS = {
    "SUPER_ADMIN": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoyLCJyb2xlIjoiU1VQRVJfQURNSU4iLCJjb21wYW55X2lkIjpudWxsLCJleHAiOjE3NzQ1ODczNjR9.nu3dtWkPs4Iu9i1ACsaO0kFwKka6IHpZzV7iIUXAd3k",
    "ADMIN": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjo2LCJyb2xlIjoiQURNSU4iLCJjb21wYW55X2lkIjozLCJleHAiOjE3NzQ1ODczOTh9.Jos-3cg7JCsX27zY4-WEa1yiID4VcM9lJ2rUk_AF1V8",
    "HR": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjo3LCJyb2xlIjoiSFIiLCJjb21wYW55X2lkIjozLCJleHAiOjE3NzQ1ODc1Mzl9.ZK_JMhi2U1NxEQEZFWC_n_af3bfLpSwdlxhRF0jIdro"
}

def test_profile(role, token):
    print(f"\n--- Testing {role} Profile (Refined) ---")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    try:
        res = requests.get(BASE_URL, headers=headers)
        print(f"Status: {res.status_code}")
        if res.status_code == 200:
            data = res.json()["data"]
            print(f"Name: {data['name']}")
            print(f"Employee ID: {data['employee_id']}")
            print(f"Joined: {data['joined']}")
            print(f"Overview Keys: {list(data['overview'].keys())}")
            print(f"Contact Info: {data['overview']['contact_information']['email_address']}")
            print(f"Work Snapshot Role: {data['overview']['work_snapshot']['role_designation']}")
        else:
            print(f"Error: {res.text}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    for role, token in TOKENS.items():
        test_profile(role, token)
