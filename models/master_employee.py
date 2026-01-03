from models.master import db

class Employee(db.Model):
    __tablename__ = 'employee'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    company_subdomain = db.Column(db.String(100))
    department = db.Column(db.String(100))
    designation = db.Column(db.String(100))
    phone_number = db.Column(db.String(20))
    date_of_joining = db.Column(db.String(20))