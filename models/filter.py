from datetime import datetime
from models import db
import json

class FilterConfiguration(db.Model):
    __tablename__ = 'filter_configurations'
    id = db.Column(db.Integer, primary_key=True)
    filter_name = db.Column(db.String(100), nullable=False)
    module = db.Column(db.String(50), nullable=False)
    filter_config = db.Column(db.Text)
    allowed_roles = db.Column(db.Text)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)