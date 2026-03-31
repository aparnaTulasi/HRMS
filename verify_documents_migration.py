from app import app
from models import db
from sqlalchemy import inspect

def verify_migration():
    with app.app_context():
        inspector = inspect(db.engine)
        hr_cols = [c['name'] for c in inspector.get_columns('hr_documents')]
        emp_cols = [c['name'] for c in inspector.get_columns('employee_documents')]
        
        expected_hr = ['is_active', 'status', 'is_sensitive', 'last_viewed_at', 'view_count']
        expected_emp = ['is_active', 'status', 'last_viewed_at', 'view_count']
        
        print("HRDocument Columns:", hr_cols)
        print("EmployeeDocument Columns:", emp_cols)
        
        for col in expected_hr:
            assert col in hr_cols, f"Missing {col} in hr_documents"
        
        for col in expected_emp:
            assert col in emp_cols, f"Missing {col} in employee_documents"
            
        print("Verification SUCCESSful!")

if __name__ == "__main__":
    verify_migration()
