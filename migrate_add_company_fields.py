import sqlite3

DB_PATH = "instance/hrms.db"

def get_cols(cur):
    cur.execute("PRAGMA table_info(companies);")
    return {r[1] for r in cur.fetchall()}

def add_if_missing(cur, col, col_type):
    cols = get_cols(cur)
    if col in cols:
        print(f"✅ Already exists: {col}")
        return
    cur.execute(f"ALTER TABLE companies ADD COLUMN {col} {col_type};")
    print(f"➕ Added: {col}")

con = sqlite3.connect(DB_PATH)
cur = con.cursor()

add_if_missing(cur, "company_size", "VARCHAR(30)")
add_if_missing(cur, "state", "VARCHAR(100)")
add_if_missing(cur, "country", "VARCHAR(100)")
add_if_missing(cur, "city_branch", "VARCHAR(100)")

con.commit()
con.close()
print("✅ Done")