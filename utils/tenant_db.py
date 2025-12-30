import sqlite3
import os
from flask import current_app
from models.master import Company

def get_tenant_db_connection(db_name):
    """
    Establishes a connection to the tenant database.
    """
    if not db_name:
        return None
        
    # Get tenant folder from config, default to 'tenants' if not set
    tenant_folder = current_app.config.get('TENANT_FOLDER', 'tenants')
    
    # Ensure db_name has .db extension
    if not db_name.endswith('.db'):
        filename = f"{db_name}.db"
    else:
        filename = db_name
        
    db_path = os.path.join(tenant_folder, filename)
    
    if not os.path.exists(db_path):
        print(f"❌ Tenant DB not found: {db_path}")
        return None
            
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"❌ SQLite Connection Error: {e}")
        return None

def execute_tenant_query(company_id, query, params=(), commit=False):
    """
    Helper to execute a query against a tenant DB given the company ID.
    Used by auth/routes.py
    """
    company = Company.query.get(company_id)
    if not company:
        print(f"❌ Company ID {company_id} not found")
        return None
        
    conn = get_tenant_db_connection(company.db_name)
    if not conn:
        return None
        
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        if commit:
            conn.commit()
            return True
        result = cur.fetchall()
        return result
    except Exception as e:
        print(f"❌ Query Error in {company.db_name}: {e}")
        return None
    finally:
        if conn:
            conn.close()
