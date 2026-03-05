import os
import sys

current_dir = os.getcwd()
sys.path.append(current_dir)

from app import app
from models.branch import Branch
from models.company import Company

with app.app_context():
    branches = Branch.query.all()
    print(f"DEBUG: Found {len(branches)} branches in DB")
    for b in branches:
        c = Company.query.get(b.company_id)
        c_name = c.company_name if c else "UNKNOWN"
        print(f"ID: {b.id} | Name: {b.branch_name} | Company: {c_name} | Status: {b.status} | Lat: {b.latitude} | Lng: {b.longitude}")
