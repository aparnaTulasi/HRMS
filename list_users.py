
from app import app
from models.user import User

with app.app_context():
    users = User.query.filter(User.role.in_(['HR', 'ADMIN', 'SUPER_ADMIN'])).all()
    for u in users:
        print(f"Role: {u.role}, Email: {u.email}")
