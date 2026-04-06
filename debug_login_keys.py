import requests
import json

# Testing the root alias
url = "http://127.0.0.1:5000/login"
payload = {
    "email": "aparnatulasi7@gmail.com",
    "password": "password"
}
headers = {'Content-Type': 'application/json'}

try:
    response = requests.post(url, data=json.dumps(payload), headers=headers)
    print(f"Status: {response.status_code}")
    # Print keys to identify the exact case
    if response.headers.get('Content-Type') == 'application/json':
        data = response.json()
        print(f"Keys: {list(data.keys())}")
        if 'access_token' in data:
            print("FOUND: access_token")
        if 'token' in data:
            print("FOUND: token")
    else:
        print("Response is not JSON")
except Exception as e:
    print(f"Error: {e}")
