from app import app, db
from models.user import User
from models.employee import Employee
from models.company import Company

with app.app_context():
    hr = User.query.filter_by(role='HR').first()
    if hr:
        print(f"HR User: {hr.email}")
        print(f"Company ID: {hr.company_id}")
        comp = Company.query.get(hr.company_id)
        print(f"Company Name: {comp.company_name if comp else 'N/A'}")
    else:
        print("No HR user found.")
