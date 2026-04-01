import os
import pymysql
from config import Config

# Extract DB credentials from Config
db_uri = Config.SQLALCHEMY_DATABASE_URI
# mysql+pymysql://root:password@localhost/hrms_db
# Let's parse it manually or just use the URI if possible.
# Actually, I'll just use the standard credentials from the environment if available,
# or I'll use the URI string for a direct pymysql connection.

def fix_db():
    try:
        # Assuming mysql+pymysql://user:pass@host/db
        parts = db_uri.replace('mysql+pymysql://', '').replace('/', '@').split('@')
        user_pass = parts[0].split(':')
        user = user_pass[0]
        password = user_pass[1] if len(user_pass) > 1 else ''
        host = parts[1]
        db_name = parts[2]
        
        conn = pymysql.connect(host=host, user=user, password=password, database=db_name)
        cursor = conn.cursor()
        
        # 1. Update Employee 13
        cursor.execute("UPDATE employees SET designation = 'fulltimeADMIN', employment_type = 'fulltime' WHERE id = 13")
        
        # 2. Get user_id for employee 13
        cursor.execute("SELECT user_id FROM employees WHERE id = 13")
        res = cursor.fetchone()
        if res:
            user_id = res[0]
            # 3. Update User role
            cursor.execute("UPDATE users SET role = 'ADMIN', status = 'ACTIVE' WHERE id = %s", (user_id,))
            
        conn.commit()
        print("SUCCESS: Database updated manually.")
        conn.close()
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    fix_db()
