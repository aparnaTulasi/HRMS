import os
from flask import Flask
from models import db
from config import Config

# --- DANGER ZONE ---
# This script will permanently delete all data in your database.
# Do not run this in a production environment.

def main():
    """
    Initializes a temporary Flask app to gain an application context,
    then drops all database tables and recreates them.
    """
    # Create a temporary Flask app instance
    app = Flask(__name__)
    # Load configuration from your config.py file
    app.config.from_object(Config)

    # Associate the SQLAlchemy object with the app
    db.init_app(app)

    with app.app_context():
        print("--- WARNING: This script will delete all data in your database. ---")
        confirm = input("Are you sure you want to proceed? Type 'yes' to continue: ")

        if confirm.lower() != 'yes':
            print("Operation cancelled.")
            return

        print("\n[1/3] Dropping all database tables...")
        try:
            # Import all your models here so SQLAlchemy knows about them
            # when calling db.create_all(). This is a crucial step.
            from models.user import User
            from models.company import Company
            from models.employee import Employee
            from models.department import Department
            # Add any other models you have created here

            db.drop_all()
            print("[2/3] All tables dropped successfully.")

            db.create_all()
            print("[3/3] All tables recreated successfully based on current models.")
            print("\n✅ Database has been reset to a clean state.")

        except Exception as e:
            print(f"\n❌ An error occurred: {e}")
            print("Operation failed. Your database might be in an inconsistent state.")

if __name__ == '__main__':
    main()
