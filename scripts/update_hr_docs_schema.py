import sqlite3
import os

def update_hr_docs_schema():
    # Path to database
    db_path = os.path.join('instance', 'hrms.db')
    
    # Adjust path if running from scripts directory
    if not os.path.exists(db_path):
        db_path = os.path.join('..', 'instance', 'hrms.db')
        
    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        return

    print(f"Connecting to: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Columns to add to letter_requests
    letter_req_cols = [
        ("employee_name", "VARCHAR(150)"),
        ("employee_email", "VARCHAR(150)"),
        ("letter_date", "DATE"),
        ("template_option", "VARCHAR(50) DEFAULT 'Standard Format'"),
        ("send_email_copy", "BOOLEAN DEFAULT 0")
    ]

    # Columns to add to certificate_issues
    cert_issue_cols = [
        ("recipient_email", "VARCHAR(150)"),
        ("template_option", "VARCHAR(50) DEFAULT 'Standard Format'"),
        ("send_email_copy", "BOOLEAN DEFAULT 0")
    ]

    try:
        # Update letter_requests
        print("Checking 'letter_requests' table...")
        cursor.execute("PRAGMA table_info(letter_requests)")
        existing_cols = [row[1] for row in cursor.fetchall()]
        
        for col_name, col_type in letter_req_cols:
            if col_name not in existing_cols:
                print(f"   + Adding column '{col_name}'...")
                cursor.execute(f"ALTER TABLE letter_requests ADD COLUMN {col_name} {col_type}")
            else:
                print(f"   - Column '{col_name}' already exists.")

        # Update certificate_issues
        print("\nChecking 'certificate_issues' table...")
        cursor.execute("PRAGMA table_info(certificate_issues)")
        existing_cols = [row[1] for row in cursor.fetchall()]

        for col_name, col_type in cert_issue_cols:
            if col_name not in existing_cols:
                print(f"   + Adding column '{col_name}'...")
                cursor.execute(f"ALTER TABLE certificate_issues ADD COLUMN {col_name} {col_type}")
            else:
                print(f"   - Column '{col_name}' already exists.")

        conn.commit()
        print("\n✅ Database schema updated successfully!")

    except Exception as e:
        print(f"❌ Error updating database: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    update_hr_docs_schema()