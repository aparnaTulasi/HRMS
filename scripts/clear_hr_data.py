from app import app
from models import db
from models.user import User
from models.employee import Employee
from models.attendance import Attendance
from models.employee_documents import EmployeeDocument
from models.employee_bank import EmployeeBankDetails
from models.employee_address import EmployeeAddress
from models.permission import UserPermission
from models.department import Department

# Try importing Leave models
try:
    from leave.models import LeaveRequest, LeaveBalance
except ImportError:
    try:
        from leave.models import Leave as LeaveRequest, LeaveBalance
    except ImportError:
        LeaveRequest = None
        LeaveBalance = None

# Try importing Payroll models
try:
    from models.payroll import PayrollRunEmployee, PayrollEarning, PayrollDeduction, PayrollSummary, EmployeeSalaryStructure
except ImportError:
    PayrollRunEmployee = None

if __name__ == "__main__":
    with app.app_context():
        print("🧹 Clearing HR data...")
        try:
            # Find all users with role 'HR'
            hr_users = User.query.filter_by(role='HR').all()
            count = 0
            for user in hr_users:
                print(f"   - Deleting User: {user.email}")
                
                # 1. Delete User Permissions
                UserPermission.query.filter_by(user_id=user.id).delete()

                # 2. Find and Delete Employee Profile & Related Data
                emp = Employee.query.filter_by(user_id=user.id).first()
                if emp:
                    # Unlink from Department (Manager)
                    managed_depts = Department.query.filter_by(manager_id=emp.id).all()
                    for dept in managed_depts:
                        dept.manager_id = None

                    # Delete Leaves
                    if LeaveRequest:
                        LeaveRequest.query.filter_by(employee_id=emp.id).delete()
                    if LeaveBalance:
                        LeaveBalance.query.filter_by(employee_id=emp.id).delete()

                    # Delete Payroll Data
                    if PayrollRunEmployee:
                        PayrollEarning.query.filter_by(employee_id=emp.id).delete()
                        PayrollDeduction.query.filter_by(employee_id=emp.id).delete()
                        PayrollSummary.query.filter_by(employee_id=emp.id).delete()
                        PayrollRunEmployee.query.filter_by(employee_id=emp.id).delete()
                        EmployeeSalaryStructure.query.filter_by(employee_id=emp.id).delete()

                    Attendance.query.filter_by(employee_id=emp.id).delete()
                    EmployeeDocument.query.filter_by(employee_id=emp.id).delete()
                    EmployeeBankDetails.query.filter_by(employee_id=emp.id).delete()
                    EmployeeAddress.query.filter_by(employee_id=emp.id).delete()
                    db.session.delete(emp)
                
                # 3. Delete the User record
                db.session.delete(user)
                count += 1
            
            db.session.commit()
            print(f"✅ Successfully cleared {count} HR record(s).")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error: {e}")