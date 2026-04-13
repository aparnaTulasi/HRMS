from app import app, db
from flask import g
from models.user import User
from models.employee import Employee
from models.company import Company
from sqlalchemy import text

def inspect_sql():
    with app.app_context():
        user = User.query.filter_by(role='SUPER_ADMIN').first()
        if not user:
            print("No Super Admin found")
            return
            
        g.user = user
        
        # Check Employees query
        from routes.admin import get_employees
        query = Employee.query
        # Apply filters like in get_employees
        query = query.filter(Employee.is_active == True)
        print("=== Employee SQL ===")
        print(query.statement.compile(compile_kwargs={"literal_binds": True}))
        print(f"Count from this query: {query.count()}")
        
        # Check Companies query
        print("\n=== Company SQL ===")
        query_c = Company.query.order_by(Company.id.desc())
        print(query_c.statement.compile(compile_kwargs={"literal_binds": True}))
        print(f"Count from this query: {query_c.count()}")
        
        # Check raw count
        print("\n=== Raw DB Counts (Direct Text) ===")
        c_count = db.session.execute(text("SELECT COUNT(*) FROM companies")).scalar()
        e_count = db.session.execute(text("SELECT COUNT(*) FROM employees")).scalar()
        print(f"Raw Companies: {c_count}")
        print(f"Raw Employees: {e_count}")

if __name__ == "__main__":
    inspect_sql()
