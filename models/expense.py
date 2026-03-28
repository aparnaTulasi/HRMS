# models/expense.py
from datetime import datetime
from models import db

class ExpenseClaim(db.Model):
    __tablename__ = "expense_claims"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, nullable=False, index=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False, index=True)
    
    project_purpose = db.Column(db.String(255), nullable=False) # UI: Project / Purpose
    category = db.Column(db.String(50), nullable=False)        # UI: Flight, Hotel, Meals, Taxi, etc.
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default="$")           # UI: $
    
    expense_date = db.Column(db.Date, nullable=False)          # UI: Date of Expense
    description = db.Column(db.Text, nullable=True)            # UI: Provide detail...
    
    status = db.Column(db.String(20), default="PENDING")       # PENDING, APPROVED, REJECTED
    
    # Detailed date fields as requested
    year = db.Column(db.Integer)
    month = db.Column(db.Integer)
    day = db.Column(db.Integer)
    time = db.Column(db.String(20)) # e.g. "14:30:00"
    added_by_name = db.Column(db.String(150)) # "byperson name"
    
    # HR/Admin approval fields
    approved_by = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee = db.relationship("Employee", foreign_keys=[employee_id], backref="expense_claims")
    approver = db.relationship("Employee", foreign_keys=[approved_by])

    def to_dict(self):
        return {
            "id": self.id,
            "employee_name": self.employee.full_name if self.employee else "Unknown",
            "employee_id": self.employee.employee_id if self.employee else "N/A",
            "project_purpose": self.project_purpose,
            "category": self.category,
            "amount": self.amount,
            "currency": self.currency,
            "expense_date": self.expense_date.isoformat(),
            "status": self.status,
            "description": self.description,
            "created_at": self.created_at.isoformat()
        }
