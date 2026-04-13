from app import app, db
from models.company import Company
from models.employee import Employee
from models.user import User

def diagnose_visibility():
    with app.app_context():
        print("=== Company Visibility Check ===")
        companies = Company.query.all()
        print(f"Total Companies: {len(companies)}")
        for c in companies:
            # Check if status column exists and its value
            status = getattr(c, 'status', 'N/A')
            print(f"ID: {c.id}, Name: {c.company_name}, Status: {status}")

        print("\n=== Employee Visibility Check ===")
        # Check active counts
        active_count = Employee.query.filter_by(is_active=True).count()
        inactive_count = Employee.query.filter_by(is_active=False).count()
        none_count = Employee.query.filter(Employee.is_active == None).count()
        
        print(f"Total Employees: {Employee.query.count()}")
        print(f"  Active (True): {active_count}")
        print(f"  Inactive (False): {inactive_count}")
        print(f"  Null: {none_count}")
        
        if Employee.query.count() > 0:
            print("\nSample Employees with Status:")
            emps = Employee.query.limit(10).all()
            for e in emps:
                user = User.query.get(e.user_id) if e.user_id else None
                u_status = user.status if user else "No User"
                print(f"ID: {e.id}, Name: {e.full_name}, is_active: {e.is_active}, User Status: {u_status}")

if __name__ == "__main__":
    diagnose_visibility()
