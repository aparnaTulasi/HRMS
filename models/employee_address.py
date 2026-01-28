from models import db

class EmployeeAddress(db.Model):
    __tablename__ = 'employee_address'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    address_type = db.Column(db.String(20)) # PRESENT / PERMANENT
    address_line = db.Column(db.String(255))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    pincode = db.Column(db.String(20))
    country = db.Column(db.String(100))