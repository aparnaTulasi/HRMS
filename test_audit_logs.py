
import requests

BASE_URL = "http://192.168.1.6:5000/api"
SA_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJyb2xlIjoiU1VQRVJfQURNSU4iLCJjb21wYW55X2lkIjpudWxsLCJleHAiOjE3NzMyMDk1Mzl9.oUwenpQMpiEZjblb_4f4yN4Olnl9d4918X1TjY-fVU4"

def test_fetch_logs():
    headers = {"Authorization": f"Bearer {SA_TOKEN}"}
    
    # 1. Fetch Logs
    resp = requests.get(f"{BASE_URL}/audit/logs", headers=headers)
    print(f"Fetch Logs Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Total Logs: {data.get('total')}")
        for log in data.get('data', []):
            print(f"- {log.get('action')} by User {log.get('user_id')} on {log.get('entity')} at {log.get('created_at')}")
    else:
        print(f"Error: {resp.text}")

if __name__ == "__main__":
    test_fetch_logs()
