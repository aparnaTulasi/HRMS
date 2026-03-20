from app import app
from models import db
from models.audit_log import AuditLog
from datetime import datetime, timedelta

def seed_audit_logs():
    with app.app_context():
        # Clear existing logs if needed (optional)
        # db.session.query(AuditLog).delete()
        
        logs = [
            # Super Admin Logs
            AuditLog(
                user_id=1,
                role='SUPER_ADMIN',
                action='CREATE_COMPANY',
                entity='Company',
                entity_id=1,
                method='POST',
                path='/api/superadmin/companies',
                status_code=201,
                ip_address='127.0.0.1',
                created_at=datetime.utcnow() - timedelta(hours=2)
            ),
            AuditLog(
                user_id=1,
                role='SUPER_ADMIN',
                action='UPDATE_USER_ROLE',
                entity='User',
                entity_id=4,
                method='PUT',
                path='/api/user/4/role',
                status_code=200,
                ip_address='127.0.0.1',
                created_at=datetime.utcnow() - timedelta(hours=1)
            ),
            # Admin Logs (Company 1)
            AuditLog(
                company_id=1,
                user_id=4,
                role='ADMIN',
                action='MARK_ATTENDANCE',
                entity='Attendance',
                entity_id=10,
                method='POST',
                path='/api/attendance/manual',
                status_code=200,
                ip_address='192.168.1.6',
                created_at=datetime.utcnow() - timedelta(minutes=45)
            ),
            AuditLog(
                company_id=1,
                user_id=4,
                role='ADMIN',
                action='APPROVE_LEAVE',
                entity='Leave',
                entity_id=5,
                method='PUT',
                path='/api/leave/5/status',
                status_code=200,
                ip_address='192.168.1.6',
                created_at=datetime.utcnow() - timedelta(minutes=30)
            ),
            # Employee Logs (Under Company 1 for HR to see)
            AuditLog(
                company_id=1,
                user_id=10,
                role='EMPLOYEE',
                action='LOGIN',
                entity='Auth',
                method='POST',
                path='/api/auth/login',
                status_code=200,
                ip_address='192.168.1.10',
                created_at=datetime.utcnow() - timedelta(minutes=15)
            ),
            AuditLog(
                company_id=1,
                user_id=12,
                role='MANAGER',
                action='UPDATE_PROJECT',
                entity='Project',
                entity_id=2,
                method='PUT',
                path='/api/projects/2',
                status_code=200,
                ip_address='192.168.1.12',
                created_at=datetime.utcnow() - timedelta(minutes=5)
            )
        ]
        
        db.session.add_all(logs)
        db.session.commit()
        print("✅ Audit logs seeded successfully!")

if __name__ == "__main__":
    seed_audit_logs()
