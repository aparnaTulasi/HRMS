from app import app, db
from models.user import User
from models.company import Company
from models.employee import Employee
from models.permission import UserPermission
from models.role import Role, RolePermission
from werkzeug.security import generate_password_hash
import json

def setup_test_data():
    with app.app_context():
        # 1. Get/Create Test Company
        company = Company.query.first()
        if not company:
            company = Company(company_name="Test Corp", subdomain="testcorp")
            db.session.add(company)
            db.session.commit()
        
        # 2. Create a Role with specific permissions
        role_name = "TEST_ROLE_99"
        role = Role.query.filter_by(name=role_name, company_id=company.id).first()
        if role:
            RolePermission.query.filter_by(role_id=role.id).delete()
            db.session.delete(role)
            db.session.commit()
            
        role = Role(name=role_name, company_id=company.id, description="Testing Role")
        db.session.add(role)
        db.session.flush()
        
        # Add role-based permissions: Reports View
        rp1 = RolePermission(role_id=role.id, permission_code="REPORTS_VIEW")
        db.session.add(rp1)
        
        # 3. Create a User with this role and direct granular permissions
        test_email = "tester_role_perms@example.com"
        u = User.query.filter_by(email=test_email).first()
        if u:
            UserPermission.query.filter_by(user_id=u.id).delete()
            Employee.query.filter_by(user_id=u.id).delete()
            db.session.delete(u)
            db.session.commit()
            
        u = User(
            email=test_email,
            password=generate_password_hash("password123"),
            role=role_name,
            company_id=company.id,
            status="ACTIVE"
        )
        db.session.add(u)
        db.session.flush()
        
        # Add direct granular permissions: Payroll View (different from role)
        up1 = UserPermission(user_id=u.id, permission_code="PAYROLL_VIEW", granted_by=1)
        db.session.add(up1)
        
        db.session.commit()
        return u.id, test_email

def verify_permissions(user_id):
    with app.app_context():
        user = User.query.get(user_id)
        if not user:
            print(f"User {user_id} not found")
            return
            
        print(f"\n--- Testing Permissions for User: {user.email} (Role: {user.role}) ---")
        
        # 1. Test the new model method
        all_perms = user.get_all_permissions()
        print(f"Aggregated Permissions: {all_perms}")
        
        expected = ["REPORTS_VIEW", "PAYROLL_VIEW"]
        missing = [p for p in expected if p not in all_perms]
        
        if not missing:
            print("SUCCESS: Both direct and role-based permissions are present.")
        else:
            print(f"FAILURE: Missing permissions: {missing}")

        # 2. Test has_permission
        print(f"Check REPORTS_VIEW: {'PASS' if user.has_permission('REPORTS_VIEW') else 'FAIL'}")
        print(f"Check PAYROLL_VIEW: {'PASS' if user.has_permission('PAYROLL_VIEW') else 'FAIL'}")
        print(f"Check RANDOM_PERM (should fail): {'FAIL' if not user.has_permission('RANDOM_PERM') else 'PASS'}")

        # 3. Test Super Admin Override
        sa_email = "sa_test_perms@example.com"
        sa = User.query.filter_by(role="SUPER_ADMIN").first()
        if not sa:
            sa = User(email=sa_email, password=generate_password_hash("pass"), role="SUPER_ADMIN", status="ACTIVE")
            db.session.add(sa)
            db.session.commit()
            
        print(f"\n--- Testing Super Admin Override ({sa.email}) ---")
        if sa.has_permission("ANYTHING_GOES"):
            print("SUCCESS: Super Admin has all permissions.")
        else:
            print("FAILURE: Super Admin check failed.")


if __name__ == "__main__":
    uid, email = setup_test_data()
    verify_permissions(uid)
