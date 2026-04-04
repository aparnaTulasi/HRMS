from app import app, db
from sqlalchemy import inspect

def inspect_schema():
    with app.app_context():
        inspector = inspect(db.engine)
        
        # Inspection of employees
        print("\n--- Employees Table ---")
        cols = inspector.get_columns('employees')
        for col in cols:
            print(f"  {col['name']}: {col['type']}")
            
        # Inspection of user_permissions
        print("\n--- UserPermissions Table ---")
        cols = inspector.get_columns('user_permissions')
        for col in cols:
            print(f"  {col['name']}: {col['type']}")

if __name__ == "__main__":
    inspect_schema()
