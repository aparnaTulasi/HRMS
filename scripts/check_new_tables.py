from models import db
from app import app
from sqlalchemy import inspect

with app.app_context():
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print("Tables in DB:", tables)
    
    needed = ['visitor_requests', 'desks', 'desk_bookings']
    for t in needed:
        if t in tables:
            print(f"✅ Table '{t}' exists.")
        else:
            print(f"❌ Table '{t}' MISSING!")
