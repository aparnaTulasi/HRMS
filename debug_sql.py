from app import app, db
from models.employee import Employee
from models.user import User

def debug_insert():
    with app.app_context():
        try:
            # Try to create a dummy user first
            u = User(email='debug@test.com', password='password', role='EMPLOYEE')
            db.session.add(u)
            db.session.flush()
            
            # Try to create employee
            e = Employee(
                user_id=u.id,
                company_id=1,
                employee_id='DEBUG-001',
                full_name='Debug User',
                status='ACTIVE',
                is_active=True
            )
            db.session.add(e)
            db.session.commit()
            print("Successfully inserted employee!")
        except Exception as e:
            print(f"FAILED: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    debug_insert()
