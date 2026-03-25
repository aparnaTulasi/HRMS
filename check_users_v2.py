from app import app
from models.user import User

with app.app_context():
    with open('user_diag_v2.txt', 'w') as f:
        f.write("--- FULL USER LIST ---\n")
        users = User.query.all()
        for u in users:
            f.write(f"ID: {u.id} | Email: {u.email} | Role: {u.role} | CoID: {u.company_id}\n")
