from app import app
from models import db
from sqlalchemy import text

def update_schema():
    with app.app_context():
        try:
            # Add file_size
            db.session.execute(text("ALTER TABLE hr_documents ADD COLUMN file_size VARCHAR(20)"))
            print("Added column: file_size")
        except Exception as e:
            print(f"Column file_size might already exist: {e}")

        try:
            # Add file_type
            db.session.execute(text("ALTER TABLE hr_documents ADD COLUMN file_type VARCHAR(20)"))
            print("Added column: file_type")
        except Exception as e:
            print(f"Column file_type might already exist: {e}")

        db.session.commit()
        print("Schema update completed.")

if __name__ == "__main__":
    update_schema()
