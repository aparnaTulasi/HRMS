import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

def migrate():
    # Database connection parameters (extracted from existing scripts)
    db_config = {
        'host': 'localhost',
        'user': 'root',
        'password': '',
        'database': 'hrms_db',
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor
    }

    connection = pymysql.connect(**db_config)
    try:
        with connection.cursor() as cursor:
            print("Starting migration for subscription and feature columns...")

            # 1. Update Companies table
            try:
                # Add Subscription columns
                cursor.execute("ALTER TABLE companies ADD COLUMN start_date DATETIME DEFAULT CURRENT_TIMESTAMP")
                cursor.execute("ALTER TABLE companies ADD COLUMN end_date DATETIME NULL")
                cursor.execute("ALTER TABLE companies ADD COLUMN max_users INT DEFAULT 10")
                
                # Add Feature toggles
                cursor.execute("ALTER TABLE companies ADD COLUMN has_attendance TINYINT(1) DEFAULT 1")
                cursor.execute("ALTER TABLE companies ADD COLUMN has_leave TINYINT(1) DEFAULT 1")
                cursor.execute("ALTER TABLE companies ADD COLUMN has_payroll TINYINT(1) DEFAULT 1")
                cursor.execute("ALTER TABLE companies ADD COLUMN has_performance TINYINT(1) DEFAULT 1")
                cursor.execute("ALTER TABLE companies ADD COLUMN kyc_status VARCHAR(20) DEFAULT 'PENDING'")
                
                print("Added subscription and feature columns to companies table.")
            except Exception as e:
                print(f"Error updating companies table: {e}")

            # 2. Create system_settings table
            try:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS system_settings (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        setting_key VARCHAR(50) UNIQUE NOT NULL,
                        setting_value VARCHAR(255) NOT NULL,
                        description VARCHAR(255),
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    )
                """)
                print("Created system_settings table.")
                
                # 3. Seed default system settings
                default_settings = [
                    ('TIMEZONE', 'UTC', 'Global System Timezone'),
                    ('CURRENCY', 'INR', 'Default Currency Symbol'),
                    ('DATE_FORMAT', 'YYYY-MM-DD', 'System-wide Date Format'),
                    ('LANGUAGE', 'English', 'Default System Language')
                ]
                for key, val, desc in default_settings:
                    try:
                        cursor.execute("INSERT IGNORE INTO system_settings (setting_key, setting_value, description) VALUES (%s, %s, %s)", (key, val, desc))
                    except Exception as e:
                        print(f"Error seeding setting {key}: {e}")
                
            except Exception as e:
                print(f"Error creating system_settings table: {e}")

            connection.commit()
            print("Migration completed successfully!")

    finally:
        connection.close()

if __name__ == "__main__":
    migrate()
