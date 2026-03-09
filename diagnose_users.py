from app import app, db
from models.user import User

with app.app_context():
    users = User.query.all()
    print(f"{'ID':<4} {'Email':<40} {'Role':<12} {'Status':<10}")
    print("-" * 70)
    for u in users:
        print(f"{u.id:<4} {u.email:<40} {u.role:<12} {u.status:<10}")
