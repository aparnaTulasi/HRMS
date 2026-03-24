from app import app
from models.user import User

with app.app_context():
    users = User.query.all()
    print(f"{'ID':<5} {'EMAIL':<30} {'ROLE':<15} {'COMPANY_ID':<10}")
    print("-" * 65)
    for u in users:
        uid = str(getattr(u, 'id', 'N/A'))
        email = str(u.email or 'N/A')
        role = str(getattr(u, 'role', 'N/A'))
        cid = str(getattr(u, 'company_id', 'N/A'))
        print(f"{uid:<5} {email:<30} {role:<15} {cid:<10}")
