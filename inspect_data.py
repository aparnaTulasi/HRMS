from app import app, db
from models.payroll import PaySlip

with app.app_context():
    print("--- PAYSLIP INSPECTION (IDS 15, 27) ---")
    results = PaySlip.query.filter(PaySlip.employee_id.in_([15, 27])).all()
    if not results:
        print("No payslips found for these IDs.")
    for r in results:
        print(f"Emp: {r.employee_id}, Month: {r.pay_month}, Year: {r.pay_year}, Salary: {r.net_salary}, Status: {r.status}, Company: {r.company_id}")
    
    print("\n--- COMPANY ID CHECK ---")
    from models.employee import Employee
    m = Employee.query.get(15)
    s = Employee.query.get(27)
    print(f"Manager Emp 15 Company: {m.company_id if m else 'N/A'}")
    print(f"Sub Emp 27 Company: {s.company_id if s else 'N/A'}")
