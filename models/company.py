# models/company.py
from datetime import datetime
from models import db

class Company(db.Model):
    __tablename__ = 'companies'

    id = db.Column(db.Integer, primary_key=True)

    company_name = db.Column(db.String(100), nullable=False)
    company_size = db.Column(db.String(30), nullable=False)      # ✅ NEW
    industry = db.Column(db.String(100), nullable=False)         # ✅ MAKE REQUIRED
    state = db.Column(db.String(100), nullable=False)            # ✅ NEW
    country = db.Column(db.String(100), nullable=False)          # ✅ NEW
    city_branch = db.Column(db.String(100), nullable=False)      # ✅ NEW

    # keep for existing flow (do not remove now)
    subdomain = db.Column(db.String(50), unique=False, nullable=False)
    company_code = db.Column(db.String(20), unique=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    users = db.relationship('User', backref='company', lazy=True)
    employees = db.relationship('Employee', backref='company', lazy=True)
    departments = db.relationship('Department', backref='company', lazy=True)
