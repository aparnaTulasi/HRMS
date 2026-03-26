import requests
import json

BASE_URL = "http://127.0.0.1:5000"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoyLCJyb2xlIjoiU1VQRVJfQURNSU4iLCJjb21wYW55X2lkIjpudWxsLCJleHAiOjE3NzQ1ODczNjR9.nu3dtWkPs4Iu9i1ACsaO0kFwKka6IHpZzV7iIUXAd3k"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def test_team_dashboard():
    print("\n--- Testing Team Dashboard Stats ---")
    res = requests.get(f"{BASE_URL}/api/superadmin/team/dashboard", headers=headers)
    print(f"Status: {res.status_code}")
    if res.status_code == 200:
        print(json.dumps(res.json(), indent=2))

def test_team_superstars():
    print("\n--- Testing Team Superstars ---")
    res = requests.get(f"{BASE_URL}/api/superadmin/team/superstars", headers=headers)
    print(f"Status: {res.status_code}")
    if res.status_code == 200:
        print(f"Count: {len(res.json()['data'])}")

def test_squad_management():
    print("\n--- Testing Squad Management ---")
    # 1. Create a squad
    payload = {
        "squad_name": "Core Platform",
        "project_name": "HRMS Cloud",
        "squad_type": "IT",
        "members": []
    }
    res = requests.post(f"{BASE_URL}/api/superadmin/squads", headers=headers, json=payload)
    print(f"POST Squad Status: {res.status_code}")

    # 2. Get squads
    res = requests.get(f"{BASE_URL}/api/superadmin/squads", headers=headers)
    print(f"GET Squads Status: {res.status_code}")
    if res.status_code == 200:
        print(f"Total Squads: {res.json()['data']['stats']['total_squads']}")

if __name__ == "__main__":
    test_team_dashboard()
    test_team_superstars()
    test_squad_management()
