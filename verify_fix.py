import requests
import json

BASE_URL = "http://127.0.0.1:5000/api/me/profile"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoyLCJyb2xlIjoiU1VQRVJfQURNSU4iLCJjb21wYW55X2lkIjpudWxsLCJleHAiOjE3NzQ1ODczNjR9.nu3dtWkPs4Iu9i1ACsaO0kFwKka6IHpZzV7iIUXAd3k"

def verify():
    headers = {
        "Authorization": f"Bearer {TOKEN}"
    }

    # Data to update
    payload = {
        "name": "Aparna SEELAM Updated",
        "phone": "1234567890",
        "address": "New Address St, City",
        "employee_id": "MOD-1234",
        "designation": "Chief Admin",
        "department": "IT Support",
        "bio": "Fixed and working bio."
    }

    print("\n--- Verifying Profile PATCH ---")
    try:
        res = requests.patch(BASE_URL, headers=headers, json=payload)
        print(f"PATCH Status: {res.status_code}")
        print(f"PATCH Response: {res.text}")

        if res.status_code == 200:
            print("\n--- Verifying with GET ---")
            res_get = requests.get(BASE_URL, headers=headers)
            if res_get.status_code == 200:
                data = res_get.json()["data"]
                print(f"Updated Name: {data.get('name')}")
                print(f"Updated Employee ID: {data.get('employee_id')}")
                # print(f"Updated Address: {data['overview']['contact_information']['address_location']}")
                # print(f"Updated bio: {data['overview']['about_bio']}")
            else:
                print(f"GET failed: {res_get.text}")
        else:
            print("PATCH request failed.")

    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    verify()
