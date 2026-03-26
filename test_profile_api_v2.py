import requests
import json

BASE_URL = "http://127.0.0.1:5000/api/me/profile"
# Token from previous test_profile_api.py (assuming it's still valid or I need to generate one)
# I'll just use the one I saw earlier.
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJyb2xlIjoiU1VQRVJfQURNSU4iLCJjb21wYW55X2lkIjpudWxsLCJleHAiOjE3NzI5NTY5OTN9.G17h-OQCK3t36rYMNe_Kep-NLylYnJszFQjr4eD_k8M"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def test_get():
    print("Testing GET Profile (Enhanced)...")
    try:
        res = requests.get(BASE_URL, headers=headers)
        print(f"Status: {res.status_code}")
        if res.status_code == 200:
            data = res.json()
            print("Response Structure Check:")
            profile = data.get("data", {})
            print(f"- Name: {profile.get('name')}")
            print(f"- Designation: {profile.get('designation')}")
            print(f"- Tabs present: {list(profile.get('tabs', {}).keys())}")
            print(f"- Overview Contact Email: {profile.get('tabs', {}).get('overview', {}).get('contact_info', {}).get('email')}")
        else:
            print(f"Error: {res.text}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_get()
