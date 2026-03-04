from app import app
from models import db
from models.user import User
from models.employee import Employee
from models.attendance import Attendance
from models.employee_address import EmployeeAddress
from models.employee_bank import EmployeeBankDetails
from models.employee_documents import EmployeeDocument

if __name__ == "__main__":
    with app.app_context():
        emails = [
            "bandelapravalika1460@gmail.com"
        ]
        
        print("--- Starting Cleanup ---")
        for email in emails:
            user = User.query.filter_by(email=email).first()
            if not user:
                print(f"User {email} not found.")
                continue
            
            print(f"Found user: {user.email} (ID: {user.id})")
            
            # Find Employee
            emp = Employee.query.filter_by(user_id=user.id).first()
            if emp:
                print(f"  Found Employee profile (ID: {emp.id}). Deleting related data...")
                
                # Delete Attendance
                att_count = Attendance.query.filter_by(employee_id=emp.id).delete()
                print(f"    - Deleted {att_count} attendance records.")
                
                # Delete Addresses
                addr_count = EmployeeAddress.query.filter_by(employee_id=emp.id).delete()
                print(f"    - Deleted {addr_count} addresses.")
                
                # Delete Bank Details
                bank_count = EmployeeBankDetails.query.filter_by(employee_id=emp.id).delete()
                print(f"    - Deleted {bank_count} bank details.")
                
                # Delete Documents
                doc_count = EmployeeDocument.query.filter_by(employee_id=emp.id).delete()
                print(f"    - Deleted {doc_count} documents.")
                
                # Finally delete Employee
                db.session.delete(emp)
                print("  - Deleted Employee profile.")
            
            # Delete User
            db.session.delete(user)
            print("  - Deleted User record.")
            
        try:
            db.session.commit()
            print("✅ Successfully cleared data.")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error deleting data: {e}")