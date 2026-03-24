from app import app
from models import db
from models.user import User

with app.app_context():
    roles = db.session.query(User.role).distinct().all()
    print("Distinct Roles in Database:")
    for r in roles:
        print(f" - '{r[0]}'")
    
    users = User.query.filter(User.role.like('%ADMIN%')).all()
    print("\nUsers with 'ADMIN' in role:")
    for u in users:
        print(f" - ID: {u.id}, Email: {u.email}, Role: '{u.role}', CoID: {u.company_id}")
