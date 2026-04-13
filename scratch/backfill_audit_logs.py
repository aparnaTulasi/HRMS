from app import app, db
from models.audit_log import AuditLog
from models.user import User
from sqlalchemy import text
from datetime import datetime
import json

def _get_module_local(entity):
    mapping = {
        'User': 'Auth', 'AUTH': 'Auth', 'Employee': 'Employee', 'Attendance': 'Employee',
        'LeaveRequest': 'Employee', 'Leave': 'Employee', 'Shift': 'Employee',
        'Payroll': 'Finance', 'Loan': 'Finance', 'Payslip': 'Finance',
        'Company': 'Company', 'Branch': 'Company', 'Department': 'Company',
        'Designation': 'Company'
    }
    return mapping.get(entity, 'System')

def _generate_desc_local(action, entity, meta):
    act = (action or "").upper()
    ent = entity or "Record"
    name = "Record"
    try:
        if meta:
            meta_dict = json.loads(meta.replace("'", '"')) if isinstance(meta, str) else meta
            name = meta_dict.get('name') or meta_dict.get('full_name') or meta_dict.get('company_name') or name
    except:
        pass
    if "LOGIN" in act: return "Successful login"
    if "CREATE" in act: return f"Created new {ent}: {name}"
    if "UPDATE" in act: return f"Updated {ent} details for {name}"
    if "DELETE" in act: return f"Deleted {ent}: {name}"
    return f"Performed {act} on {ent}"

def run_migration():
    with app.app_context():
        print("Starting Audit Log Schema Upgrade...")
        engine = db.engine
        
        # 1. Add columns if they don't exist (MySQL/SQLite compatible approach)
        columns = [
            ("user_name", "VARCHAR(100)"),
            ("module", "VARCHAR(50)"),
            ("description", "TEXT"),
            ("status", "VARCHAR(20)"),
            ("reference_id", "VARCHAR(50)"),
            ("old_data", "JSON"),
            ("new_data", "JSON"),
            ("year", "INT"),
            ("month", "INT"),
            ("day", "INT"),
            ("hour", "INT")
        ]
        
        for col_name, col_type in columns:
            try:
                engine.connect().execute(text(f"ALTER TABLE audit_logs ADD COLUMN {col_name} {col_type}"))
                print(f"Added column: {col_name}")
            except Exception as e:
                print(f"Column {col_name} might already exist.")

        # 2. Backfill existing data
        print("Backfilling existing logs...")
        logs = AuditLog.query.filter(AuditLog.year == None).all()
        print(f"Found {len(logs)} logs to backfill.")
        
        count = 0
        for log in logs:
            dt = log.created_at or datetime.utcnow()
            log.year = dt.year
            log.month = dt.month
            log.day = dt.day
            log.hour = dt.hour
            
            if not log.module:
                log.module = _get_module_local(log.entity)
            if not log.description:
                log.description = _generate_desc_local(log.action, log.entity, log.meta)
            if not log.status:
                log.status = "SUCCESS" if (log.status_code or 200) < 400 else "FAILED"
            
            # Fetch user name if missing
            if not log.user_name and log.user_id:
                u = User.query.get(log.user_id)
                if u: log.user_name = u.name
            
            count += 1
            if count % 100 == 0:
                db.session.commit()
                print(f"Processed {count}...")

        db.session.commit()
        print(f"Migration complete. {count} rows updated.")

if __name__ == "__main__":
    run_migration()
