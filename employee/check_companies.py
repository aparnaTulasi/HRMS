import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from models.master import Company

if __name__ == "__main__":
    with app.app_context():
        companies = Company.query.all()
        if not companies:
            print("⚠️ No companies found in the database.")
            print("👉 Run 'python seed_hrms.py' to populate the database.")
        else:
            print(f"✅ Found {len(companies)} companies:")
            print("-" * 50)
            print(f"{'ID':<5} | {'Subdomain':<15} | {'Name'}")
            print("-" * 50)
            for c in companies:
                print(f"{c.id:<5} | {c.subdomain:<15} | {c.company_name}")
            print("-" * 50)