from app import app
from models import db
from models.branch import Branch

with app.app_context():
    # Update Branch 2 (jayadittakavi) to Kakinada
    b2 = Branch.query.filter(Branch.branch_name.like('%kakinada%'), Branch.company_id == 2).first()
    if b2:
        b2.latitude = 16.9891
        b2.longitude = 82.2475
        print(f"Updated Branch {b2.id} (jayadittakavi) to Kakinada")

    # Update Branch 3 (Futureinvo) to a slightly different Kakinada spot
    b3 = Branch.query.filter(Branch.branch_name.like('%kakinada%'), Branch.company_id == 3).first()
    if b3:
        b3.latitude = 16.9950
        b3.longitude = 82.2500
        print(f"Updated Branch {b3.id} (Futureinvo) to Kakinada (Offset)")

    db.session.commit()
    print("Database coordinates updated.")
