from app import app
from models.user import User

with app.app_context():
    roles = [u.role for u in User.query.all()]
    print(f"Unique Roles in DB: {set(roles)}")
