from datetime import datetime, date
from models import db

class Asset(db.Model):
    __tablename__ = 'assets'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)

    asset_code = db.Column(db.String(100), unique=True, nullable=False)
    asset_name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100))

    # Master fields (recommended)
    serial_number = db.Column(db.String(150), unique=True, nullable=True)
    brand = db.Column(db.String(100))
    model = db.Column(db.String(120))
    vendor_name = db.Column(db.String(150))

    purchase_date = db.Column(db.Date)
    purchase_cost = db.Column(db.Float)
    warranty_end_date = db.Column(db.Date)

    location = db.Column(db.String(150))
    notes = db.Column(db.Text)

    status = db.Column(db.String(50), default='Available')  # Available/Assigned/Damaged/Retired
    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AssetAllocation(db.Model):
    __tablename__ = 'asset_allocations'

    id = db.Column(db.Integer, primary_key=True)

    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)

    allocation_date = db.Column(db.Date, default=date.today)
    expected_return_date = db.Column(db.Date, nullable=True)
    return_date = db.Column(db.Date, nullable=True)

    # notes & workflow
    issue_notes = db.Column(db.Text)
    return_notes = db.Column(db.Text)

    issued_by = db.Column(db.Integer, nullable=True)   # user_id (optional)
    returned_by = db.Column(db.Integer, nullable=True) # user_id (optional)

    status = db.Column(db.String(50), default='Assigned')  # Assigned/Returned


class AssetConditionLog(db.Model):
    __tablename__ = 'asset_condition_logs'

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)

    log_type = db.Column(db.String(50), nullable=False)  # Damage/Repair/Inspection
    condition = db.Column(db.String(80))                 # Good/Fair/Poor
    notes = db.Column(db.Text)

    logged_by = db.Column(db.Integer, nullable=True)     # user_id (optional)
    logged_at = db.Column(db.DateTime, default=datetime.utcnow)
