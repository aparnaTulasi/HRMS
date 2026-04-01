from models import db
from datetime import datetime

class ExitRequest(db.Model):
    __tablename__ = 'exit_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    resignation_date = db.Column(db.DateTime, default=datetime.utcnow)
    desired_lwd = db.Column(db.DateTime, nullable=False) # Last Working Day
    official_lwd = db.Column(db.DateTime, nullable=True) # Finalized by HR
    reason = db.Column(db.Text, nullable=False)
    
    status = db.Column(db.String(20), default='PENDING') # PENDING, APPROVED, REJECTED, COMPLETED
    hr_remarks = db.Column(db.Text, nullable=True)
    
    # Process tracking
    is_clearance_done = db.Column(db.Boolean, default=False)
    final_settlement_done = db.Column(db.Boolean, default=False)
    
    # Relationships
    employee = db.relationship('Employee', backref='exit_requests')
    
    def to_dict(self):
        return {
            "id": self.id,
            "employee_name": f"{self.employee.first_name} {self.employee.last_name}" if self.employee else "Unknown",
            "employee_code": self.employee.employee_id if self.employee else "N/A",
            "resignation_date": self.resignation_date.strftime("%d %b %Y"),
            "desired_lwd": self.desired_lwd.strftime("%d %b %Y"),
            "official_lwd": self.official_lwd.strftime("%d %b %Y") if self.official_lwd else "TBD",
            "reason": self.reason,
            "status": self.status,
            "hr_remarks": self.hr_remarks,
            "is_clearance_done": self.is_clearance_done,
            "final_settlement_done": self.final_settlement_done
        }
