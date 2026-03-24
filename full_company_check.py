from app import app
from models import db
from models.company import Company

with app.app_context():
    companies = Company.query.all()
    print(f"Total Companies in DB: {len(companies)}")
    for c in companies:
        print(f" - ID: {c.id}, Name: {c.company_name}, Status: {c.status}")
