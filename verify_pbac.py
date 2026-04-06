import sys
import os
import json
from flask import Flask

# Add project root to sys.path
sys.path.append(os.getcwd())

from app import app
from models import db
from models.user import User
from models.permission import UserPermission
from models.company import Company
from werkzeug.security import generate_password_hash
import jwt
from datetime import datetime, timedelta
from config import Config

def test_pbac_enforcement():
    with app.app_context():
        print("--- VERIFYING PBAC ENFORCEMENT ---")
        
        # 1. Setup in-memory DB
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        db.create_all()
        
        client = app.test_client()
        comp = Company(subdomain='testcomp', company_name='Test Comp', company_code='TC01')
        db.session.add(comp)
        db.session.commit()
        
        # Scenario 1: SuperAdmin (Format Variant)
        sa = User(email='sa@test.com', password=generate_password_hash('pw123'), role='SUPERADMIN', company_id=comp.id, status='ACTIVE')
        db.session.add(sa)
        db.session.commit()
        
        # Scenario 2: Admin WITH VIEW permission
        admin_view = User(email='admin_view@test.com', password=generate_password_hash('pw123'), role='ADMIN', company_id=comp.id, status='ACTIVE')
        db.session.add(admin_view)
        db.session.commit()
        perm_view = UserPermission(user_id=admin_view.id, permission_code='ROLE_MANAGEMENT_VIEW')
        db.session.add(perm_view)
        db.session.commit()
        
        # Scenario 3: Admin WITHOUT permission
        admin_none = User(email='admin_none@test.com', password=generate_password_hash('pw123'), role='ADMIN', company_id=comp.id, status='ACTIVE')
        db.session.add(admin_none)
        db.session.commit()

        test_cases = [
            (sa, 'SUPERADMIN', 200, "SuperAdmin (Variant) should have access"),
            (admin_view, 'ADMIN (with VIEW perm)', 200, "Admin with explicit permission should have access"),
            (admin_none, 'ADMIN (no perm)', 403, "Admin without permission should be blocked")
        ]
        
        for user, label, expected_status, note in test_cases:
            token = jwt.encode({
                'user_id': user.id,
                'role': user.role,
                'company_id': user.company_id,
                'exp': datetime.utcnow() + timedelta(hours=1)
            }, Config.SECRET_KEY, algorithm="HS256")
            
            headers = {'Authorization': f'Bearer {token}'}
            resp = client.get('/api/superadmin/permissions/modules', headers=headers)
            
            print(f"Test case: {label:25} | Result Status: {resp.status_code} | Expected: {expected_status}")
            if resp.status_code != expected_status:
                print(f"   ❌ FAILED: {note}")
            else:
                print(f"   ✅ PASSED")
            
        print("\n--- PBAC TEST COMPLETE ---")

if __name__ == "__main__":
    test_pbac_enforcement()
