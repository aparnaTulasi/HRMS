import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def check_code_column():
    conn = mysql.connector.connect(
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME")
    )
    cursor = conn.cursor()
    cursor.execute("SHOW COLUMNS FROM leave_types LIKE 'code'")
    res = cursor.fetchone()
    if res:
        print(f"✅ Found code column: {res}")
    else:
        print("❌ code column NOT found in leave_types!")
    cursor.close()
    conn.close()

if __name__ == "__main__":
    check_code_column()
