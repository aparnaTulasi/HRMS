import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import sqlite3
from config import TENANT_FOLDER, BASE_DIR

MASTER_DB_PATH = os.path.join(BASE_DIR, "master.db")

def view_data():
    print("="*60)
    print("👀 VIEWING DATABASE DATA")
    print("="*60)

    # 1. Check Master DB
    if os.path.exists(MASTER_DB_PATH):
        print(f"\n📂 MASTER DB: {MASTER_DB_PATH}")
        conn = sqlite3.connect(MASTER_DB_PATH)
        cur = conn.cursor()
        
        print("\n  [users_master] (Auth Credentials)")
        try:
            cur.execute("SELECT id, email, role, status, company_id FROM users_master")
            rows = cur.fetchall()
            if not rows: print("    (Empty)")
            for r in rows: print(f"    ID: {r[0]} | {r[1]} | {r[2]} | {r[3]} | CompID: {r[4]}")
        except Exception as e: print(f"    Error: {e}")

        print("\n  [employee] (Global Directory)")
        try:
            cur.execute("SELECT id, name, email, company_subdomain FROM employee")
            rows = cur.fetchall()
            if not rows: print("    (Empty)")
            for r in rows: print(f"    ID: {r[0]} | {r[1]} | {r[2]} | {r[3]}")
        except Exception as e: print(f"    Error: {e}")
        conn.close()
    else:
        print(f"\n❌ Master DB not found at {MASTER_DB_PATH}")

    # 2. Check Tenant DBs
    if os.path.exists(TENANT_FOLDER):
        print(f"\n📂 TENANT FOLDER: {TENANT_FOLDER}")
        for f in os.listdir(TENANT_FOLDER):
            if f.endswith(".db"):
                print(f"\n  🗄️  TENANT DB: {f}")
                try:
                    conn = sqlite3.connect(os.path.join(TENANT_FOLDER, f))
                    cur = conn.cursor()
                    
                    print("    [hrms_users]")
                    try:
                        cur.execute("SELECT id, email, role FROM hrms_users")
                        rows = cur.fetchall()
                        if not rows: print("      (Empty)")
                        for r in rows: print(f"      ID: {r[0]} | {r[1]} | {r[2]}")
                    except: print("      (Table not found)")

                    print("    [hrms_employee]")
                    try:
                        cur.execute("SELECT id, first_name, last_name, email, status FROM hrms_employee")
                        rows = cur.fetchall()
                        if not rows: print("      (Empty)")
                        for r in rows: print(f"      ID: {r[0]} | {r[1]} {r[2]} | {r[3]} | {r[4]}")
                    except: print("      (Table not found)")
                    
                    conn.close()
                except Exception as e:
                    print(f"    Error opening DB: {e}")

if __name__ == "__main__":
    view_data()