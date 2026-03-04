from app import app
from models import db
from models.user import User
from models.employee import Employee

if __name__ == "__main__":
    with app.app_context():
        print("🧹 Clearing Super Admin data...")
        try:
            super_admins = User.query.filter_by(role='SUPER_ADMIN').all()
            for user in super_admins:
                Employee.query.filter_by(user_id=user.id).delete()
                db.session.delete(user)
            db.session.commit()
            print(f"✅ Cleared {len(super_admins)} Super Admin(s).")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error: {e}")