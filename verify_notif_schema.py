from app import app, db
from models.notification import Notification
from sqlalchemy import inspect

def verify_table():
    with app.app_context():
        print("Verifying 'notifications' table schema...")
        db.create_all()
        
        inspector = inspect(db.engine)
        columns = [c['name'] for c in inspector.get_columns('notifications')]
        print(f"Columns in 'notifications' table: {columns}")
        
        required = ['id', 'user_id', 'role', 'message', 'is_read', 'created_at']
        for col in required:
            if col not in columns:
                print(f"❌ Missing column: {col}")
            else:
                print(f"✅ Column exists: {col}")

if __name__ == "__main__":
    verify_table()
