import sys
import os

# Add the project root to sys.path
sys.path.append(r'c:\Users\nagas\OneDrive\Desktop\HRMS-main\HRMS-main')

from app import app, db
from models.employee_statutory import Form16
from models.employee import Employee

with app.app_context():
    # Make sure tables are created
    db.create_all()
    
    emp = Employee.query.first()
    if emp:
        record = Form16.query.filter_by(employee_id=emp.id, fy="2024-2025").first()
        if not record:
            record = Form16(
                employee_id=emp.id,
                company_id=emp.company_id,
                fy="2024-2025",
                ay="2025-2026",
                pan=emp.pan or "ABCDE1234F",
                tan="BLRK01234A",
                employer_pan="AAACF1234Z",
                part_a={
                    "grossSalary": 768000,
                    "tdsQ1": 14820, "tdsQ2": 14820, "tdsQ3": 14820, "tdsQ4": 14820,
                    "totalTDS": 59280
                },
                part_b={
                    "basicSalary": 480000, "hra": 192000, "specialAllowance": 96000,
                    "grossSalary": 768000, "hra_exempt": 112000, "ltaExempt": 15000,
                    "totalExemption": 127000, "netSalary": 641000, "pfDeduction": 57600,
                    "npsDeduction": 0, "otherDeduction": 0, "total80C": 57600,
                    "total80D": 25000, "total80CCD": 0, "totalVIDeductions": 82600,
                    "grossTotalIncome": 641000, "totalDeductions": 82600,
                    "totalTaxableIncome": 558400, "taxOnIncome": 26760,
                    "surcharge": 0, "healthEducationCess": 1070, "totalTax": 27830,
                    "taxRelief87A": 0, "netTaxPayable": 27830, "advanceTax": 0,
                    "tdsSelf": 59280, "tdsPrevEmployer": 0, "totalTDS": 59280, "refund": 31450
                }
            )
            db.session.add(record)
            db.session.commit()
            print(f"Mock Form-16 data created for {emp.full_name} (ID: {emp.id})")
        else:
            print(f"Form-16 already exists for {emp.full_name}")
    else:
        print("No employee found to create mock data.")
