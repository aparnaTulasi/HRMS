from app import app, db
from sqlalchemy import inspect

def check_columns():
    with app.app_context():
        inspector = inspect(db.engine)
        columns = inspector.get_columns('attendance_logs')
        for column in columns:
            print(f"Column: {column['name']}, Type: {column['type']}")

if __name__ == "__main__":
    check_columns()
