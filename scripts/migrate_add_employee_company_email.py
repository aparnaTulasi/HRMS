import sqlite3

db_path = "instance/hrms.db"
con = sqlite3.connect(db_path)
cur = con.cursor()

cur.execute("PRAGMA table_info(employees)")
cols = [r[1] for r in cur.fetchall()]

if "company_email" not in cols:
    cur.execute("ALTER TABLE employees ADD COLUMN company_email VARCHAR(120);")
    print("✅ Added employees.company_email")
else:
    print("ℹ️ employees.company_email already exists")

con.commit()
con.close()