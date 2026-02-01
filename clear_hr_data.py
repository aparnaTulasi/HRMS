from app import app
from models import db
from models.user import User
from models.employee import Employee
from models.attendance import Attendance
from models.employee_documents import EmployeeDocument
from models.employee_bank import EmployeeBankDetails
from models.employee_address import EmployeeAddress
from models.permission import UserPermission

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