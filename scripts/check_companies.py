import sqlite3
import os

def check_companies():
    db_path = os.path.join('instance', 'hrms.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n📊 Existing Companies in Database:")
    cursor.execute("SELECT id, company_name, subdomain, created_at FROM companies")
    companies = cursor.fetchall()
    
    if not companies:
        print("   (No companies found)")
    else:
        for c in companies:
            print(f"   ID: {c[0]} | Name: {c[1]} | Subdomain: {c[2]}")
    
    print("\n")
    conn.close()

if __name__ == "__main__":
    check_companies()