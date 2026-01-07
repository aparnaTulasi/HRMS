from models import db

class EmployeeAddress(db.Model):
    __tablename__ = 'employee_address'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), unique=True, nullable=False)
    
    address_line1 = db.Column(db.String(200))
    permanent_address = db.Column(db.String(200))
    city = db.Column(db.String(50))
    state = db.Column(db.String(50))
    zip_code = db.Column(db.String(20))