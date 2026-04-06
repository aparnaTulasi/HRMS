import sys
import os
import json
from flask import Flask

# Add project root to sys.path
sys.path.append(os.getcwd())

from app import app
from models import db
from models.user import User
from models.company import Company
from werkzeug.security import generate_password_hash
import jwt
from datetime import datetime, timedelta
from config import Config

def test_permissions_access():
    with app.app_context():
        print("--- VERIFYING PERMISSIONS FIX ---")
        
        # 1. Setup in-memory DB or use existing
        # Using app context directly to test normalization logic
        from utils.role_utils import normalize_role
        print(f"Testing normalization: 'superadmin' -> {normalize_role('superadmin')}")
        print(f"Testing normalization: 'SUPER-ADMIN' -> {normalize_role('SUPER-ADMIN')}")
        
        # Mocking a request for ADMIN
        from routes.permissions import get_permission_modules
        
        # We need a client to test the actual route with decorators
        client = app.test_client()
        
        # Create a dummy company and users with different role strings
        # Switch to in-memory for safety if needed, but let's just use the current test setup logic
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        db.create_all()
        
        comp = Company(subdomain='testcomp', company_name='Test Comp', company_code='TC01')
        db.session.add(comp)
        db.session.commit()
        
        roles_to_test = [
            ('sa@test.com', 'SUPER_ADMIN'),
            ('sa2@test.com', 'SUPERADMIN'),
            ('sa3@test.com', 'SUPER-ADMIN'),
            ('admin@test.com', 'ADMIN'),
            ('hr@test.com', 'HR'),
            ('emp@test.com', 'EMPLOYEE')
        ]
        
        for email, role in roles_to_test:
            user = User(email=email, password=generate_password_hash('pw123'), role=role, company_id=comp.id, status='ACTIVE')
            db.session.add(user)
            db.session.commit()
            
            # Generate token
            token = jwt.encode({
                'user_id': user.id,
                'role': user.role,
                'company_id': user.company_id,
                'exp': datetime.utcnow() + timedelta(hours=1)
            }, Config.SECRET_KEY, algorithm="HS256")
            
            headers = {'Authorization': f'Bearer {token}'}
            resp = client.get('/api/superadmin/permissions/modules', headers=headers)
            
            expected_status = 200 if normalize_role(role) in ['SUPER_ADMIN', 'ADMIN', 'HR'] else 403
            
            print(f"Testing Role: {role:15} | Status: {resp.status_code} | Expected: {expected_status}")
            
            if resp.status_code == 200:
                data = resp.get_json()
                modules = data.get('data', {}).get('modules', [])
                print(f"   Modules count: {len(modules)}")
                if len(modules) == 0:
                    print("   ❌ ALERT: Modules list is EMPTY despite 200 OK")
            
        print("\n--- TEST COMPLETE ---")

if __name__ == "__main__":
    test_permissions_access()
