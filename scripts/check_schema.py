import sqlite3
import os

db_path = os.path.join('instance', 'hrms.db')
if not os.path.exists(db_path):
    print(f"❌ Database not found at {db_path}")
    exit()

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("📊 DATABASE SCHEMA CHECK")
print("="*50)

# Check users table
cursor.execute("PRAGMA table_info(users)")
print("\nUsers table columns:")
for col in cursor.fetchall():
    print(f"  {col[1]} ({col[2]})")

# Check companies table  
cursor.execute("PRAGMA table_info(companies)")
print("\nCompanies table columns:")
for col in cursor.fetchall():
    print(f"  {col[1]} ({col[2]})")

conn.close()