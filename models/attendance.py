from datetime import datetime
from models import db

class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    in_time = db.Column(db.DateTime)
    out_time = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='ABSENT')
    work_hours = db.Column(db.Float, default=0.0)
    year = db.Column(db.Integer, default=datetime.utcnow().year)
    month = db.Column(db.Integer, default=datetime.utcnow().month)
    marked_by = db.Column(db.String(20))
    remarks = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('employee_id', 'date', name='unique_attendance'),)