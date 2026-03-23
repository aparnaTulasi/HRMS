from datetime import datetime
from models import db

class Form16(db.Model):
    __tablename__ = 'form16_records'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    fy = db.Column(db.String(10), nullable=False)  # Financial Year, e.g., "2024-2025"
    ay = db.Column(db.String(10), nullable=False)  # Assessment Year, e.g., "2025-2026"
    pan = db.Column(db.String(20))
    tan = db.Column(db.String(20))
    employer_pan = db.Column(db.String(20))
    
    # Part A and Part B data stored as JSON for flexibility
    part_a = db.Column(db.JSON)
    part_b = db.Column(db.JSON)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to employee
    employee = db.relationship('Employee', backref='tax_certificates')

    def to_dict(self):
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'company_id': self.company_id,
            'name': self.employee.full_name if self.employee else '',
            'employee_no': self.employee.employee_id if self.employee else '',
            'designation': self.employee.designation if self.employee else '',
            'department': self.employee.department if self.employee else '',
            'pan': self.pan,
            'tan': self.tan,
            'employer_pan': self.employer_pan,
            'fy': self.fy,
            'ay': self.ay,
            'partA': self.part_a,
            'partB': self.part_b,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
class FullAndFinal(db.Model):
    __tablename__ = 'full_and_final_settlements'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    resign_date = db.Column(db.Date)
    last_working_day = db.Column(db.Date)
    
    notice_period_required = db.Column(db.Integer, default=0)
    notice_period_served = db.Column(db.Integer, default=0)
    notice_status = db.Column(db.String(50)) # Served, Short, Waived
    status = db.Column(db.String(50), default='Pending') # Pending, Processing, Settled
    
    settlement_data = db.Column(db.JSON) # Detailed earnings/deductions
    exit_clearance = db.Column(db.JSON) # Checklist
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee = db.relationship('Employee', backref='settlements')

    def to_dict(self):
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'name': self.employee.full_name if self.employee else 'Unknown',
            'designation': self.employee.designation if self.employee else 'N/A',
            'department': self.employee.department if self.employee else 'N/A',
            'resignDate': self.resign_date.strftime('%d %b %Y') if self.resign_date else None,
            'lastWorkingDay': self.last_working_day.strftime('%d %b %Y') if self.last_working_day else None,
            'noticePeriodRequired': self.notice_period_required,
            'noticePeriodServed': self.notice_period_served,
            'noticeStatus': self.notice_status,
            'status': self.status,
            'settlement': self.settlement_data,
            'clearance': self.exit_clearance
        }
