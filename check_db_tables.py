
from app import app
from models import db
from sqlalchemy import inspect

with app.app_context():
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print(f"Tables: {tables}")
    if 'audit_logs' in tables:
        from models.audit_log import AuditLog
        count = AuditLog.query.count()
        print(f"AuditLog count: {count}")
    else:
        print("audit_logs TABLE MISSING!")
