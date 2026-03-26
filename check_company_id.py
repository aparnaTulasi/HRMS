from app import app
from models.user import User
from models.loan import Loan
from models import db

with app.app_context():
    for uid in [2, 6, 7]:
        u = User.query.get(uid)
        if u:
            print(f"User {uid} (Role {u.role}) Company: {u.company_id}")
    
    total_loans = Loan.query.count()
    print(f"Total Loans in DB: {total_loans}")
    
    if total_loans > 0:
        l = Loan.query.first()
        print(f"First Loan Company ID: {l.company_id}")
