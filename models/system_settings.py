from . import db
from datetime import datetime

class SystemSetting(db.Model):
    __tablename__ = 'system_settings'

    id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.String(50), unique=True, nullable=False) # e.g., 'TIMEZONE', 'CURRENCY'
    setting_value = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255))
    
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def get_value(cls, key, default=None):
        setting = cls.query.filter_by(setting_key=key.upper()).first()
        return setting.setting_value if setting else default
