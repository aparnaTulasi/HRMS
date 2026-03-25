from app import app
from models import db
from models.user import User

with app.app_context():
    # User ID 6 (ADMIN), 7 (HR), 8 (MANAGER)
    for uid in [6, 7, 8]:
        u = User.query.get(uid)
        if u:
            print(f"Reassigning User {u.id} ({u.role}) from CID {u.company_id} to 3")
            u.company_id = 3
    
    db.session.commit()
    print("Update complete.")
