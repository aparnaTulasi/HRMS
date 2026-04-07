import sys
import os
sys.path.append(os.getcwd())
from models import db
from models.support_ticket import SupportTicket
from app import app
with app.app_context():
    db.create_all()
    print("TABLES_CREATED")
