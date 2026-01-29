from datetime import datetime
from models import db

class Asset(db.Model):
    __tablename__ = 'assets'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    asset_code = db.Column(db.String(100), unique=True, nullable=False)
    asset_name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100))
    status = db.Column(db.String(50), default='Available') # Available/Assigned/Damaged

class AssetAllocation(db.Model):
    __tablename__ = 'asset_allocations'
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    allocation_date = db.Column(db.Date, default=datetime.utcnow)
    return_date = db.Column(db.Date)
    condition_notes = db.Column(db.Text)
    status = db.Column(db.String(50), default='Assigned') # Assigned/Returned