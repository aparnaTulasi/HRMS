from app import app
from models.user import User
from models import db
from flask import g
from routes.company import list_companies
import json

def test_list_companies():
    with app.app_context():
        # Find a super admin user to use for the request
        user = User.query.filter_by(role='SUPER_ADMIN').first()
        if not user:
            print("No SUPER_ADMIN user found")
            return

        with app.test_client() as client:
            # We need a token. Let's assume the decorator might bypass or we can mock g.user
            # Actually, @token_required usually expects a real token in headers.
            # But we can try to see if we can get a token or just mock the identity.
            
            with app.test_request_context(headers={"Authorization": "Bearer fake_token"}):
                g.user = user # The actual SA user from DB
                
                try:
                    response = list_companies()
                    print("Response Status Code:", response[1] if isinstance(response, tuple) else 200)
                    data = response[0].get_json() if hasattr(response[0], 'get_json') else response.get_json()
                    print("Response Data:", json.dumps(data, indent=2))
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    print("Error calling list_companies:", e)

if __name__ == "__main__":
    test_list_companies()
