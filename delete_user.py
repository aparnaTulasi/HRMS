from app import app
from models import db
from models.user import User
from models.super_admin import SuperAdmin
from models.employee import Employee

email_to_delete = "seelamaparnatulasi@gmail.com"

with app.app_context():
    try:
        # Find the user
        user = User.query.filter_by(email=email_to_delete).first()
        sa = SuperAdmin.query.filter_by(email=email_to_delete).first()
        
        # Also check for Employee record linked to this user
        emp = None
        if user:
            emp = Employee.query.filter_by(user_id=user.id).first()

        if sa:
            db.session.delete(sa)
            print(f"✅ Deleted SuperAdmin record for {email_to_delete}")
        
        if emp:
            db.session.delete(emp)
            print(f"✅ Deleted Employee record for {email_to_delete}")

        if user:
            db.session.delete(user)
            print(f"✅ Deleted User record for {email_to_delete}")
            
        if not sa and not user:
            print(f"ℹ️ No records found for {email_to_delete}")
        else:
            db.session.commit()
            print("🚀 Changes committed to database.")
            
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error deleting user: {e}")
