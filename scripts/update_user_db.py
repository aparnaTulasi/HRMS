import sqlite3
import os

# Calculate path to the database file
# Assumes this script is in HRMS/scripts/ and db is in HRMS/instance/
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(BASE_DIR, "instance", "hrms.db")

def update_database():
    print("🚀 Starting Database Update...")
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Database file not found at: {DB_PATH}")
        print("   Please ensure the application has run at least once.")
        return

    print(f"🔌 Connecting to database: {DB_PATH}")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Verify 'users' table exists (explicit check)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            print("❌ Error: Table 'users' not found in the database.")
            conn.close()
            return

        # Get list of existing columns in users table
        cursor.execute("PRAGMA table_info(users)")
        existing_columns = [info[1] for info in cursor.fetchall()]
        
        # Define columns to add
        new_columns = [
            ("phone", "VARCHAR(20)"),
            ("profile_completed", "BOOLEAN DEFAULT 0"),
            ("profile_locked", "BOOLEAN DEFAULT 0")
        ]

        for col_name, col_type in new_columns:
            if col_name not in existing_columns:
                print(f"🛠️  Adding column '{col_name}' to 'users' table")
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
            else:
                print(f"✅ Column '{col_name}' already exists.")

        # Attempt to add the composite unique index
        # Note: SQLite does not easily allow dropping the old UNIQUE constraint on 'email' 
        # without recreating the table, but we can add the new composite constraint.
        print("🛠️  Updating indexes...")
        try:
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS unique_company_email ON users(company_id, email)")
            print("✅ Composite unique index (company_id, email) ensured.")
        except Exception as e:
            print(f"⚠️  Index creation note: {e}")

        conn.commit()
        conn.close()
        print("\n✨ Database schema updated successfully!")
        
    except Exception as e:
        print(f"\n❌ Error updating database: {e}")

if __name__ == "__main__":
    update_database()