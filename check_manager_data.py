from app import app, db
from models.employee import Employee
from models.user import User

def check():
    with app.app_context():
        # Find a manager with subordinates
        managers = Employee.query.join(User, Employee.user_id == User.id).filter(User.role=='MANAGER').all()
        for m in managers:
            subs = Employee.query.filter_by(manager_id=m.id).all()
            if subs:
                print(f"MANAGER_ID={m.id}")
                print(f"MANAGER_USER_ID={m.user_id}")
                print(f"MANAGER_NAME={m.full_name}")
                print(f"SUBORDINATE_IDS={[s.id for s in subs]}")
                print(f"SUBORDINATE_USER_IDS={[s.user_id for s in subs]}")
                return
        print("No manager with subordinates found.")

if __name__ == "__main__":
    check()
