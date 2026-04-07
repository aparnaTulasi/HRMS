import sys
import os
sys.path.append(os.getcwd())
try:
    from app import app, db
    with app.app_context():
        from sqlalchemy import text
        # MySQL uses AUTO_INCREMENT, SQLite uses AUTOINCREMENT
        # Also using VARCHAR lengths for IDs
        sql = """
        CREATE TABLE IF NOT EXISTS support_tickets (
            id INT AUTO_INCREMENT PRIMARY KEY,
            ticket_id VARCHAR(50) NOT NULL UNIQUE,
            subject VARCHAR(255) NOT NULL,
            category VARCHAR(100) NOT NULL,
            priority VARCHAR(50) NOT NULL DEFAULT 'Medium',
            status VARCHAR(50) NOT NULL DEFAULT 'Open',
            description TEXT NOT NULL,
            attachment_url VARCHAR(255),
            company_id INT,
            created_by INT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
        """
        db.session.execute(text(sql))
        db.session.commit()
        print("SQL_EXEC_SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"ERROR: {str(e)}")
