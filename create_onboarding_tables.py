import sqlite3
import os

db_path = os.path.join(os.getcwd(), 'instance', 'hrms.db')

def create_letter_approval_tables():
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 1. onboarding_candidates
        print("Creating onboarding_candidates table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS onboarding_candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                candidate VARCHAR(150) NOT NULL,
                role VARCHAR(120),
                joining_date DATE,
                status VARCHAR(30) DEFAULT 'IN_PROGRESS',
                progress INTEGER DEFAULT 0,
                created_by INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. letter_templates
        print("Creating letter_templates table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS letter_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                letter_type VARCHAR(40) NOT NULL,
                title VARCHAR(120) NOT NULL,
                category VARCHAR(50),
                resource_url VARCHAR(255),
                blog_link VARCHAR(255),
                status VARCHAR(20) DEFAULT 'Active',
                usage_count INTEGER DEFAULT 0,
                body_html TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                version_no INTEGER DEFAULT 1,
                created_by INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 3. letter_requests
        print("Creating letter_requests table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS letter_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                employee_id INTEGER,
                candidate_id INTEGER,
                employee_name VARCHAR(150),
                employee_email VARCHAR(150),
                letter_date DATE,
                template_option VARCHAR(50) DEFAULT 'Standard Format',
                send_email_copy BOOLEAN DEFAULT 0,
                letter_type VARCHAR(40) NOT NULL,
                template_id INTEGER,
                status VARCHAR(30) DEFAULT 'DRAFT',
                payload TEXT, -- Store as JSON string
                pdf_path VARCHAR(255),
                current_version INTEGER DEFAULT 1,
                created_by INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (template_id) REFERENCES letter_templates (id)
            )
        """)

        # 4. letter_approval_workflows
        print("Creating letter_approval_workflows table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS letter_approval_workflows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                name VARCHAR(150) NOT NULL,
                letter_type VARCHAR(40) NOT NULL,
                status VARCHAR(20) DEFAULT 'Active',
                is_active BOOLEAN DEFAULT 1,
                created_by INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 5. letter_approval_workflow_levels
        print("Creating letter_approval_workflow_levels table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS letter_approval_workflow_levels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id INTEGER NOT NULL,
                step_no INTEGER NOT NULL,
                role VARCHAR(50) NOT NULL,
                user_id INTEGER,
                FOREIGN KEY (workflow_id) REFERENCES letter_approval_workflows (id)
            )
        """)

        # 6. letter_approval_steps (Tracks active request steps)
        print("Creating letter_approval_steps table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS letter_approval_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER NOT NULL,
                step_no INTEGER NOT NULL,
                approver_role VARCHAR(40) NOT NULL,
                status VARCHAR(20) DEFAULT 'PENDING',
                action_by INTEGER,
                action_at DATETIME,
                comments VARCHAR(255),
                FOREIGN KEY (request_id) REFERENCES letter_requests (id)
            )
        """)

        # 7. certificate_issues
        print("Creating certificate_issues table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS certificate_issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                recipient VARCHAR(150) NOT NULL,
                certificate_type VARCHAR(100) NOT NULL,
                issue_date DATE NOT NULL,
                recipient_email VARCHAR(150),
                template_option VARCHAR(50) DEFAULT 'Standard Format',
                send_email_copy BOOLEAN DEFAULT 0,
                employee_id INTEGER,
                payload TEXT,
                pdf_path VARCHAR(255),
                issued_by INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 8. letter_variables
        print("Creating letter_variables table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS letter_variables (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                name VARCHAR(50) NOT NULL,
                description VARCHAR(255),
                source VARCHAR(20) DEFAULT 'System',
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        print("All letter-related tables created successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")

    conn.commit()
    conn.close()
    print("Schema update complete.")

if __name__ == "__main__":
    create_letter_approval_tables()
