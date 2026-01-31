import sqlite3

DB_PATH = "instance/hrms.db"

con = sqlite3.connect(DB_PATH)
cur = con.cursor()

# 1) Create new clean table
cur.execute("""
CREATE TABLE IF NOT EXISTS companies_new (
    id INTEGER PRIMARY KEY,
    company_name VARCHAR(100) NOT NULL,
    subdomain VARCHAR(50) NOT NULL,
    company_code VARCHAR(20),
    company_size VARCHAR(30),
    industry VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100),
    city_branch VARCHAR(100),
    created_at DATETIME,
    updated_at DATETIME
);
""")

# 2) Copy data from old table to new table (only matching columns)
cur.execute("""
INSERT INTO companies_new (id, company_name, subdomain, company_code, industry, created_at, updated_at)
SELECT id, company_name, subdomain, company_code, industry, created_at, updated_at FROM companies;
""")

# 3) Drop old table
cur.execute("DROP TABLE companies;")

# 4) Rename new table
cur.execute("ALTER TABLE companies_new RENAME TO companies;")

con.commit()
con.close()

print("✅ companies table rebuilt (unwanted columns removed)")