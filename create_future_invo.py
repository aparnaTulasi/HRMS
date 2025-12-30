import os
from app import app
from models.master import db, Company, UserMaster
from utils.create_db import create_company_db, seed_admin_user
from utils.auth_utils import hash_password

with app.app_context():
    # The subdomain you are trying to use in Postman
    target_subdomain = "Future_Invo"
    
    print(f"🔨 Checking company: {target_subdomain}...")
    
    if not Company.query.filter_by(subdomain=target_subdomain).first():
        print(f"   Creating new company '{target_subdomain}'...")
        
        # 1. Create Company Record in Master DB
        company = Company(
            company_name="Future Invo Systems",
            subdomain=target_subdomain,
            db_name="future_invo",  # Safe filename
            admin_email="admin@futureinvo.com",
            admin_password=hash_password("admin123")
        )
        db.session.add(company)
        db.session.commit()
        
        # 2. Create Tenant Database & Tables
        create_company_db(company.db_name)
        
        # 3. Seed Admin User
        seed_admin_user(company.db_name, company.id, "admin@futureinvo.com", hash_password("admin123"))
        
        # 4. Ensure Admin exists in Master DB
        if not UserMaster.query.filter_by(email="admin@futureinvo.com").first():
            admin = UserMaster(
                email="admin@futureinvo.com", 
                password=hash_password("admin123"), 
                role="ADMIN", 
                company_id=company.id, 
                is_active=True
            )
            db.session.add(admin)
            db.session.commit()
            
        print(f"✅ Company created! You can now register users under '{target_subdomain}'.")
    else:
        print(f"ℹ️  Company '{target_subdomain}' already exists.")