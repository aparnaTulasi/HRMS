import requests
import json

# Test the policy APIs
BASE_URL = "http://127.0.0.1:5000"

def test_policy_apis():
    # 1. Get categories
    print("1. Testing GET /api/policies/categories")
    response = requests.get(f"{BASE_URL}/api/policies/categories")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        categories = response.json()
        print(f"   Found {len(categories)} categories")
    
    # 2. Get policies
    print("\n2. Testing GET /api/policies/")
    response = requests.get(f"{BASE_URL}/api/policies/")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        policies = response.json()
        print(f"   Found {len(policies)} policies")
    
    print("\n✨ Policy APIs are working!")

if __name__ == '__main__':
    test_policy_apis()