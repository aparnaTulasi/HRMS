from app import app, db
from sqlalchemy import text

def add_column():
    with app.app_context():
        try:
            db.session.execute(text("ALTER TABLE users ADD COLUMN must_change_password BOOLEAN DEFAULT FALSE"))
            db.session.commit()
            print("Successfully added must_change_password column to users table.")
        except Exception as e:
            print(f"Error adding column (it might already exist): {e}")

if __name__ == "__main__":
    add_column()
