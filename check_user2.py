from app import app
from models import db
from models.user import User

with app.app_context():
    u = User.query.get(2)
    if u:
        print(f"User 2 - Email: {u.email}, Role: '{u.role}', CoID: {u.company_id}")
    else:
        print("User 2 NOT FOUND in DB.")
