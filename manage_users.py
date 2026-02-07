import argparse
import sys
from app import app, db
from models.user import User
from models.employee import Employee
from models.company import Company
from werkzeug.security import generate_password_hash
from datetime import datetime

def list_users(args):
    """Lists all users in the database."""
    with app.app_context():
        users = User.query.order_by(User.id).all()
        if not users:
            print("No users found in the database.")
            return
        
        print(f"{'ID':<4} {'Email':<35} {'Role':<12} {'Status':<10} {'Company ID':<12}")
        print("-" * 85)
        for user in users:
            print(f"{user.id:<4} {user.email:<35} {user.role:<12} {user.status:<10} {user.company_id or 'N/A':<12}")

def reset_password(args):
    """Resets the password for a given user email."""
    email = args.email
    new_password = args.new_password
    
    print(f"🔄 Resetting password for: {email}")
    
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        
        if not user:
            print(f"❌ User not found: {email}")
            return

        user.password = generate_password_hash(new_password)
        db.session.commit()
        print(f"✅ Password for {email} has been reset to: {new_password}")

def create_user(args):
    """Creates a new user and associated employee profile."""
    email = args.email
    password = args.password
    role = args.role.upper()
    first_name = args.first_name
    last_name = args.last_name

    with app.app_context():
        company = Company.query.first()
        if not company:
            print("❌ Error: No company found in database. Cannot create user.")
            return

        if User.query.filter_by(email=email).first():
            print(f"⚠️ User {email} already exists.")
            return

        print(f"🆕 Creating user {email}...")

        new_user = User(
            email=email,
            password=generate_password_hash(password),
            role=role,
            company_id=company.id,
            status='ACTIVE'
        )
        db.session.add(new_user)
        db.session.flush()

        new_employee = Employee(
            user_id=new_user.id,
            company_id=company.id,
            employee_id=f"EMP-{new_user.id:04d}",
            first_name=first_name,
            last_name=last_name,
            company_email=email,
            personal_email=email,
            date_of_joining=datetime.utcnow().date()
        )
        db.session.add(new_employee)

        try:
            db.session.commit()
            print(f"✅ User created successfully!")
            print(f"   Email: {email}, Password: {password}, Role: {role}")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error saving to database: {e}")

def main():
    parser = argparse.ArgumentParser(description="HRMS User Management Utility.")
    subparsers = parser.add_subparsers(dest='command', help='Available commands', required=True)

    # --- List Users Command ---
    list_parser = subparsers.add_parser('list', help='List all users.')
    list_parser.set_defaults(func=list_users)

    # --- Reset Password Command ---
    reset_parser = subparsers.add_parser('reset-password', help='Reset a user\'s password.')
    reset_parser.add_argument('email', type=str, help='The email of the user to reset.')
    reset_parser.add_argument('new_password', type=str, help='The new password for the user.')
    reset_parser.set_defaults(func=reset_password)

    # --- Create User Command ---
    create_parser = subparsers.add_parser('create', help='Create a new user and employee profile.')
    create_parser.add_argument('email', type=str, help='The new user\'s email address.')
    create_parser.add_argument('password', type=str, help='The new user\'s password.')
    create_parser.add_argument('first_name', type=str, help='The user\'s first name.')
    create_parser.add_argument('last_name', type=str, help='The user\'s last name.')
    create_parser.add_argument('--role', type=str, default='EMPLOYEE', choices=['EMPLOYEE', 'HR', 'ADMIN', 'MANAGER'], help='The role of the new user.')
    create_parser.set_defaults(func=create_user)

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
