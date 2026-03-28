from app import app
from models import db

def create_tables():
    with app.app_context():
        try:
            # Create all tables (this will skip existing ones and create new ones)
            db.create_all()
            print("Successfully created/updated approval tables.")
        except Exception as e:
            print(f"Error creating tables: {e}")

if __name__ == "__main__":
    create_tables()
