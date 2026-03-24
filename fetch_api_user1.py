import requests
import json

url = "http://localhost:5000/api/superadmin/companies"
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJyb2xlIjoiU1VQRVJfQURNSU4iLCJjb21wYW55X2lkIjpudWxsLCJleHAiOjE3NzMyMDk1Mzl9.oUwenpQMpiEZjblb_4f4yN4Olnl9d4918X1TjY-fVU4"
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
