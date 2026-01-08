from app import app
from models import db

if __name__ == "__main__":
    with app.app_context():
        print("Dropping all tables...")
        db.drop_all()
        print("Creating all tables...")
        db.create_all()
        print("Database schema updated successfully!")