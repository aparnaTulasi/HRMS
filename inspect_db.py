from app import app
from models import db
from models.user import User
from models.branch import Branch
from models.company import Company

with app.app_context():
    with open("db_inspect_output.txt", "w", encoding="utf-8") as f:
        f.write("--- USERS ---\n")
        users = User.query.all()
        for u in users:
            f.write(f"ID: {u.id} | Email: {u.email} | Role: {u.role} | CoID: {u.company_id}\n")
        
        f.write("\n--- COMPANIES & BRANCHES ---\n")
        companies = Company.query.all()
        for c in companies:
            branch_count = Branch.query.filter_by(company_id=c.id).count()
            f.write(f"Company: {c.company_name} (ID: {c.id}) | Branches: {branch_count}\n")
            branches = Branch.query.filter_by(company_id=c.id).all()
            for b in branches:
                f.write(f"  - Branch: {b.branch_name} | Lat: {b.latitude} | Lng: {b.longitude}\n")

        f.write("\n--- ALL BRANCHES ---\n")
        all_branches = Branch.query.all()
        f.write(f"Total Branches in DB: {len(all_branches)}\n")
