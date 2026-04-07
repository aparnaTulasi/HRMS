import sys
import os
sys.path.append(os.getcwd())
try:
    from app import app, db
    with app.app_context():
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"RESULT_TABLES: {tables}")
except Exception as e:
    print(f"ERROR: {str(e)}")
