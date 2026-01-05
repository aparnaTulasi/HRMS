import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import sqlite3

def list_tables(db_path):
    """Lists all tables and their columns in the given SQLite database."""
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        return

    print(f"\n📂 Database: {db_path}")
    print("=" * 50)

    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Get list of tables
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cur.fetchall()
        
        if not tables:
            print("   (No tables found)")
        
        for table in tables:
            table_name = table[0]
            if table_name == "sqlite_sequence":
                continue
                
            print(f" 📄 Table: {table_name}")
            
            # Get columns
            cur.execute(f"PRAGMA table_info({table_name})")
            columns = cur.fetchall()
            # col[1] is name, col[2] is type
            col_defs = [f"{col[1]} ({col[2]})" for col in columns]
            print(f"    └── Columns: {', '.join(col_defs)}")
            
            # Get row count
            cur.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cur.fetchone()[0]
            print(f"    └── Rows: {count}")
            print("-" * 30)
            
        conn.close()
    except Exception as e:
        print(f"❌ Error reading database: {e}")

if __name__ == "__main__":
    # 1. Inspect Master Database
    list_tables(os.path.join(os.path.dirname(__file__), "..", "master.db"))
    
    # 2. Inspect Tenant Database (Aparna Corp)
    tenant_path = os.path.join(os.path.dirname(__file__), "..", "tenants", "aparna.db")
    list_tables(tenant_path)