from app import app
from models import db
from sqlalchemy import text, inspect

def migrate_documents():
    with app.app_context():
        inspector = inspect(db.engine)
        
        # 1. Update hr_documents
        print("Migrating hr_documents...")
        hr_cols = [c['name'] for c in inspector.get_columns('hr_documents')]
        new_hr_cols = [
            ('is_active', 'BOOLEAN DEFAULT 1'),
            ('status', 'VARCHAR(20) DEFAULT "Active"'),
            ('is_sensitive', 'BOOLEAN DEFAULT 0'),
            ('last_viewed_at', 'DATETIME'),
            ('view_count', 'INT DEFAULT 0')
        ]
        for col_name, col_def in new_hr_cols:
            if col_name not in hr_cols:
                print(f"Adding {col_name} to hr_documents...")
                db.session.execute(text(f"ALTER TABLE hr_documents ADD COLUMN {col_name} {col_def}"))
        
        # 2. Update employee_documents
        print("Migrating employee_documents...")
        emp_cols = [c['name'] for c in inspector.get_columns('employee_documents')]
        new_emp_cols = [
            ('is_active', 'BOOLEAN DEFAULT 1'),
            ('status', 'VARCHAR(20) DEFAULT "Active"'),
            ('last_viewed_at', 'DATETIME'),
            ('view_count', 'INT DEFAULT 0')
        ]
        for col_name, col_def in new_emp_cols:
            if col_name not in emp_cols:
                print(f"Adding {col_name} to employee_documents...")
                db.session.execute(text(f"ALTER TABLE employee_documents ADD COLUMN {col_name} {col_def}"))
        
        db.session.commit()
        print("Document migration completed successfully!")

if __name__ == "__main__":
    migrate_documents()
