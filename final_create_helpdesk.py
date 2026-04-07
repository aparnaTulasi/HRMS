import sys
import os
sys.path.append(os.getcwd())
try:
    from app import app, db
    # We must import the model for db.create_all() to detect it
    from models.support_ticket import SupportTicket
    with app.app_context():
        # Force create the table using the model metadata
        SupportTicket.__table__.create(db.engine, checkfirst=True)
        print("TABLE_CREATED_SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"ERROR: {str(e)}")
