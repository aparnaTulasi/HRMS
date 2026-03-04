from . import db
from datetime import datetime

class Company(db.Model):
    __tablename__ = 'companies'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.String(50), unique=True)
    company_name = db.Column(db.String(150), nullable=False)
    subdomain = db.Column(db.String(100), unique=True, nullable=False)
    company_code = db.Column(db.String(50), unique=True, nullable=False)
    company_prefix = db.Column(db.String(10), nullable=False)
    company_uid = db.Column(db.String(50), nullable=True)
    last_user_number = db.Column(db.Integer, default=0)
    industry = db.Column(db.String(100))
    company_size = db.Column(db.String(50))
    country = db.Column(db.String(100))
    state = db.Column(db.String(100))
    city_branch = db.Column(db.String(100))
    timezone = db.Column(db.String(50), default="UTC")
    address = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    email = db.Column(db.String(120))
    status = db.Column(db.String(50), default="Active")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to branches (one-to-many)
    # This allows you to easily access a company's branches via `company.branches`
    branches = db.relationship('Branch', backref='company', lazy=True, cascade="all, delete-orphan")