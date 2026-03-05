import os
import sys

current_dir = os.getcwd()
sys.path.append(current_dir)

from app import app
from models.company import Company

with app.app_context():
    companies = Company.query.all()
    print(f"DEBUG: Found {len(companies)} companies in DB")
    for c in companies:
        print(f"ID: {c.id} | Name: {c.company_name} | City: {c.city_branch} | Address: {c.address} | State: {c.state}")
