from app import app, db
from models.user import User
from models.employee import Employee
from models.payroll import PaySlip, PayGrade
from flask import g
import traceback

def test_payroll_access_matrix():
    with app.app_context():
        print("--- PREREQUISITE CHECK: Finding Users ---")
        roles_to_test = ["SUPER_ADMIN", "ADMIN", "HR", "MANAGER"]
        test_users = {}
        
        for role in roles_to_test:
            u = User.query.filter_by(role=role).first()
            if u:
                test_users[role] = u
                print(f"Found {role}: {u.email} (Company ID: {u.company_id})")
            else:
                print(f"WARN: No user found with role {role}")

        if not test_users:
            print("ERROR: No users found to test.")
            return

        from routes.payroll import admin_list_payslips, _company_id
        from flask import request

        results = []

        for role, user in test_users.items():
            print(f"\n--- Testing Role: {role} ({user.email}) ---")
            
            with app.test_request_context():
                g.user = user
                
                # Test 1: Permission Check (Direct DB Check)
                perms = [p.permission_code for p in user.permissions]
                has_payroll_view = any("PAYROLL_VIEW" in p for p in perms)
                print(f"DB Permissions Check: {'PASSED' if has_payroll_view else 'FAILED'} (Explicit PAYROLL_VIEW found)")
                
                # Test 2: Role Visibility Logic
                cid = _company_id()
                q = PaySlip.query.filter_by(company_id=cid)
                initial_count = q.count()
                
                if role == "HR":
                    # HR has special filter
                    q = q.join(Employee, PaySlip.employee_id == Employee.id).join(User, Employee.user_id == User.id)
                    q = q.filter(User.role.in_(["MANAGER", "EMPLOYEE"]))
                    visibility = "RESTRICTED (Manager/Employee only)"
                else:
                    visibility = "FULL (All roles in company)"
                
                count_visible = q.count()
                print(f"Visibility Access: {visibility}")
                print(f"Records Visible: {count_visible} out of {initial_count} total in company")
                
                # Test 3: Route Simulation (Includes Decorator logic if called via app.test_client)
                # But here we call function directly, so we just check if it returns data
                try:
                    response, status_code = admin_list_payslips()
                    if status_code == 200:
                        print(f"Route API Check: PASSED (200)")
                    else:
                        print(f"Route API Check: FAILED ({status_code})")
                except Exception as e:
                    print(f"Route API Check: EXCEPTION ({str(e)})")
                    status_code = 500
                
                results.append({
                    "role": role,
                    "permission": "PASS" if has_payroll_view else "WARN",
                    "visibility": visibility,
                    "api_route": "PASS" if status_code == 200 else "FAIL"
                })

        print("\n--- FINAL TEST MATRIX ---")
        print("{:<15} {:<15} {:<30} {:<15}".format("Role", "DB Perms", "Visibility Mode", "Route API"))
        for r in results:
            print("{:<15} {:<15} {:<30} {:<15}".format(r['role'], r['permission'], r['visibility'], r['api_route']))

if __name__ == "__main__":
    test_payroll_access_matrix()
