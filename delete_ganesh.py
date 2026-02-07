import sys
import os

# Add parent directory to path to find 'app' module if it's in the root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from app import create_app
except ImportError:
    # Fallback: if app.py defines 'app' directly instead of a factory
    from app import app as flask_app
    def create_app():
        return flask_app

from models import db
from models.user import User
from models.super_admin import SuperAdmin
from models.employee import Employee

# Initialize Flask App Context
app = create_app()

with app.app_context():
    target_email = "ganeshkoppartha591@gmail.com"
    
    # Find the user
    user = User.query.filter_by(email=target_email).first()
    
    if user:
        # Delete associated SuperAdmin profile if it exists
        sa = SuperAdmin.query.filter_by(user_id=user.id).first()
        if sa:
            db.session.delete(sa)
            print(f"Deleted SuperAdmin profile for {target_email}")

        # Delete associated Employee profile if it exists
        emp = Employee.query.filter_by(user_id=user.id).first()
        if emp:
            db.session.delete(emp)
            print(f"Deleted Employee profile for {target_email}")

        # Delete the User record
        db.session.delete(user)
        db.session.commit()
        print(f"Successfully deleted User: {target_email}")
    else:
        print(f"User {target_email} not found.")
