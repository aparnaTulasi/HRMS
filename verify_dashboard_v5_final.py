from app import app, db
from models.user import User
from models.employee import Employee
from models.job_posting import JobPosting
from flask import g
import json
from unittest.mock import patch

# Mock decorator
def mock_token_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated

def get_res_json(res):
    if isinstance(res, tuple):
        return res[0].get_json()
    return res.get_json()

with patch('utils.decorators.token_required', mock_token_required), \
     patch('utils.decorators.role_required', lambda x: lambda f: f):
    
    from routes.dashboard_routes import get_dashboard_stats

    def verify_v5():
        with app.app_context():
            print("\n=== FINAL VERIFICATION FOR E2E SCENARIO (V5) ===\n")
            
            # HR Context (Company 1)
            hr = User.query.filter_by(role='HR', company_id=1).first()
            if hr:
                g.user = hr
                with app.test_request_context():
                    res = get_dashboard_stats()
                    data = get_res_json(res).get('data', {})
                    
                    print("HR DASHBOARD (COMPANY HEALTH):")
                    print(json.dumps(data.get('company_health', {}), indent=2))
                    
                    print("\nPENDING ONBOARDING LIST:")
                    # Check for "Fresh Graduate" hire
                    onboarding = data.get('onboarding_pending', [])
                    print(f"Count: {len(onboarding)}")
                    for emp in onboarding:
                        print(f"- {emp.get('name')} (Status: {emp.get('onboarding_status')})")

            # Check Recruitment
            job = JobPosting.query.filter_by(job_title="Software Architect", company_id=1).first()
            print(f"\nRecruitment Job 'Software Architect' Active: {True if job else False}")

    if __name__ == "__main__":
        verify_v5()
