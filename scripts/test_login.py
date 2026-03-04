import requests
import json

# Test login endpoint
url = "http://127.0.0.1:5000/api/auth/login"
payload = {
    "email": "admin@hrms.com",
    "password": "admin123"
}

headers = {
    "Content-Type": "application/json"
}

try:
    response = requests.post(url, json=payload, headers=headers)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {response.headers}")
    
    if response.status_code == 200:
        data = response.json()
        print("\n✅ Login Successful!")
        print(f"Token: {data.get('token', 'No token')[:50]}...")
        print(f"Role: {data.get('role', 'No role')}")
        print(f"URL: {data.get('url', 'No URL')}")
        print(f"User Data: {json.dumps(data.get('user', {}), indent=2)}")
    else:
        print(f"\n❌ Login Failed: {response.text}")
        
except Exception as e:
    print(f"\n❌ Error: {e}")