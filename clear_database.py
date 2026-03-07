import sys
import os
from app import app, db
from sqlalchemy import text

def clear_data():
    with app.app_context():
        print("⚠️  Warning: This will delete ALL data from the database.")
        confirm = input("Are you sure? (y/n): ")
        if confirm.lower() != 'y':
            print("Aborted.")
            return

        try:
            # Disable foreign key checks to allow truncation
            db.session.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
            
            # Get all table names
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            for table in tables:
                if table == 'alembic_version': # Don't clear migration history
                    continue
                print(f"Clearing table: {table}")
                db.session.execute(text(f"TRUNCATE TABLE {table};"))
            
            # Re-enable foreign key checks
            db.session.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
            db.session.commit()
            print("✅ Database cleared successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error clearing database: {str(e)}")

if __name__ == "__main__":
    clear_data()
