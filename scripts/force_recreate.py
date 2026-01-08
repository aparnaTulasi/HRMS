import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
import os

print("🔄 FORCING DATABASE RECREATION")
print("="*50)

# Delete database file
db_path = 'instance/hrms.db'
if os.path.exists(db_path):
    os.remove(db_path)
    print(f"✅ Deleted: {db_path}")

# Delete backup if exists
backup_path = f'{db_path}.backup'
if os.path.exists(backup_path):
    os.remove(backup_path)
    print(f"✅ Deleted backup: {backup_path}")

# Create app context and recreate tables
with app.app_context():
    # Drop all tables
    db.drop_all()
    print("✅ Dropped all tables")
    
    # Create all tables
    db.create_all()
    print("✅ Created all tables with new schema")
    
    print("\n📋 Tables created:")
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    for table_name in inspector.get_table_names():
        print(f"  - {table_name}")

print("\n🎉 Database recreated successfully!")
print("👉 Now restart Flask app: python app.py")