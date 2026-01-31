import os
from app import app, db

def rebuild_database():
    """
    Drops all tables and recreates them based on the current models.
    WARNING: This will delete all data in the database.
    """
    with app.app_context():
        print("--- Dropping all database tables... ---")
        db.drop_all()
        print("--- Creating all database tables... ---")
        db.create_all()
        print("✅ Database has been rebuilt successfully!")

if __name__ == "__main__":
    db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    db_path = db_uri.replace("sqlite:///", "") if db_uri.startswith("sqlite:///") else ""

    if os.path.exists(db_path):
        confirm = input(f"⚠️  WARNING: This will delete all data in '{db_path}'.\nAre you sure you want to continue? (y/n): ")
        if confirm.lower() == 'y':
            rebuild_database()
        else:
            print("Operation cancelled.")
    else:
        print(f"Database file '{db_path}' not found. Creating a new one.")
        rebuild_database()