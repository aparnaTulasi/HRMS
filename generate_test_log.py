
from app import app
from models import db
from utils.audit_logger import log_action
from flask import g

with app.app_context():
    # Mock a user in g for the logger
    from models.user import User
    user = User.query.filter_by(role='HR').first()
    if user:
        g.user = user
        log_action("TEST_ACTION", "AuditTest", 999, 200, meta={"msg": "Manual test log"})
        print(f"Logged action for user: {user.email}")
    else:
        print("No HR user found to mock")
