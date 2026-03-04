from models import db

class Designation(db.Model):
    __tablename__ = 'designations'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    designation_name = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"<Designation {self.designation_name}>"