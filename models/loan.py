from datetime import datetime
from models import db

class Loan(db.Model):
    __tablename__ = "loans"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False, index=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False, index=True)
    
    loan_type = db.Column(db.String(50), nullable=False) # Personal, Home Renovation, Emergency, etc.
    amount = db.Column(db.Float, nullable=False)
    interest_rate = db.Column(db.Float, default=8.5)
    tenure_months = db.Column(db.Integer, nullable=False)
    emi = db.Column(db.Float, nullable=False)
    
    status = db.Column(db.String(20), default="PENDING") # PENDING, APPROVED, ACTIVE, PAID, REJECTED
    disbursement_date = db.Column(db.Date, nullable=True)
    
    reason = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee = db.relationship("Employee", backref="loans")

    def to_dict(self):
        return {
            "id": self.id,
            "employee_name": self.employee.full_name if self.employee else "Unknown",
            "amount": self.amount,
            "type": self.loan_type,
            "status": self.status,
            "emi": self.emi,
            "interest_rate": self.interest_rate,
            "tenure_months": self.tenure_months,
            "disbursement_date": self.disbursement_date.isoformat() if self.disbursement_date else None,
            "created_at": self.created_at.isoformat()
        }
