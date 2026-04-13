from app import app, db
from models.user import User
from models.company import Company
from models.employee import Employee
from models.permission import UserPermission
from constants.permissions import MODULES, ACTIONS, get_permission_code
from werkzeug.security import generate_password_hash
import secrets

def create_end_to_end_test_user():
    with app.app_context():
        # 1. Identify Super Admin and Company
        company = Company.query.first()
        if not company:
            print("No company found in the database. Please create a company first.")
            return
            
        sa = User.query.filter_by(role='SUPER_ADMIN').first()
        if not sa:
            # Create a dummy SA if needed? No, let's assume one exists or use a dummy ID
            sa_id = 1
        else:
            sa_id = sa.id

        # 2. Test Credentials
        test_email = f"tester_{secrets.token_hex(3)}@hrms.com"
        test_password = "TestUser123!"
        target_role = "EMPLOYEE"
        
        # Modules to assign
        target_modules = ["Dashboard", "Attendance", "Payroll", "Documents"]
        matrix = {mod: ["View"] for mod in target_modules}

        print(f"--- Creating End-to-End Test User ---")
        print(f"Company: {company.company_name} (Subdomain: {company.subdomain})")
        print(f"Email: {test_email}")
        print(f"Role: {target_role}")
        print(f"Assigned Modules (View Only): {target_modules}")

        try:
            # a. Create User
            new_user = User(
                email=test_email,
                password=generate_password_hash(test_password),
                role=target_role,
                company_id=company.id,
                status='ACTIVE'
            )
            db.session.add(new_user)
            db.session.flush()

            # b. Create Employee Profile
            from utils.id_generator import generate_employee_id
            new_employee = Employee(
                user_id=new_user.id,
                company_id=company.id,
                employee_id=generate_employee_id(company.id),
                full_name="Sidebar Tester",
                company_email=test_email,
                personal_email=test_email,
                status='ACTIVE',
                is_active=True
            )
            db.session.add(new_employee)

            # c. Assign Permissions
            for module, actions in matrix.items():
                for action in actions:
                    perm_code = get_permission_code(module, action)
                    user_perm = UserPermission(
                        user_id=new_user.id,
                        permission_code=perm_code,
                        granted_by=sa_id
                    )
                    db.session.add(user_perm)

            db.session.commit()
            
            print("\nSUCCESS: User created successfully!")
            print(f"LOGIN DETAILS:")
            print(f"Email: {test_email}")
            print(f"Password: {test_password}")
            print(f"Company Node: {company.subdomain}")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error creating test user: {e}")

if __name__ == "__main__":
    create_end_to_end_test_user()

