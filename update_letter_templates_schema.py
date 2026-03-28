from app import app
from models import db
from sqlalchemy import text

def update_schema():
    with app.app_context():
        try:
            # Add category
            db.session.execute(text("ALTER TABLE letter_templates ADD COLUMN category VARCHAR(50)"))
            print("Added column: category")
        except Exception as e:
            print(f"Column category might already exist: {e}")

        try:
            # Add resource_url
            db.session.execute(text("ALTER TABLE letter_templates ADD COLUMN resource_url VARCHAR(255)"))
            print("Added column: resource_url")
        except Exception as e:
            print(f"Column resource_url might already exist: {e}")

        try:
            # Add blog_link
            db.session.execute(text("ALTER TABLE letter_templates ADD COLUMN blog_link VARCHAR(255)"))
            print("Added column: blog_link")
        except Exception as e:
            print(f"Column blog_link might already exist: {e}")

        try:
            # Add status
            db.session.execute(text("ALTER TABLE letter_templates ADD COLUMN status VARCHAR(20) DEFAULT 'Active'"))
            print("Added column: status")
        except Exception as e:
            print(f"Column status might already exist: {e}")

        try:
            # Add usage_count
            db.session.execute(text("ALTER TABLE letter_templates ADD COLUMN usage_count INTEGER DEFAULT 0"))
            print("Added column: usage_count")
        except Exception as e:
            print(f"Column usage_count might already exist: {e}")

        db.session.commit()
        print("Schema update completed.")

if __name__ == "__main__":
    update_schema()
