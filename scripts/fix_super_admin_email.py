import sqlite3
import os

def fix_super_admin_email():
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

    try:
        # Update super_admins email from users table
        print("Updating super_admins email from users table...")
        cursor.execute("""
            UPDATE super_admins
            SET email = (SELECT email FROM users WHERE users.id = super_admins.user_id)
            WHERE email IS NULL OR email = ''
        """)
        
        if cursor.rowcount > 0:
            print(f"✅ Updated {cursor.rowcount} super_admin records with email.")
        else:
            print("✅ No super_admin records needed email update.")

        conn.commit()

    except Exception as e:
        print(f"❌ Error updating database: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_super_admin_email()
