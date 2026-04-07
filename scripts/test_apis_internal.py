from app import app
import json

def test_apis():
    with app.test_client() as client:
        # We need a token normally, but for a quick internal test, 
        # let's see if we can mock g.user or just check if the route exists and the logic doesn't crash on syntax.
        # Actually, let's just do a GET manually in a script that mimics the request context.
        
        from flask import g
        from models.user import User
        
        with app.app_context():
            user = User.query.filter_by(role='HR').first() or User.query.first()
            if not user:
                print("❌ No user found to test with.")
                return
            
            print(f"🧪 Testing with User: {user.email} (Role: {user.role})")
            
            with client.session_transaction() as sess:
                pass # session not used with JWT usually
            
            # Mock g.user for the duration of the test
            from utils.role_utils import normalize_role
            
            # Helper to mock g.user
            def mock_g():
                g.user = user
            
            # Test Staff List
            print("\n📡 Testing GET /api/visitor/staff-list...")
            with app.test_request_context():
                mock_g()
                from routes.visitor_routes import get_staff_list
                res, code = get_staff_list()
                print(f"Status: {code}")
                # print(f"Data: {res.get_json()}")
                if code == 200: print("✅ Success")
                else: print("❌ Failed")

            # Test Visitor Stats
            print("\n📡 Testing GET /api/visitor/stats...")
            with app.test_request_context():
                mock_g()
                from routes.visitor_routes import get_visitor_stats
                res, code = get_visitor_stats()
                print(f"Status: {code}")
                if code == 200: 
                    print("✅ Success")
                    print(f"Data: {res.get_json()['data']}")
                else: print("❌ Failed")

            # Test Desk Stats
            print("\n📡 Testing GET /api/desk/stats...")
            with app.test_request_context():
                mock_g()
                from routes.desk_routes import get_desk_stats
                res, code = get_desk_stats()
                print(f"Status: {code}")
                if code == 200: 
                    print("✅ Success")
                    print(f"Data: {res.get_json()['data']}")
                else: print("❌ Failed")

if __name__ == "__main__":
    test_apis()
