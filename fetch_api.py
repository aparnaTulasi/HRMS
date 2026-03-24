import requests
import json

url = "http://localhost:5000/api/superadmin/companies"
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoyLCJyb2xlIjoiU1VQRVJfQURNSU4iLCJjb21wYW55X2lkIjpudWxsLCJleHAiOjE3NzQ0MjI2OTF9.M_u5L0lGqNRh3dvcBXWcv5wQD68AGQVY4UP7JJULs4k"
headers = {"Authorization": f"Bearer {token}"}

try:
    response = requests.get(url, headers=headers)
    res_json = response.json()
    companies = res_json.get("data", [])
    print(f"Status: {response.status_code}")
    print(f"Total Companies Returned: {len(companies)}")
    for c in companies:
        print(f" - ID: {c.get('id')}, Name: {c.get('company_name')}")
except Exception as e:
    print(f"Error: {e}")
