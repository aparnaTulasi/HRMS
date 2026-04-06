import sys
import os
import unittest
import json
from flask import Flask, g
from werkzeug.security import generate_password_hash
import jwt
from datetime import datetime, timedelta

# Add the project directory to sys.path
sys.path.append(os.getcwd())

from app import app
from models import db
from models.user import User
from models.company import Company
from models.employee import Employee
from config import Config

class TestDynamicDashboardURL(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        cls.client = app.test_client()
        with app.app_context():
            db.create_all()
            
            # 1. Create a test company
            cls.company = Company(
                company_name="Test Company",
                subdomain="testcomp",
                company_code="TC001",
                company_prefix="TC"
            )
            db.session.add(cls.company)
            db.session.commit()
            
            # 2. Create test users
            # User A: Correct
            cls.user_a = User(
                email="aparna@testcomp.com",
                password=generate_password_hash("password123"),
                role="HR",
                company_id=cls.company.id,
                status="ACTIVE"
            )
            db.session.add(cls.user_a)
            
            # User B: Another account
            cls.user_b = User(
                email="ravi@other.com",
                password=generate_password_hash("password123"),
                role="EMPLOYEE",
                company_id=cls.company.id,
                status="ACTIVE"
            )
            db.session.add(cls.user_b)
            db.session.commit()
            
            # Create Employee Profiles
            cls.emp_a = Employee(user_id=cls.user_a.id, company_id=cls.company.id, full_name="Aparna HR")
            cls.emp_b = Employee(user_id=cls.user_b.id, company_id=cls.company.id, full_name="Ravi Emp")
            db.session.add_all([cls.emp_a, cls.emp_b])
            db.session.commit()

    def get_token(self, user_id):
        return jwt.encode({
            'user_id': user_id,
            'role': 'HR',
            'company_id': self.company.id,
            'exp': datetime.utcnow() + timedelta(hours=1)
        }, Config.SECRET_KEY, algorithm="HS256")

    def test_01_login_response(self):
        """Verify login returns structured user data and dynamic redirect_url."""
        with app.app_context():
            response = self.client.post('/api/auth/login', json={
                'email': 'aparna@testcomp.com',
                'password': 'password123'
            })
            data = response.get_json()
            
            self.assertEqual(response.status_code, 200, f"Login failed: {data}")
            self.assertIn('redirect_url', data)
            self.assertIn('/aparna/testcomp/dashboard', data['redirect_url'])
            self.assertEqual(data['user']['username'], 'aparna')
            self.assertEqual(data['user']['company'], 'testcomp')

    def test_02_valid_dynamic_dashboard_access(self):
        """Verify that a user can access their own dynamic dashboard URL."""
        with app.app_context():
            token = self.get_token(self.user_a.id)
            headers = {'Authorization': f'Bearer {token}'}
            
            # Access: /aparna/testcomp/dashboard
            response = self.client.get('/aparna/testcomp/dashboard', headers=headers)
            data = response.get_json()
            
            self.assertEqual(response.status_code, 200, f"Access failed: {data}")
            self.assertTrue(data['success'])
            self.assertEqual(data['role'], 'HR')

    def test_03_forbidden_mismatch_access(self):
        """Verify that a user CANNOT access another user's dynamic dashboard URL (403)."""
        with app.app_context():
            token = self.get_token(self.user_a.id) # Token is for Aparna
            headers = {'Authorization': f'Bearer {token}'}
            
            # Attempt to access Ravi's URL: /ravi/testcomp/dashboard
            response = self.client.get('/ravi/testcomp/dashboard', headers=headers)
            
            self.assertEqual(response.status_code, 403)
            self.assertIn('Forbidden', response.get_json()['message'])

    def test_04_forbidden_company_mismatch(self):
        """Verify that a user CANNOT access a dashboard for a different company (403)."""
        with app.app_context():
            token = self.get_token(self.user_a.id)
            headers = {'Authorization': f'Bearer {token}'}
            
            # Attempt to access: /aparna/wrongcomp/dashboard
            response = self.client.get('/aparna/wrongcomp/dashboard', headers=headers)
            
            self.assertEqual(response.status_code, 403)

if __name__ == "__main__":
    unittest.main()
