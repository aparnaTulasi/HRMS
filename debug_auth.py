import sys
import os
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
from routes.auth import auth_bp

def test_login_manually():
    print("Testing LOGIN...")
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        # Create a test company
        company = Company(
            company_name="Test Company",
            subdomain="testcomp",
            company_code="TC001",
            company_prefix="TC"
        )
        db.session.add(company)
        db.session.commit()
        
        # Create test users
        user = User(
            email="aparna@testcomp.com",
            password=generate_password_hash("password123"),
            role="HR",
            company_id=company.id,
            status="ACTIVE"
        )
        db.session.add(user)
        db.session.commit()
        
        client = app.test_client()
        response = client.post('/api/auth/login', json={
            'email': 'aparna@testcomp.com',
            'password': 'password123'
        })
        print(f"Login Response Status: {response.status_code}")
        print(f"Login Response Body: {response.get_data(as_text=True)}")

if __name__ == "__main__":
    test_login_manually()
