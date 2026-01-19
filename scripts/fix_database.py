import sqlite3
import os

def fix_user_table():
    db_path = os.path.join('instance', 'hrms.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Fixing users table...")
    
    try:
        # Check current columns
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print(f"Current columns: {column_names}")

        # Check if we need to fix anything
        if 'role' in column_names and 'updated_at' in column_names:
            print("✅ Database schema is already correct.")
            conn.close()
            return

        print("⚠️ Schema mismatch detected. Recreating table with correct columns...")

        # Determine source for 'role'
        role_selector = "'ADMIN'" # Default for new column
        if 'user_role' in column_names:
            role_selector = "user_role"
            print("   - Mapping existing 'user_role' to 'role'")
        else:
            print("   - 'role' column missing, setting default to 'ADMIN'")

        # Determine source for 'updated_at'
        updated_at_selector = "created_at" # Default to created_at if missing
        if 'updated_at' in column_names:
            updated_at_selector = "updated_at"
        
        # SQLite transaction to recreate table
        cursor.executescript(f"""
            CREATE TABLE users_new (
                id INTEGER PRIMARY KEY,
                email VARCHAR(120) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                role VARCHAR(20) NOT NULL,
                company_id INTEGER,
                status VARCHAR(20) DEFAULT 'PENDING',
                portal_prefix VARCHAR(50),
                otp VARCHAR(6),
                otp_expiry DATETIME,
                reset_otp VARCHAR(6),
                reset_otp_expiry DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies(id)
            );
            
            INSERT INTO users_new (id, email, password, role, company_id, status, portal_prefix, otp, otp_expiry, created_at, updated_at)
            SELECT id, email, password, {role_selector}, company_id, status, portal_prefix, otp, otp_expiry, created_at, {updated_at_selector}
            FROM users;
            
            DROP TABLE users;
            
            ALTER TABLE users_new RENAME TO users;
        """)
        
        print("✅ Table updated successfully!")
            
        conn.commit()
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()
    
    print("\nDone! You can now restart your Flask app.")

if __name__ == "__main__":
    fix_user_table()