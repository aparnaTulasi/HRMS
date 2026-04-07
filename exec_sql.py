import sys
import os
sys.path.append(os.getcwd())
try:
    from app import app, db
    with app.app_context():
        from sqlalchemy import text
        sql = """
        CREATE TABLE IF NOT EXISTS support_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id VARCHAR(50) NOT NULL UNIQUE,
            subject VARCHAR(255) NOT NULL,
            category VARCHAR(100) NOT NULL,
            priority VARCHAR(50) NOT NULL DEFAULT 'Medium',
            status VARCHAR(50) NOT NULL DEFAULT 'Open',
            description TEXT NOT NULL,
            attachment_url VARCHAR(255),
            company_id INTEGER,
            created_by INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
        db.session.execute(text(sql))
        db.session.commit()
        print("SQL_EXEC_SUCCESS")
except Exception as e:
    print(f"ERROR: {str(e)}")
