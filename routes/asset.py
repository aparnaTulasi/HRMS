from datetime import datetime
from models import db

class Asset(db.Model):
    __tablename__ = 'assets'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    asset_code = db.Column(db.String(50), nullable=False)
    asset_name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))
    serial_number = db.Column(db.String(100))
    brand = db.Column(db.String(50))
    model = db.Column(db.String(50))
    vendor_name = db.Column(db.String(100))
    location = db.Column(db.String(100))
    notes = db.Column(db.Text)
    status = db.Column(db.String(50), default='Available')
    is_active = db.Column(db.Boolean, default=True)
    purchase_date = db.Column(db.Date)
    warranty_end_date = db.Column(db.Date)
    purchase_cost = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AssetAllocation(db.Model):
    __tablename__ = 'asset_allocations'
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    allocation_date = db.Column(db.Date, default=datetime.utcnow)
    expected_return_date = db.Column(db.Date)
    return_date = db.Column(db.Date)
    issue_notes = db.Column(db.Text)
    return_notes = db.Column(db.Text)
    issued_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    returned_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    status = db.Column(db.String(50), default='Assigned')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AssetConditionLog(db.Model):
    __tablename__ = 'asset_condition_logs'
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    log_type = db.Column(db.String(50)) # Damage, Repair, Inspection
    condition = db.Column(db.String(50))
    notes = db.Column(db.Text)
    logged_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    logged_at = db.Column(db.DateTime, default=datetime.utcnow)