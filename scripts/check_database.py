import sqlite3
import os

def check_schema():
    db_path = os.path.join('instance', 'hrms.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(f"🔍 Checking users table schema in {db_path}...")
    
    try:
        # Get table info
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        
        if not columns:
            print("❌ Table 'users' does not exist!")
            return

        print("Columns in users table:")
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
        
        # Check if role/user_role exists
        column_names = [col[1] for col in columns]
        
        if 'role' in column_names:
            print("\n✅ 'role' column exists. Database matches Model.")
        elif 'user_role' in column_names:
            print("\n⚠️ 'user_role' column exists.")
            print("   Mismatch detected: Model expects 'role', Database has 'user_role'.")
            print("   Run fix_database.py to fix this.")
        else:
            print("\n❌ Neither 'role' nor 'user_role' found!")
            
        if 'reset_otp' in column_names:
            print("✅ 'reset_otp' column exists.")
        else:
            print("❌ 'reset_otp' column MISSING! Run scripts/add_reset_columns.py")
            
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_schema()