from app import app
from models import db
from models.user import User

with app.app_context():
    print("--- USERS ---")
    users = User.query.all()
    for u in users:
        print(f"ID: {u.id}, Email: {u.email}, Role: {u.role}, CoID: {u.company_id}")
