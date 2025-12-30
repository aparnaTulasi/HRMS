import os
from app import app
from models.master import db, UserMaster, Company
from utils.tenant_db import get_tenant_db_connection

def check_user_status(email):
    print(f"\n🔍 Inspecting User: {email}")
    print("="*50)
    
    # 1. Check Master Database
    user = UserMaster.query.filter_by(email=email).first()
    
    if not user:
        print("❌ User NOT found in Master Database.")
        print("   -> You should be able to register this email.")
        return

    print(f"✅ Found in Master DB (ID: {user.id})")
    
    # 2. Identify Company
    company = db.session.get(Company, user.company_id)
    if not company:
        print(f"❌ Error: User linked to non-existent Company ID {user.company_id}")
        return
        
    print(f"   🏢 Company: {company.company_name}")
    print(f"   🌐 Subdomain: {company.subdomain}")
    print(f"   👤 Admin Email: {company.admin_email}")
    print(f"      (Login as this admin to approve this user)")

    # 3. Check Tenant Database Status
    conn = get_tenant_db_connection(company.db_name)
    if not conn:
        print(f"❌ Error: Could not connect to tenant DB '{company.db_name}'")
        return
        
    cur = conn.cursor()
    cur.execute("SELECT id, status FROM hrms_employee WHERE email = ?", (email,))
    row = cur.fetchone()
    
    if row:
        emp_id, status = row
        print(f"   🆔 Employee ID (Tenant): {emp_id} (Use this ID in API: /api/admin/approve-user/{emp_id})")
        print(f"   📊 Status in Tenant DB: {status}")
        if status == 'PENDING':
            print(f"\n   ⚠️  NOTE: If API returns 0 pending, ensure you are logged in as: {company.admin_email}")
    else:
        print("❌ User found in Master DB but NOT in Tenant DB (Data inconsistency).")
    
    conn.close()

if __name__ == "__main__":
    with app.app_context():
        check_user_status("ravi@gmail.com")