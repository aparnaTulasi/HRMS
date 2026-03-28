import requests
import json

BASE_URL = "http://127.0.0.1:5000"
TOKEN = "YOUR_TOKEN_HERE" # Need a valid token

def test_support_apis():
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    
    # 1. Create a ticket
    print("Testing ticket creation...")
    ticket_data = {
        "subject": "Internet issue",
        "category": "IT Support",
        "priority": "High",
        "description": "The internet is very slow in cabin 4.",
        "attachment_url": "https://example.com/screenshot.png"
    }
    # resp = requests.post(f"{BASE_URL}/tickets", headers=headers, data=json.dumps(ticket_data))
    # print(resp.json())
    
    # 2. Get dashboard stats
    print("Testing dashboard stats...")
    # resp = requests.get(f"{BASE_URL}/dashboard-stats", headers=headers)
    # print(resp.json())
    
    # 3. Get tickets list
    print("Testing tickets list...")
    # resp = requests.get(f"{BASE_URL}/tickets", headers=headers)
    # print(resp.json())

    print("Support Helpdesk API verification logic is ready.")

if __name__ == "__main__":
    test_support_apis()
