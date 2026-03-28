import sqlite3
import os
from datetime import datetime, timedelta

db_path = os.path.join(os.getcwd(), 'instance', 'hrms.db')

def seed_loans():
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get sample employees
    cursor.execute("SELECT id, full_name FROM employees LIMIT 5")
    employees = cursor.fetchall()
    if not employees:
        print("No employees found to seed loans.")
        return

    # Sample Data from UI
    # Rajesh Kumar (#101), ₹50,000, Personal, Active, EMI ₹5,000
    # Sneha Patel (#102), ₹2,00,000, Home Renovation, Approved, EMI ₹10,000
    # Amit Singh (#103), ₹20,000, Emergency, Paid, EMI ₹4,000
    # Priya Sharma (#104), ₹1,00,000, Personal, Pending, EMI ₹8,500

    loan_samples = [
        ("Personal", 50000.0, 8.5, 12, 5000.0, "Active", datetime.now() - timedelta(days=60)),
        ("Home Renovation", 200000.0, 8.5, 24, 10000.0, "Approved", datetime.now() - timedelta(days=30)),
        ("Emergency", 20000.0, 8.5, 6, 4000.0, "Paid", datetime.now() - timedelta(days=90)),
        ("Personal", 100000.0, 8.5, 15, 8500.0, "Pending", None)
    ]

    print("Seeding loans...")
    for i, (ltype, amt, rate, tenure, emi, status, d_date) in enumerate(loan_samples):
        emp_id = employees[i % len(employees)][0]
        cursor.execute("""
            INSERT INTO loans (company_id, employee_id, loan_type, amount, interest_rate, tenure_months, emi, status, disbursement_date, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (1, emp_id, ltype, amt, rate, tenure, emi, status, d_date.date().isoformat() if d_date else None, datetime.now().isoformat()))

    conn.commit()
    conn.close()
    print("Seeding complete.")

if __name__ == "__main__":
    seed_loans()
