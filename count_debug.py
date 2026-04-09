from app import app, db
from models.payroll import PaySlip
from models.audit_log import AuditLog

with app.app_context():
    ps_count = PaySlip.query.filter(PaySlip.employee_id.in_([15, 27])).count()
    al_count = AuditLog.query.filter(AuditLog.user_id.in_([20, 33])).count()
    print(f"Payslips for 15,27: {ps_count}")
    print(f"AuditLogs for 20,33: {al_count}")
    
    if ps_count == 0:
        # Check ANY payslips
        print(f"Total Payslips in DB: {PaySlip.query.count()}")
    if al_count == 0:
        print(f"Total AuditLogs in DB: {AuditLog.query.count()}")
