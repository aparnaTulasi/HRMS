import requests
import json

url = "http://localhost:5000/login"
payload = {
    "email": "aparnatulasi7@gmail.com",
    "password": "Password123" # I need to find the password
}

try:
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")
