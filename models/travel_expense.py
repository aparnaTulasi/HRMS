from datetime import datetime
from models import db

class TravelExpense(db.Model):
    __tablename__ = 'travel_expenses'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    type = db.Column(db.String(100))  # Lunch/Guest House/Travel
    amount = db.Column(db.Float, nullable=False)
    from_location = db.Column(db.String(200))
    to_location = db.Column(db.String(200))
    purpose = db.Column(db.Text)
    status = db.Column(db.String(50), default='Pending')  # Pending/Approved/Rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)