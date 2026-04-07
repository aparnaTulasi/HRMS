# models/desk.py
from datetime import datetime, date
from models import db

class Desk(db.Model):
    __tablename__ = 'desks'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False, index=True)
    
    desk_code = db.Column(db.String(20), nullable=False) # e.g. "D01"
    location = db.Column(db.String(150)) # e.g. "Desk 101, 1st Floor - Alpha Wing"
    floor = db.Column(db.String(50)) # e.g. "1st Floor"
    wing = db.Column(db.String(50)) # e.g. "Alpha Wing"
    team = db.Column(db.String(100)) # e.g. "Engineering"
    
    is_permanent = db.Column(db.Boolean, default=False)
    assigned_employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True) # For permanent seats
    
    # Current live status (Available, Booked, Assigned)
    status = db.Column(db.String(20), default='Available')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    assigned_employee = db.relationship('Employee', foreign_keys=[assigned_employee_id])

class DeskBooking(db.Model):
    __tablename__ = 'desk_bookings'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False, index=True)
    
    desk_id = db.Column(db.Integer, db.ForeignKey('desks.id'), nullable=False, index=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False, index=True)
    
    booking_date = db.Column(db.Date, nullable=False, index=True)
    preferred_time = db.Column(db.String(20)) # e.g. "10:00 AM"
    
    # status: Confirmed, Pending Approval, Cancelled
    status = db.Column(db.String(20), default='Confirmed', nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    desk = db.relationship('Desk', backref='bookings')
    employee = db.relationship('Employee', backref='desk_bookings')
