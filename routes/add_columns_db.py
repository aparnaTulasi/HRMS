import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine, text
from config import Config

def add_columns():
    print(f"Connecting to database: {Config.SQLALCHEMY_DATABASE_URI}")
    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    
    # SQL commands to add columns
    # Note: Adjust table names if they differ (e.g. letter_request vs letter_requests)
    commands = [
        # LetterRequest
        "ALTER TABLE letter_requests ADD COLUMN employee_name VARCHAR(255)",
        "ALTER TABLE letter_requests ADD COLUMN employee_email VARCHAR(255)",
        "ALTER TABLE letter_requests ADD COLUMN letter_date DATE",
        "ALTER TABLE letter_requests ADD COLUMN template_option VARCHAR(255)",
        "ALTER TABLE letter_requests ADD COLUMN send_email_copy BOOLEAN DEFAULT 0",
        
        # CertificateIssue
        "ALTER TABLE certificate_issues ADD COLUMN recipient_email VARCHAR(255)",
        "ALTER TABLE certificate_issues ADD COLUMN template_option VARCHAR(255)",
        "ALTER TABLE certificate_issues ADD COLUMN send_email_copy BOOLEAN DEFAULT 0"
    ]

    with engine.connect() as conn:
        for cmd in commands:
            try:
                conn.execute(text(cmd))
                print(f"✅ Executed: {cmd}")
            except Exception as e:
                print(f"⚠️  Failed/Skipped: {cmd}\n    Reason: {e}")
        conn.commit()

if __name__ == "__main__":
    add_columns()