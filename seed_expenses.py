import sqlite3
import os
from datetime import datetime, date, timedelta

db_path = os.path.join(os.getcwd(), 'instance', 'hrms.db')

def seed_expenses():
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get sample employees
    cursor.execute("SELECT id, full_name FROM employees LIMIT 5")
    employees = cursor.fetchall()
    if not employees:
        print("No employees found to seed expenses.")
        return

    # Sample Data from UI
    # John Doe (EXP-001), Flight - Client Visit NYC, Oct 10, 2023, $1,200, Approved
    # Sarah Lee (EXP-002), Hotel - Tech Conference, Oct 12, 2023, $850, Pending
    # Mike Chen (EXP-003), Meals - Team Dinner, Oct 15, 2023, $300, Rejected
    # Meera Joshi (EXP-004), Taxi - Branch Audit, Oct 18, 2023, $150, Approved

    expense_samples = [
        ("Client Visit NYC", "Flight", 1200.0, date(2023, 10, 10), "Approved"),
        ("Tech Conference", "Hotel", 850.0, date(2023, 10, 12), "Pending"),
        ("Team Dinner", "Meals", 300.0, date(2023, 10, 15), "Rejected"),
        ("Branch Audit", "Taxi", 150.0, date(2023, 10, 18), "Approved")
    ]

    print("Seeding expenses...")
    for i, (purpose, cat, amt, e_date, status) in enumerate(expense_samples):
        emp_id, emp_name = employees[i % len(employees)]
        now = datetime.now()
        cursor.execute("""
            INSERT INTO expense_claims (
                company_id, employee_id, project_purpose, category, amount, currency, 
                expense_date, status, year, month, day, time, added_by_name, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (1, emp_id, purpose, cat, amt, "$", 
              e_date.isoformat(), status, e_date.year, e_date.month, e_date.day, 
              now.strftime("%H:%M:%S"), emp_name, datetime.now().isoformat()))

    conn.commit()
    conn.close()
    print("Seeding complete.")

if __name__ == "__main__":
    seed_expenses()
