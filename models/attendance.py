from datetime import datetime, date
from models import db

class Attendance(db.Model):
    """
    One row per employee per date (UPSERT key)
    """
    __tablename__ = "attendance_logs"

    attendance_id = db.Column(db.Integer, primary_key=True)

    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False, index=True)

    # Main unique key for UPSERT
    attendance_date = db.Column(db.Date, nullable=False, index=True)

    # Times (optional for Absent)
    punch_in_time = db.Column(db.DateTime, nullable=True)
    punch_out_time = db.Column(db.DateTime, nullable=True)

    # Stored to show "Logged Time"
    total_minutes = db.Column(db.Integer, default=0, nullable=False)

    # Present / Absent / Leave / Half Day etc. (keep it flexible)
    status = db.Column(db.String(20), default="Present", nullable=False)

    # manual/import/web/biometric (you said no self punch, still keep for audit)
    capture_method = db.Column(db.String(50), default="Manual", nullable=False)  # Manual / Import

    # Audit
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("company_id", "employee_id", "attendance_date", name="uq_att_company_emp_date"),
    )

    def recalc_total_minutes(self):
        if self.punch_in_time and self.punch_out_time and self.punch_out_time > self.punch_in_time:
            diff = self.punch_out_time - self.punch_in_time
            self.total_minutes = int(diff.total_seconds() // 60)
        else:
            self.total_minutes = 0