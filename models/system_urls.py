from models.master import db
from datetime import datetime

class SystemUrl(db.Model):
    __tablename__ = 'system_urls'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(255), nullable=False)
    created_by = db.Column(db.Integer)  # User ID of Super Admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class RoleUrlPermission(db.Model):
    __tablename__ = 'role_url_permissions'
    
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(50), nullable=False)
    url_id = db.Column(db.Integer, db.ForeignKey('system_urls.id'), nullable=False)
    can_access = db.Column(db.Boolean, default=False)
    
    url = db.relationship('SystemUrl', backref='permissions')

    __table_args__ = (
        db.UniqueConstraint('role', 'url_id', name='unique_role_url'),
    )