from app import app, db
from models.user import User
from sqlalchemy import inspect

print("🔍 DEBUGGING DATABASE ISSUE")
print("="*50)

with app.app_context():
    # Check current database tables
    inspector = inspect(db.engine)
    print("\nTables in database:")
    for table_name in inspector.get_table_names():
        print(f"  - {table_name}")
    
    # Check users table columns
    print("\nUsers table columns (from database):")
    try:
        for column in inspector.get_columns('users'):
            print(f"  {column['name']} ({column['type']})")
    except Exception as e:
        print(f"  Could not inspect 'users' table: {e}")

    # Check what User model expects
    print("\nUser model columns (from code):")
    for column in User.__table__.columns:
        print(f"  {column.name} ({column.type})")
    
    # Try to create a user
    print("\n🤔 Trying to create a test user...")
    try:
        test_user = User(
            email="test@test.com",
            password="test",
            role="TEST",
            status="ACTIVE"
        )
        db.session.add(test_user)
        db.session.commit()
        print("✅ User creation SUCCESS!")
        db.session.delete(test_user) # Clean up
        db.session.commit()
    except Exception as e:
        print(f"❌ User creation FAILED: {e}")
        db.session.rollback()