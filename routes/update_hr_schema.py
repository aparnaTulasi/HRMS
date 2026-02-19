import sys
import os

# Add parent directory to path to import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask
from models import db
from sqlalchemy import text

# Try to import create_app, else setup minimal app
try:
    from app import create_app
    app = create_app()
except ImportError:
    print("Could not import create_app from app. Using minimal setup.")
    app = Flask(__name__)
    # Update this URI to match your actual DB config if create_app fails
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hrms.db' 
    db.init_app(app)

def run_update():
    with app.app_context():
        with db.engine.connect() as conn:
            # 1. LetterRequest Columns
            cols_lr = [
                ("employee_name", "VARCHAR(255)"),
                ("employee_email", "VARCHAR(255)"),
                ("letter_date", "DATE"),
                ("template_option", "VARCHAR(50)"),
                ("send_email_copy", "BOOLEAN DEFAULT 0"),
                ("status", "VARCHAR(50)"),
                ("pdf_path", "VARCHAR(255)")
            ]
            print("Updating LetterRequest table...")
            for col, dtype in cols_lr:
                try:
                    conn.execute(text(f"ALTER TABLE letter_requests ADD COLUMN {col} {dtype}"))
                    print(f"  ✅ Added {col}")
                except Exception as e:
                    print(f"  ℹ️  {col} might already exist.")

            # 2. CertificateIssue Columns
            cols_ci = [
                ("issue_date", "DATE"),
                ("recipient_email", "VARCHAR(255)"),
                ("template_option", "VARCHAR(50)"),
                ("send_email_copy", "BOOLEAN DEFAULT 0")
            ]
            print("Updating CertificateIssue table...")
            for col, dtype in cols_ci:
                try:
                    conn.execute(text(f"ALTER TABLE certificate_issues ADD COLUMN {col} {dtype}"))
                    print(f"  ✅ Added {col}")
                except Exception as e:
                    print(f"  ℹ️  {col} might already exist.")
            
            conn.commit()
            print("Schema update complete.")

if __name__ == "__main__":
    run_update()