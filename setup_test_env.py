from app import app, db
from models.user import User
from models.employee import Employee
from models.payroll import PaySlip
from models.audit_log import AuditLog
from datetime import datetime, date

def setup():
    with app.app_context():
        print("--- CONSTRUCTING TEST SCENARIO ---")
        
        # 1. Manager setup
        m_user = User.query.get(20) # seelamaparna@gmail.com
        m_user.company_id = 1
        m_emp = Employee.query.filter_by(user_id=20).first()
        if m_emp:
            m_emp.company_id = 1
        else:
            m_emp = Employee(user_id=20, company_id=1, full_name="Test Manager")
            db.session.add(m_emp)
        db.session.flush()

        # 2. Subordinate setup
        s_user = User.query.get(33)
        s_user.company_id = 1
        s_emp = Employee.query.filter_by(user_id=33).first()
        if s_emp:
            s_emp.company_id = 1
            s_emp.manager_id = m_emp.id
        else:
            s_emp = Employee(user_id=33, company_id=1, full_name="Test Subordinate", manager_id=m_emp.id)
            db.session.add(s_emp)
        db.session.flush()

        # 3. Create a payslip for Subordinate in March 2026
        ps = PaySlip.query.filter_by(employee_id=s_emp.id, pay_month=3, pay_year=2026).first()
        if not ps:
            ps = PaySlip(
                company_id=1,
                employee_id=s_emp.id,
                pay_month=3,
                pay_year=2026,
                net_salary=50000.0,
                status="PAID",
                pay_date=date(2026, 3, 31)
            )
            db.session.add(ps)

        # 4. Create an audit log for Subordinate (Employee module)
        log = AuditLog(
            company_id=1,
            user_id=s_user.id,
            action="UPDATE",
            entity="Attendance",
            role="EMPLOYEE"
        )
        db.session.add(log)

        db.session.commit()
        print("Environment ready. Manager (20) and Sub (33) are now in Company 1 with linked hierarchy and data.")

if __name__ == "__main__":
    setup()
