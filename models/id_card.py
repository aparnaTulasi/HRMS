from datetime import datetime, date
from models import db

class IDCard(db.Model):
    __tablename__ = 'id_cards'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    
    # Auto-populated fields (can be updated)
    employee_code = db.Column(db.String(100), nullable=False)
    full_name = db.Column(db.String(200), nullable=False)
    designation = db.Column(db.String(100))
    department = db.Column(db.String(100))
    company_name = db.Column(db.String(200))
    
    # Additional fields
    photo_url = db.Column(db.String(500))
    company_logo_url = db.Column(db.String(500))
    blood_group = db.Column(db.String(20))
    joining_date = db.Column(db.Date)
    emergency_contact = db.Column(db.String(50))
    
    # System fields
    card_id = db.Column(db.String(100), unique=True, nullable=False) # e.g. IDC1023
    qr_code_path = db.Column(db.String(500))
    
    # ACTIVE, LOST, REISSUED, DISABLED
    status = db.Column(db.String(50), default='ACTIVE')
    
    issued_date = db.Column(db.DateTime, default=datetime.utcnow)
    expiry_date = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    history = db.relationship('IDCardHistory', backref='id_card', lazy=True)

class IDCardHistory(db.Model):
    __tablename__ = 'id_card_history'

    id = db.Column(db.Integer, primary_key=True)
    id_card_id = db.Column(db.Integer, db.ForeignKey('id_cards.id'), nullable=False)
    
    # CREATED, REISSUED, LOST_MARKED, DEACTIVATED
    action_type = db.Column(db.String(50), nullable=False)
    reason = db.Column(db.Text)
    
    old_qr_code = db.Column(db.String(500))
    new_qr_code = db.Column(db.String(500))
    
    action_by = db.Column(db.Integer) # user_id
    action_date = db.Column(db.DateTime, default=datetime.utcnow)
