from app import app
from models.master import db, UserMaster

with app.app_context():
    target_email = "adminaparna@gmail.com"
    user = UserMaster.query.filter_by(email=target_email).first()
    
    if user:
        if not user.is_active:
            user.is_active = True
            db.session.commit()
            print(f"✅ Account reactivated: {target_email}")
        else:
            print(f"ℹ️  Account is already active: {target_email}")
    else:
        print(f"❌ User not found: {target_email}")