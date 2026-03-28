from datetime import datetime
from models import db

class Role(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255))
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    permissions = db.relationship('RolePermission', backref='role', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        # Flatten permissions into a list of strings for the matrix
        permission_list = [p.permission_code for p in self.permissions]
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'company_id': self.company_id,
            'permissions': permission_list,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class RolePermission(db.Model):
    __tablename__ = 'role_permissions'

    id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    permission_code = db.Column(db.String(100), nullable=False) # e.g. "employees.view"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
