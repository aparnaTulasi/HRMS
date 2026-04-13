from app import app, db
from models.user import User
from models.company import Company

def check_users():
    with app.app_context():
        print("=== User List ===")
        users = User.query.all()
        for u in users:
            print(f"Email: {u.email}, Role: {u.role}, Company ID: {u.company_id}")
            
        print("\n=== Valid Company IDs ===")
        companies = Company.query.all()
        valid_ids = [c.id for c in companies]
        print(f"IDs: {valid_ids}")

if __name__ == "__main__":
    check_users()
