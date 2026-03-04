import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from models import db
from models.user import User
from werkzeug.security import generate_password_hash

def create_test_users():
    with app.app_context():
        users = [
            {
                'username': 'superadmin',
                'email': 'superadmin@hrms.com',
                'password': 'admin123',
                'is_superadmin': True,
                'is_admin': True,
                'is_hr': True,
                'role': 'SUPER_ADMIN'
            },
            {
                'username': 'admin',
                'email': 'admin@hrms.com',
                'password': 'admin123',
                'is_admin': True,
                'is_hr': True,
                'role': 'ADMIN'
            },
            {
                'username': 'hruser',
                'email': 'hr@hrms.com',
                'password': 'hr123',
                'is_hr': True,
                'role': 'HR'
            },
            {
                'username': 'employee1',
                'email': 'employee@hrms.com',
                'password': 'emp123',
                'role': 'EMPLOYEE'
            }
        ]
        
        for user_data in users:
            existing = User.query.filter_by(email=user_data['email']).first()
            if not existing:
                user = User(
                    username=user_data['username'],
                    email=user_data['email'],
                    password=generate_password_hash(user_data['password']),
                    is_active=True,
                    is_admin=user_data.get('is_admin', False),
                    is_superadmin=user_data.get('is_superadmin', False),
                    is_hr=user_data.get('is_hr', False),
                    role=user_data.get('role', 'EMPLOYEE')
                )
                db.session.add(user)
                print(f"✅ Created user: {user_data['email']}")
            else:
                print(f"⚠️  User already exists: {user_data['email']}")
        
        db.session.commit()
        print("\n✨ Test users created!")

if __name__ == '__main__':
    create_test_users()