from app import app
from sqlalchemy import inspect
from models import db

with app.app_context():
    inspector = inspect(db.engine)
    print("Tables in database:")
    for table_name in inspector.get_table_names():
        print(f"- {table_name}")
