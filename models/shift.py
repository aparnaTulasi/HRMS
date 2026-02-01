from datetime import datetime
from models import db

class Shift(db.Model):
    __tablename__ = 'shift'
    shift_id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    shift_name = db.Column(db.String(50), nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    weekly_off = db.Column(db.String(50), default='Sunday')
    description = db.Column(db.String(200))
    is_active = db.Column(db.String(3), default='Yes') # Yes/No
    
    __table_args__ = (db.UniqueConstraint('company_id', 'shift_name', name='uq_company_shift_name'),)

class ShiftAssignment(db.Model):
    __tablename__ = 'shift_assignment'
    assignment_id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    shift_id = db.Column(db.Integer, db.ForeignKey('shift.shift_id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    
    employee = db.relationship('Employee', backref='shift_assignments')
    shift = db.relationship('Shift', backref='assignments')

    __table_args__ = (
        db.UniqueConstraint('company_id', 'employee_id', 'start_date', name='uq_company_employee_shift_start'),
    )