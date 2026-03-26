import requests
import json

BASE_URL = "http://127.0.0.1:5000/api/loans"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoyLCJyb2xlIjoiU1VQRVJfQURNSU4iLCJjb21wYW55X2lkIjpudWxsLCJleHAiOjE3NzQ1ODczNjR9.nu3dtWkPs4Iu9i1ACsaO0kFwKka6IHpZzV7iIUXAd3k"

def test_loan_dashboard():
    print("\n--- Testing Loan Dashboard API ---")
    headers = {"Authorization": f"Bearer {TOKEN}"}
    res = requests.get(f"{BASE_URL}/dashboard", headers=headers)
    print(f"Status: {res.status_code}")
    if res.status_code == 200:
        data = res.json()["data"]
        stats = data["stats"]
        print(f"Total Disbursed: ₹{stats['total_disbursed']/100000:.1f}L")
        print(f"Active Loans: {stats['active_loans']}")
        print(f"Avg. Interest Rate: {stats['avg_interest_rate']}%")
        print(f"Trend Data Count: {len(data['charts']['disbursement_trend'])}")
    else:
        print(f"Error: {res.text}")

def test_loan_requests():
    print("\n--- Testing Loan Requests API ---")
    headers = {"Authorization": f"Bearer {TOKEN}"}
    res = requests.get(f"{BASE_URL}/requests", headers=headers)
    print(f"Status: {res.status_code}")
    if res.status_code == 200:
        data = res.json()["data"]
        print(f"Requests Count: {len(data)}")
        # The first 4 should match our UI seed
        for req in data[:4]:
            print(f"Emp: {req['employee_name']}, Amt: ₹{req['amount']}, Type: {req['type']}, Status: {req['status']}, EMI: {req['emi']}")
    else:
        print(f"Error: {res.text}")

if __name__ == "__main__":
    test_loan_dashboard()
    test_loan_requests()
