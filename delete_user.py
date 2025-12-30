import os
from app import app
from models.master import db, UserMaster, Company
from utils.tenant_db import get_tenant_db_connection

def delete_user(email):
    print(f"\n🗑️  Deleting User: {email}")
    print("="*50)
    
    # 1. Find in Master DB
    user = UserMaster.query.filter_by(email=email).first()
    if not user:
        print("❌ User not found in Master Database.")
        return

    print(f"✅ Found in Master DB (ID: {user.id})")
    
    # 2. Identify Company to clean up Tenant DB
    company = db.session.get(Company, user.company_id)
    if company:
        print(f"   🏢 Linked to Company: {company.company_name} ({company.subdomain})")
        
        conn = get_tenant_db_connection(company.db_name)
        if conn:
            try:
                cur = conn.cursor()
                # Find employee ID in tenant DB
                cur.execute("SELECT id FROM hrms_employee WHERE email = ?", (email,))
                row = cur.fetchone()
                
                if row:
                    emp_id = row[0]
                    # Delete from related tables first (Foreign Key constraints)
                    cur.execute("DELETE FROM hrms_job_details WHERE employee_id = ?", (emp_id,))
                    cur.execute("DELETE FROM hrms_bank_details WHERE employee_id = ?", (emp_id,))
                    cur.execute("DELETE FROM hrms_address_details WHERE employee_id = ?", (emp_id,))
                    cur.execute("DELETE FROM hrms_employee WHERE id = ?", (emp_id,))
                    cur.execute("DELETE FROM hrms_users WHERE email = ?", (email,))
                    conn.commit()
                    print(f"   ✅ Deleted from Tenant DB ({company.db_name})")
                else:
                    print("   ⚠️  User not found in Tenant DB (skipping)")
                conn.close()
            except Exception as e:
                print(f"   ❌ Error cleaning tenant DB: {e}")
    
    # 3. Delete from Master DB
    db.session.delete(user)
    db.session.commit()
    print("✅ Deleted from Master DB")
    print(f"\n🎉 User {email} has been removed. You can now re-register them.")

if __name__ == "__main__":
    with app.app_context():
        delete_user("ravi2@gmail.com")