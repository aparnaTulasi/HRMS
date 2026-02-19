from models import db

class BankDetails(db.Model):
    __tablename__ = 'bank_details'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    bank_name = db.Column(db.String(100), nullable=False)
    account_number = db.Column(db.String(50), nullable=False)
    ifsc_code = db.Column(db.String(20), nullable=False)

    def __repr__(self):
        return f"<BankDetails {self.bank_name} - {self.account_number}>"