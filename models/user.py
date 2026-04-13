from datetime import datetime, timedelta
from flask_login import UserMixin
from models import db
import secrets
from constants.permissions import MODULES, ACTIONS, get_permission_code


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)  # company_email (sync)
    username = db.Column(db.String(100), nullable=True)  # display username
    phone = db.Column(db.String(20), nullable=True)    # phone_number (sync)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    status = db.Column(db.String(20), default='ACTIVE')

    # ✅ NEW FLAGS
    profile_completed = db.Column(db.Boolean, default=False)
    profile_locked = db.Column(db.Boolean, default=False)
    must_change_password = db.Column(db.Boolean, default=False)

    portal_prefix = db.Column(db.String(50), nullable=True)
    otp = db.Column(db.String(6), nullable=True)
    otp_expiry = db.Column(db.DateTime, nullable=True)
    last_login = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    employee_profile = db.relationship('Employee', foreign_keys='Employee.user_id', backref=db.backref('user', foreign_keys='Employee.user_id'), uselist=False, lazy=True)
    permissions = db.relationship('UserPermission', foreign_keys='UserPermission.user_id', backref=db.backref('user', foreign_keys='UserPermission.user_id'), lazy=True)

    __table_args__ = (db.UniqueConstraint('company_id', 'email', name='unique_company_email'),)

    @property
    def name(self):
        """Returns the full name of the user based on their profile."""
        if self.role == 'SUPER_ADMIN' and hasattr(self, 'super_admin') and self.super_admin:
            first = self.super_admin.first_name or ""
            last = self.super_admin.last_name or ""
            return f"{first} {last}".strip() or "Super Admin"
        
        if self.employee_profile:
            return self.employee_profile.full_name or "Employee"
            
        return "User"

    def generate_otp(self):
        self.otp = ''.join(secrets.choice('0123456789') for _ in range(6))
        self.otp_expiry = datetime.utcnow() + timedelta(minutes=10)
        return self.otp

    @property
    def is_active(self):
        """Overrides UserMixin.is_active to use the status column as the source of truth."""
        return (self.status or "").upper() == 'ACTIVE'

    def has_permission(self, permission_code):
        from utils.role_utils import normalize_role
        if normalize_role(self.role) == 'SUPER_ADMIN':
            return True
        return permission_code in self.get_all_permissions()

    def get_all_permissions(self):
        """
        Aggregates permissions from:
        1. UserPermission table (Direct granular permissions)
        2. RolePermission table (Inherited from the user's role)
        """
        from utils.role_utils import normalize_role
        role_name = normalize_role(self.role)
        
        if role_name == 'SUPER_ADMIN':
            from constants.permissions import ALL_PERMISSIONS
            return ALL_PERMISSIONS

        # 1. Direct permissions
        direct_perms = [p.permission_code for p in self.permissions]

        # 2. Inherited permissions from Role
        from models.role import Role, RolePermission
        role_obj = Role.query.filter_by(name=self.role, company_id=self.company_id).first()
        inherited_perms = []
        if role_obj:
            inherited_perms = [rp.permission_code for rp in role_obj.permissions]

        # Combine and remove duplicates
        return list(set(direct_perms + inherited_perms))

    def get_all_permissions_matrix(self):
        """
        Aggregates all permissions and groups them by module into a matrix format.
        Format: {"Dashboard": ["View", "Create"], "Attendance": ["View"]}
        """
        all_codes = self.get_all_permissions()
        
        grouped = {}
        for code in all_codes:
            matched = False
            for module in MODULES:
                clean_module = module.upper().replace(" ", "_").replace("&", "AND")
                if code.startswith(clean_module + "_"):
                    raw_action = code.replace(clean_module + "_", "")
                    matched_action = raw_action
                    for a in ACTIONS:
                        if a.upper() == raw_action:
                            matched_action = a
                            break
                    
                    if module not in grouped:
                        grouped[module] = []
                    if matched_action not in grouped[module]:
                        grouped[module].append(matched_action)
                    matched = True
                    break
            
            if not matched:
                if "Other" not in grouped:
                    grouped["Other"] = []
                if code not in grouped["Other"]:
                    grouped["Other"].append(code)
                
        return grouped