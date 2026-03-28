import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def verify_schema():
    conn = mysql.connector.connect(
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME")
    )
    cursor = conn.cursor()
    print("Columns in leave_types:")
    cursor.execute("DESCRIBE leave_types")
    for col in cursor.fetchall():
        print(col)
    
    print("\nColumns in leave_requests:")
    cursor.execute("DESCRIBE leave_requests")
    for col in cursor.fetchall():
        print(col)
        
    cursor.close()
    conn.close()

if __name__ == "__main__":
    verify_schema()
