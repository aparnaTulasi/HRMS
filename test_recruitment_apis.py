import requests
import json

BASE_URL = "http://127.0.0.1:5000"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoyLCJyb2xlIjoiU1VQRVJfQURNSU4iLCJjb21wYW55X2lkIjpudWxsLCJleHAiOjE3NzQ1ODczNjR9.nu3dtWkPs4Iu9i1ACsaO0kFwKka6IHpZzV7iIUXAd3k"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def test_recruit_stats():
    print("\n--- Testing Recruitment Stats ---")
    res = requests.get(f"{BASE_URL}/api/recruitment/stats", headers=headers)
    print(f"Status: {res.status_code}")
    if res.status_code == 200:
        print(json.dumps(res.json(), indent=2))

def test_job_listing():
    print("\n--- Testing Job Listing ---")
    res = requests.get(f"{BASE_URL}/api/recruitment/jobs", headers=headers)
    print(f"Status: {res.status_code}")
    if res.status_code == 200:
        jobs = res.json()['data']
        print(f"Found {len(jobs)} jobs")
        if jobs:
            job_id = jobs[0]['id']
            # Test getting applicants for this job
            res_app = requests.get(f"{BASE_URL}/api/recruitment/jobs/{job_id}/applicants", headers=headers)
            print(f"Applicants for Job {job_id} Status: {res_app.status_code}")
            if res_app.status_code == 200:
                print(f"Found {len(res_app.json()['data'])} applicants")

if __name__ == "__main__":
    test_recruit_stats()
    test_job_listing()
