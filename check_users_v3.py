from app import app
from models.user import User

with app.app_context():
    print("--- USERS FOR COMPANY ID 3 ---")
    users = User.query.filter_by(company_id=3).all()
    for u in users:
        print(f"ID: {u.id} | Email: {u.email} | Role: {u.role}")
    
    if not users:
        print("No users found for Company ID 3.")
