from app import app, db
from models.super_admin import SuperAdmin
from models.user import User

with app.app_context():
    user = User.query.filter_by(email='dittakavijaya@gmail.com').first()
    if user:
        sa = SuperAdmin.query.filter_by(user_id=user.id).first()
        print(f"User ID: {user.id}, Role: {user.role}")
        print(f"SuperAdmin Record: {sa.id if sa else 'None'}")
    else:
        print("User not found")
