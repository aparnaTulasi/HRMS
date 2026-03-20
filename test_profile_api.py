import requests
import json

BASE_URL = "http://127.0.0.1:5000/api/me/profile"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJyb2xlIjoiU1VQRVJfQURNSU4iLCJjb21wYW55X2lkIjpudWxsLCJleHAiOjE3NzI5NTY5OTN9.G17h-OQCK3t36rYMNe_Kep-NLylYnJszFQjr4eD_k8M"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def test_get():
    print("Testing GET Profile...")
    res = requests.get(BASE_URL, headers=headers)
    print(f"Status: {res.status_code}")
    print(f"Response: {json.dumps(res.json(), indent=2)}")

def test_patch():
    print("\nTesting PATCH Profile...")
    payload = {
        "bio": "I am the Super Admin of this platform.",
        "phone": "9999999999",
        "emergency_contact": "Emergency - 000"
    }
    res = requests.patch(BASE_URL, headers=headers, json=payload)
    print(f"Status: {res.status_code}")
    print(f"Response: {res.json()}")

if __name__ == "__main__":
    test_get()
    test_patch()
    test_get()
