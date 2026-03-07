import urllib.request
import json

url = "http://127.0.0.1:5000/api/auth/super-admin/signup"
data = {
    "first_name": "Aparna Tulasi",
    "last_name": "Seelam",
    "email": "seelamaparnatulasi@gmail.com",
    "password": "appu@134",
    "confirm_password": "appu@134",
    "role": "superadmin"
}

req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})

try:
    with urllib.request.urlopen(req) as response:
        print(f"Status Code: {response.getcode()}")
        print(f"Response Body: {response.read().decode()}")
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code}")
    print(f"Error Body: {e.read().decode()}")
except Exception as e:
    print(f"Error: {e}")
