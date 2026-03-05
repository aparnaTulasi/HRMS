import sqlite3
import os

db_path = os.path.join('instance', 'hrms.db')

def fix_payslips():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get existing columns
    cursor.execute("PRAGMA table_info(payslips)")
    columns = [col[1] for col in cursor.fetchall()]
    print(f"Current columns in payslips: {columns}")
    
    needed_columns = [
        ('annual_ctc', 'FLOAT DEFAULT 0'),
        ('monthly_ctc', 'FLOAT DEFAULT 0'),
        ('tax_regime', 'VARCHAR(30) DEFAULT "OLD"'),
        ('section_80c', 'FLOAT DEFAULT 0'),
        ('monthly_rent', 'FLOAT DEFAULT 0'),
        ('city_type', 'VARCHAR(30) DEFAULT "NON_METRO"'),
        ('other_deductions', 'FLOAT DEFAULT 0'),
        ('calculated_tds', 'FLOAT DEFAULT 0'),
        ('bank_account_no', 'VARCHAR(50)'),
        ('uan_no', 'VARCHAR(50)'),
        ('esi_account_no', 'VARCHAR(50)'),
        ('pf_employee_pct', 'FLOAT DEFAULT 12'),
        ('pf_employer_pct', 'FLOAT DEFAULT 12'),
        ('esi_employee_pct', 'FLOAT DEFAULT 0.75'),
        ('esi_employer_pct', 'FLOAT DEFAULT 3.25'),
        ('pdf_path', 'VARCHAR(255)'),
        ('is_deleted', 'BOOLEAN DEFAULT 0'),
        ('created_by', 'INTEGER'),
        ('created_at', 'DATETIME'),
        ('updated_at', 'DATETIME')
    ]
    
    for col_name, col_type in needed_columns:
        if col_name not in columns:
            print(f"Adding column {col_name} to payslips...")
            try:
                cursor.execute(f"ALTER TABLE payslips ADD COLUMN {col_name} {col_type}")
            except Exception as e:
                print(f"Error adding {col_name}: {e}")
    
    conn.commit()
    conn.close()
    print("Database fix complete.")

if __name__ == "__main__":
    fix_payslips()
