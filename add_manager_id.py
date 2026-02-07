import sqlite3

db_path = "instance/hrms.db"   # do NOT change unless your db is elsewhere

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE employees ADD COLUMN manager_id INTEGER;")
    print("✅ Column 'manager_id' added successfully")
except Exception as e:
    print("⚠️ Error:", e)

conn.commit()
conn.close()
