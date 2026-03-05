import os
import sys

# Add the project directory to sys.path
current_dir = os.getcwd()
sys.path.append(current_dir)

from app import app
from models import db
from models.company import Company
from models.branch import Branch

with app.app_context():
    companies = Company.query.all()
    branches = Branch.query.all()
    
    print(f"Total Companies: {len(companies)}")
    print(f"Total Branches: {len(branches)}")
    
    for c in companies:
        branch_count = len(c.branches)
        print(f"Company: {c.company_name} (ID: {c.id}) - Branches: {branch_count}")
        if branch_count == 0:
            print(f"  WARNING: Company {c.company_name} has NO branches!")
