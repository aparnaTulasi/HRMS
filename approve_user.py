import os
from app import app
from models.master import db, UserMaster, Company
from utils.tenant_db import get_tenant_db_connection

def approve_user_manually(email):
    print(f"\n🚀 Approving User: {email}")
    print("="*50)
    
    # 1. Find in Master DB
    user = UserMaster.query.filter_by(email=email).first()
    if not user:
        print("❌ User not found in Master Database.")
        return

    # 2. Identify Company
    # Using db.session.get() to avoid LegacyAPIWarning
    company = db.session.get(Company, user.company_id)
    if not company:
        print(f"❌ Error: User linked to non-existent Company ID {user.company_id}")
        return
        
    print(f"   🏢 Company: {company.company_name}")
    print(f"   🌐 Subdomain: {company.subdomain}")

    # 3. Connect to Tenant DB
    conn = get_tenant_db_connection(company.db_name)
    if not conn:
        print(f"❌ Error: Could not connect to tenant DB '{company.db_name}'")
        return
        
    try:
        cur = conn.cursor()
        
        # Check current status
        cur.execute("SELECT id, status FROM hrms_employee WHERE email = ?", (email,))
        row = cur.fetchone()
        
        if not row:
            print("❌ User not found in Tenant DB.")
            return
            
        emp_id, current_status = row
        print(f"   📊 Current Status: {current_status}")
        
        if current_status == "ACTIVE":
            print("   ✅ User is already ACTIVE.")
        else:
            # Update to ACTIVE
            cur.execute("UPDATE hrms_employee SET status = 'ACTIVE' WHERE id = ?", (emp_id,))
            conn.commit()
            print(f"   ✅ User {email} (Employee ID: {emp_id}) has been APPROVED.")
            
    except Exception as e:
        print(f"❌ Database Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    with app.app_context():
        approve_user_manually("ravi@gmail.com")