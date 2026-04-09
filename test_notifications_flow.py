import traceback
from app import app, db
from models.user import User
from models.notification import Notification

def test_notification_flow():
    with app.app_context():
        try:
            print("Starting Notification Flow Test...")
            
            # 1. Pick a test user
            manager = User.query.filter_by(role='MANAGER').first()
            if not manager:
                print("No Manager found for testing.")
                return

            print(f"Testing for User: {manager.email} (ID: {manager.id})")

            # 2. Trigger a mock notification
            from utils.notification_utils import create_notification
            test_msg = "RETRIEVAL TEST: This is a test notification."
            
            # Use the actual helper
            success = create_notification(user_id=manager.id, message=test_msg)
            if not success:
                print("❌ create_notification helper returned False")
                return

            db.session.commit()
            print(f"✅ Notification created and committed.")

            # 3. Simulate API call
            from routes.notification_routes import get_user_notifications
            from flask import g
            
            with app.test_request_context():
                g.user = manager
                response, status_code = get_user_notifications()
                data = response.get_json()
                
                if status_code == 200 and data.get('success'):
                    found = any(n['message'] == test_msg for n in data['data'])
                    if found:
                        print("✅ FINAL VERIFICATION SUCCESSFUL: Notification visible in API.")
                        print(f"API Data: {data['data'][0]}") # Show one example
                    else:
                        print("❌ Verification Failed: Target notification not in list.")
                        print(f"List contained {len(data['data'])} unread items.")
                else:
                    print(f"❌ API call failed with status {status_code}: {data}")

        except Exception as e:
            print(f"❌ Exception occurred: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    test_notification_flow()
