import sqlite3
import os

# Calculate path to the database file
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(BASE_DIR, "instance", "hrms.db")

def create_tables():
    print("🚀 Creating Request & Notification Tables...")
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Database file not found at: {DB_PATH}")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 1. Profile Change Requests Table
        print("🛠️  Creating table: profile_change_requests")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS profile_change_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            requester_user_id INTEGER NOT NULL,
            target_user_id INTEGER NOT NULL,
            status VARCHAR(20) DEFAULT 'PENDING',
            flow_type VARCHAR(50) NOT NULL,
            approver_role VARCHAR(50) NOT NULL,
            approver_user_id INTEGER,
            reason TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            decided_at DATETIME,
            applied_at DATETIME,
            FOREIGN KEY(requester_user_id) REFERENCES users(id),
            FOREIGN KEY(target_user_id) REFERENCES users(id),
            FOREIGN KEY(approver_user_id) REFERENCES users(id)
        )
        """)

        # 2. Profile Change Request Items Table
        print("🛠️  Creating table: profile_change_request_items")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS profile_change_request_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL,
            field_key VARCHAR(100) NOT NULL,
            old_value TEXT,
            new_value TEXT,
            FOREIGN KEY(request_id) REFERENCES profile_change_requests(id) ON DELETE CASCADE
        )
        """)

        # 3. Profile Change Approvals Table
        print("🛠️  Creating table: profile_change_approvals")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS profile_change_approvals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL,
            approver_user_id INTEGER NOT NULL,
            action VARCHAR(20) NOT NULL,
            comment TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(request_id) REFERENCES profile_change_requests(id),
            FOREIGN KEY(approver_user_id) REFERENCES users(id)
        )
        """)

        conn.commit()
        conn.close()
        print("\n✨ All tables created successfully!")
        
    except Exception as e:
        print(f"\n❌ Error creating tables: {e}")

if __name__ == "__main__":
    create_tables()