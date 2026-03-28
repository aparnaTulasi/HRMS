from app import app, db
from sqlalchemy import text

def update_schema():
    with app.app_context():
        # Check if column exists
        try:
            db.session.execute(text("ALTER TABLE employees ADD COLUMN onboarding_status VARCHAR(50) DEFAULT 'Pending'"))
            print("Added onboarding_status column")
        except Exception as e:
            print(f"onboarding_status column might already exist: {e}")

        try:
            db.session.execute(text("ALTER TABLE employees ADD COLUMN onboarding_completed_at DATETIME"))
            print("Added onboarding_completed_at column")
        except Exception as e:
            print(f"onboarding_completed_at column might already exist: {e}")

        db.session.commit()
        print("Schema update complete")

if __name__ == "__main__":
    update_schema()
