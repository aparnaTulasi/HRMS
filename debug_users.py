import os
import sys

current_dir = os.getcwd()
sys.path.append(current_dir)

from app import app
from models.user import User

with app.app_context():
    users = User.query.all()
    print(f"DEBUG: Found {len(users)} users in DB")
    company_ids = set()
    for u in users:
        if u.company_id:
            company_ids.add(u.company_id)
    print(f"DEBUG: Distinct company IDs in User table: {list(company_ids)}")
