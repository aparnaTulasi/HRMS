import sys
import os

# Add the project root directory to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db

if __name__ == "__main__":
    print("⚠️  WARNING: This will PERMANENTLY DELETE ALL DATA in the database!")
    confirm = input("Type 'yes' to confirm: ")
    
    if confirm.lower() == "yes":
        with app.app_context():
            print("Dropping all tables...")
            db.drop_all()
            print("Recreating all tables...")
            db.create_all()
            print("✅ Database has been reset successfully.")
    else:
        print("❌ Operation cancelled.")