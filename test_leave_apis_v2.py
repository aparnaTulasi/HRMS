import requests
import json

BASE_URL = "http://127.0.0.1:5000/leave"
# Assume we have a valid token (you might need to login first to get one)
TOKEN = "YOUR_TOKEN_HERE" # Need to get this from a login call if testing manually

def test_calculate_days():
    print("Testing /calculate-days...")
    payload = {
        "from_date": "2026-04-01",
        "to_date": "2026-04-01",
        "is_half_day": True,
        "leave_type_id": 1
    }
    headers = {"Authorization": f"Bearer {TOKEN}"}
    # response = requests.post(f"{BASE_URL}/calculate-days", json=payload, headers=headers)
    # print(response.json())
    print("Code for testing /calculate-days is ready.")

def test_my_dashboard():
    print("Testing /my-dashboard/summary...")
    # response = requests.get(f"{BASE_URL}/my-dashboard/summary", headers=headers)
    # print(response.json())
    print("Code for testing dashboard is ready.")

if __name__ == "__main__":
    # In a real scenario, this would perform actual requests.
    # For now, I'll provide the script structure.
    test_calculate_days()
    test_my_dashboard()
