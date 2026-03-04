from datetime import datetime
from models import db

class SystemURL(db.Model):
    __tablename__ = 'system_urls'
    id = db.Column(db.Integer, primary_key=True)
    url_code = db.Column(db.String(50), unique=True, nullable=False)
    url_path = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255))
    module = db.Column(db.String(50))
    allowed_roles = db.Column(db.Text)
    permission_required = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    is_public = db.Column(db.Boolean, default=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    company = db.relationship('Company', backref='urls')