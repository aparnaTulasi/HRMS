import sys
import os
from datetime import datetime, date

# Add the project root to the python path
sys.path.append(os.getcwd())

from app import app
from models import db
from models.employee import Employee
from models.payroll import PaySlip, PayslipEarning, PayslipDeduction

def seed_payslips():
    with app.app_context():
        count = PaySlip.query.count()
        print(f"Current payslips count: {count}")
        
        if count > 0:
            print("Payslips already exist. Skipping seeding.")
            return

        employees = Employee.query.limit(5).all()
        if not employees:
            print("No employees found to seed payslips.")
            return

        # Target Month: February 2026
        month, year = 2, 2026
        
        for emp in employees:
            ps = PaySlip(
                company_id=emp.company_id,
                employee_id=emp.id,
                pay_month=month,
                pay_year=year,
                pay_date=date(2026, 2, 28),
                total_days=28,
                paid_days=28,
                lwp_days=0,
                annual_ctc=emp.ctc or 600000,
                monthly_ctc=(emp.ctc or 600000) / 12.0,
                status="FINAL",
                created_by=1
            )
            
            # Simple earnings
            basic = ps.monthly_ctc * 0.4
            hra = ps.monthly_ctc * 0.2
            allowance = ps.monthly_ctc * 0.3
            
            ps.earnings.append(PayslipEarning(component="Basic", amount=basic))
            ps.earnings.append(PayslipEarning(component="HRA", amount=hra))
            ps.earnings.append(PayslipEarning(component="Special Allowance", amount=allowance))
            
            ps.gross_salary = basic + hra + allowance
            
            # Simple deductions
            pf = 1800
            pt = 200
            ps.deductions.append(PayslipDeduction(component="Provident Fund", amount=pf))
            ps.deductions.append(PayslipDeduction(component="Professional Tax", amount=pt))
            
            ps.total_deductions = pf + pt
            ps.net_salary = ps.gross_salary - ps.total_deductions
            
            db.session.add(ps)
            print(f"Created Feb 2026 payslip for {emp.full_name}")

        db.session.commit()
        print("Success: Payslip seeding complete.")

if __name__ == "__main__":
    seed_payslips()
