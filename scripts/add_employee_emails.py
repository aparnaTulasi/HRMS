import sqlite3

con = sqlite3.connect("instance/hrms.db")
cur = con.cursor()

def add_col(table, col, coltype):
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    if col not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {coltype};")
        print(f"✅ Added {col} to {table}")
    else:
        print(f"ℹ️ {col} already exists in {table}")

add_col("employees", "personal_email", "VARCHAR(120)")
add_col("employees", "company_email", "VARCHAR(120)")

con.commit()
con.close()
print("✅ Done")
